"""The statistics in RESULTS.md that report.py doesn't print.

    python stats.py results/full.jsonl

  paired tests     items where exactly one of two setups was right; exact two-sided sign test
  shipped acc      each panel ships what its jurors agree on; every single model (and each
                   panel juror alone, by its own stated confidence) ships the same number of
                   decisions per dataset, its most confident ones
  bootstrap        95% interval on the difference in pooled shipped accuracy, resampling
                   items within each dataset

Ties in confidence are broken by record order, as in report.py. Needs only the standard library.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from collections import defaultdict
from pathlib import Path

PANELS = ["openjury", "panel-mixed", "panel-open"]
SINGLES = ["jev-openrouter", "large-opus"]
BOOTSTRAP = 2000


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path)
    args = p.parse_args()

    by = defaultdict(dict)  # setup -> id -> record
    for line in args.results.read_text().splitlines():
        r = json.loads(line)
        by[r["setup"]][r["id"]] = r
    setups = [s for s in PANELS + SINGLES if s in by]
    shared = set.intersection(*(set(by[s]) for s in setups))
    ids = [i for i in by[setups[0]] if i in shared]  # file order, so ties break as in report.py
    print(f"{len(ids)} items shared by {', '.join(setups)}\n")

    print("## Accuracy and paired tests\n")
    print("| Setup | Accuracy (95% CI) |\n|---|---|")
    for s in setups:
        acc = sum(_right(by[s][i]) for i in ids) / len(ids)
        print(f"| {s} | {acc:.1%} ± {1.96 * math.sqrt(acc * (1 - acc) / len(ids)):.1%} |")
    print("\n| Comparison | Split | p |\n|---|---|---|")
    for a, b in itertools.combinations(setups, 2):
        wa = sum(_right(by[a][i]) and not _right(by[b][i]) for i in ids)
        wb = sum(_right(by[b][i]) and not _right(by[a][i]) for i in ids)
        print(f"| {a} vs {b} | {wa} vs {wb} | {_sign_test(wa, wb):.4f} |")

    datasets = defaultdict(list)
    for i in ids:
        datasets[by[setups[0]][i]["dataset"]].append(i)

    for panel in [s for s in PANELS if s in by]:
        shipped = {d: [i for i in its if not by[panel][i]["needs_review"]] for d, its in datasets.items()}
        n_ship = sum(map(len, shipped.values()))
        rivals = {s: _confidence(by[s]) for s in SINGLES if s in by}
        jurors = sorted({v["juror"] for i in ids for v in by[panel][i]["votes"]})
        for j in jurors:
            rivals[f"{j} alone"] = {
                i: (v["confidence"] or 0, v["choice"] == by[panel][i]["label"])
                for i in ids for v in by[panel][i]["votes"] if v["juror"] == j
            }

        print(f"\n## {panel}: shipped accuracy at {n_ship / len(ids):.1%} coverage\n")
        print("| Rival | Rival ships correctly | Panel minus rival (95% bootstrap) |\n|---|---|---|")
        own = _pooled(by[panel], shipped)
        print(f"| ({panel} itself) | {own:.1%} | |")
        rng = random.Random(0)
        for name, conf in rivals.items():
            point = _matched(conf, datasets, shipped)
            diffs = []
            for _ in range(BOOTSTRAP):
                sample = {d: [rng.choice(its) for _ in its] for d, its in datasets.items()}
                ship_s = {d: [i for i in its if not by[panel][i]["needs_review"]] for d, its in sample.items()}
                diffs.append(_pooled(by[panel], ship_s) - _matched(conf, sample, ship_s))
            diffs.sort()
            lo, hi = diffs[int(0.025 * BOOTSTRAP)], diffs[int(0.975 * BOOTSTRAP) - 1]
            print(f"| {name} | {point:.1%} | {100 * lo:+.1f} to {100 * hi:+.1f} points |")


def _right(r: dict) -> bool:
    return r["pred"] is not None and r["pred"] == r["label"]


def _confidence(records: dict) -> dict:
    """id -> (confidence signal, right): Jev's top probability, otherwise the stated confidence."""
    out = {}
    for i, r in records.items():
        c = r.get("probability") if r.get("probability") is not None else r.get("confidence")
        out[i] = (c or 0, _right(r))
    return out


def _pooled(records: dict, shipped: dict) -> float:
    n = sum(map(len, shipped.values()))
    return sum(_right(records[i]) for its in shipped.values() for i in its) / n


def _matched(conf: dict, datasets: dict, shipped: dict) -> float:
    """Pooled accuracy of the rival's k most confident items per dataset, k = what the panel shipped."""
    right = total = 0
    for d, its in datasets.items():
        k = len(shipped[d])
        top = sorted(its, key=lambda i: -conf[i][0])[:k]
        right += sum(conf[i][1] for i in top)
        total += k
    return right / total


def _sign_test(a: int, b: int) -> float:
    n, k = a + b, min(a, b)
    tail = sum(math.comb(n, x) for x in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


if __name__ == "__main__":
    main()
