"""The statistics in RESULTS.md that report.py doesn't print.

    python stats.py results/full.jsonl

  overall          accuracy, latency, decisions over 60 s, and cost per setup
  paired tests     items where exactly one of two setups was right, overall and per dataset;
                   exact two-sided sign test
  reliability      failed calls, decisions with no verdict, every failure by juror and error,
                   and juror calls that ran away past RUNAWAY completion tokens
  shipped acc      each panel ships what its jurors agree on; every single model (and each
                   panel juror alone, by its own stated confidence) ships the same number of
                   decisions per dataset, its most confident ones. Ties in confidence are
                   broken by record order, as in report.py; beside it are the expected figure
                   with ties broken at random, and the worst and best orders
  bootstrap        95% interval on the difference in pooled shipped accuracy, resampling
                   items within each dataset
  economics        a panel against each single model at the same coverage: the difference in
                   cost per wrong decision shipped
  head to head     the panels ranked by juror agreement, at each panel's own coverage
  hate speech      per-class rates on the half-hateful sample, and the share of hateful
                   comments at which two setups would be equally accurate

Prices come from report.py. Needs only the standard library.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from report import _cost, _q

PANELS = ["openjury", "panel-mixed", "panel-open"]
SINGLES = ["jev-openrouter", "large-opus"]
BOOTSTRAP = 2000
RUNAWAY = 32_768  # completion tokens; a vote takes a few dozen


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path)
    args = p.parse_args()

    by = defaultdict(dict)  # setup -> id -> record
    for line in args.results.read_text().splitlines():
        r = json.loads(line)
        by[r["setup"]][r["id"]] = r
    setups = [s for s in PANELS + SINGLES if s in by]
    panels = [s for s in PANELS if s in by]
    shared = set.intersection(*(set(by[s]) for s in setups))
    ids = [i for i in by[setups[0]] if i in shared]  # file order, so ties break as in report.py
    print(f"{len(ids)} items shared by {', '.join(setups)}\n")

    datasets = defaultdict(list)
    for i in ids:
        datasets[by[setups[0]][i]["dataset"]].append(i)

    _overall(by, setups, ids)
    _paired(by, setups, ids, datasets)
    _reliability(by, setups, panels, ids)
    for panel in panels:
        _shipped(by, panel, ids, datasets)
    _head_to_head(by, panels, ids)
    if "mhs" in datasets:
        _by_class(by, setups, panels, datasets["mhs"], "hateful")


def _overall(by, setups, ids) -> None:
    print("## Overall\n")
    print("| Setup | Accuracy (95% CI) | Latency p50 / p95 / p99 / max | Over 60 s | $ per 1,000 | $ in all |")
    print("|---|---|---|---|---|---|")
    spent = 0.0
    for s in setups:
        acc = sum(_right(by[s][i]) for i in ids) / len(ids)
        lats = sorted(by[s][i]["latency_s"] for i in ids if by[s][i].get("latency_s") is not None)
        cost = _spend(by[s], s, ids)
        spent += cost
        print(f"| {s} | {acc:.1%} ± {1.96 * math.sqrt(acc * (1 - acc) / len(ids)):.1%} "
              f"| {_q(lats, 0.5):.2f} / {_q(lats, 0.95):.2f} / {_q(lats, 0.99):.1f} / {lats[-1]:.1f} s "
              f"| {sum(x > 60 for x in lats)} | {1000 * cost / len(ids):.2f} | {cost:.2f} |")
    print(f"\nAll setups together: ${spent:.2f}")


def _paired(by, setups, ids, datasets) -> None:
    names = sorted(datasets)
    print("\n## Paired tests\n")
    print("Items only the first setup got right against items only the second did, and the exact "
          "two-sided sign test.\n")
    print("| Comparison | All | " + " | ".join(names) + " |")
    print("|---|---|" + "---|" * len(names))
    for a, b in itertools.combinations(setups, 2):
        cells = [_split(by[a], by[b], its) for its in [ids, *(datasets[d] for d in names)]]
        print(f"| {a} vs {b} | " + " | ".join(cells) + " |")


def _split(a: dict, b: dict, its: list) -> str:
    wa = sum(_right(a[i]) and not _right(b[i]) for i in its)
    wb = sum(_right(b[i]) and not _right(a[i]) for i in its)
    return f"{wa}–{wb}, p {_sign_test(wa, wb):.4f}"


def _reliability(by, setups, panels, ids) -> None:
    print("\n## Reliability\n")
    print("| Setup | Failed calls | Decisions with no verdict |\n|---|---|---|")
    for s in setups:
        calls = sum(len(by[s][i].get("votes") or [None]) for i in ids)
        failed = sum(1 for _ in _failures(by[s], ids))
        print(f"| {s} | {failed} of {calls} | {sum(by[s][i]['pred'] is None for i in ids)} |")

    rows = Counter((s, *f) for s in setups for f in _failures(by[s], ids))
    print("\n| Setup | Juror | Dataset | Error | Count |\n|---|---|---|---|---|")
    for (s, juror, dataset, error), n in sorted(rows.items()):
        print(f"| {s} | {juror} | {dataset} | {error} | {n} |")

    print(f"\nJuror calls past {RUNAWAY:,} completion tokens:\n")
    print("| Setup | Item | Juror | Completion tokens | Latency |\n|---|---|---|---|---|")
    hit = defaultdict(list)
    for s in panels:
        for i in ids:
            for v in by[s][i].get("votes") or []:
                if (v["completion_tokens"] or 0) > RUNAWAY:
                    hit[s].append(i)
                    print(f"| {s} | {i} | {v['juror']} | {v['completion_tokens']:,} | {v['latency_s'] or 0:.0f} s |")
    for s, its in hit.items():
        rest = [i for i in ids if i not in set(its)]
        cost = _spend(by[s], s, its)
        print(f"\n{s}: those {len(its)} decisions cost ${cost:.2f}, {cost / _spend(by[s], s, ids):.1%} of its "
              f"spend; without them it costs ${1000 * _spend(by[s], s, rest) / len(rest):.2f} per 1,000.")


def _failures(records: dict, ids):
    """(juror, dataset, error) for each failed call: a panel's failed votes, a single model's failed decisions."""
    for i in ids:
        r = records[i]
        if r.get("votes"):
            yield from ((v["juror"], r["dataset"], _cell(v["error"])) for v in r["votes"] if v["choice"] is None)
        elif r["pred"] is None:
            yield r.get("model", "–"), r["dataset"], _cell(r["error"])


def _cell(error: str | None) -> str:
    return (error or "")[:70].replace("|", "\\|").replace("\n", " ")


def _shipped(by, panel, ids, datasets) -> None:
    shipped = {d: [i for i in its if not by[panel][i]["needs_review"]] for d, its in datasets.items()}
    n_ship = sum(map(len, shipped.values()))
    own = _pooled(by[panel], shipped)
    wrong = [i for i in ids if not _right(by[panel][i])]
    caught = sum(bool(by[panel][i]["needs_review"]) for i in wrong) / len(wrong)
    print(f"\n## {panel}: shipped accuracy at {n_ship / len(ids):.1%} coverage\n")
    print(f"Ships {n_ship} of {len(ids)} decisions, {own:.1%} correct ({1000 * (1 - own):.0f} wrong per 1,000 "
          f"shipped), and sends {caught:.1%} of its wrong answers to review.\n")

    singles = {s: _confidence(by[s]) for s in SINGLES if s in by}
    rivals = dict(singles)
    jurors = sorted({v["juror"] for i in ids for v in by[panel][i]["votes"]})
    for j in jurors:
        rivals[f"{j} alone"] = {
            i: (v["confidence"] or 0, v["choice"] == by[panel][i]["label"])
            for i in ids for v in by[panel][i]["votes"] if v["juror"] == j
        }

    print("| Rival | Rival ships correctly | Ties at random: expected (worst to best) "
          "| Panel minus rival (95% bootstrap) |\n|---|---|---|---|")
    print(f"| ({panel} itself) | {own:.1%} | | |")
    rng = random.Random(0)
    for name, conf in rivals.items():
        point = _matched(conf, datasets, shipped)
        lo, mean, hi = _tie_range(conf, datasets, shipped)
        diffs = []
        for _ in range(BOOTSTRAP):
            sample = {d: [rng.choice(its) for _ in its] for d, its in datasets.items()}
            ship_s = {d: [i for i in its if not by[panel][i]["needs_review"]] for d, its in sample.items()}
            diffs.append(_pooled(by[panel], ship_s) - _matched(conf, sample, ship_s))
        diffs.sort()
        b_lo, b_hi = diffs[int(0.025 * BOOTSTRAP)], diffs[int(0.975 * BOOTSTRAP) - 1]
        print(f"| {name} | {point:.1%} | {mean:.1%} ({lo:.1%} to {hi:.1%}) "
              f"| {100 * b_lo:+.1f} to {100 * b_hi:+.1f} points |")

    print("\n| Single model at the same coverage | Wrong shipped, panel / single | $ per 1,000, panel / single "
          "| Break-even |\n|---|---|---|---|")
    panel_cost = 1000 * _spend(by[panel], panel, ids) / len(ids)
    panel_wrong = n_ship - round(own * n_ship)
    for s, conf in singles.items():
        right, total = _top(conf, datasets, shipped)
        single_cost = 1000 * _spend(by[s], s, ids) / len(ids)
        extra = panel_cost - single_cost  # dollars per 1,000 decisions
        avoided = 1000 * (total - right - panel_wrong) / len(ids)  # wrong decisions per 1,000 decisions
        if extra > 0 and avoided > 0:
            verdict = f"the panel pays off above ${extra / avoided:.3f} per wrong decision"
        elif extra < 0 and avoided < 0:
            verdict = f"{s} pays off above ${extra / avoided:.3f} per wrong decision"
        else:
            verdict = f"{'the panel' if extra <= 0 else s} is cheaper and ships no more wrong decisions"
        print(f"| {s} | {panel_wrong} / {total - right} | {panel_cost:.2f} / {single_cost:.2f} | {verdict} |")


def _head_to_head(by, panels, ids) -> None:
    print("\n## Panels head to head\n")
    print("Each panel ranked by juror agreement and shipping the same share; ties at the cutoff are broken "
          "at random, so the figures are expected values.\n")
    print("| Coverage | " + " | ".join(panels) + " |\n|---|" + "---|" * len(panels))
    for owner in panels:
        k = sum(not by[owner][i]["needs_review"] for i in ids)
        cells = [f"{_by_agreement(by[p], ids, k):.1%}" for p in panels]
        print(f"| {k / len(ids):.1%} ({owner}'s own) | " + " | ".join(cells) + " |")


def _by_class(by, setups, panels, its, positive: str) -> None:
    rates = {}
    for s in setups:
        pos = [i for i in its if by[s][i]["label"] == positive]
        neg = [i for i in its if by[s][i]["label"] != positive]
        rates[s] = (sum(_right(by[s][i]) for i in pos) / len(pos), sum(_right(by[s][i]) for i in neg) / len(neg))
    print(f"\n## Hate speech by class ({len(its)} items, sampled half {positive})\n")
    print(f"| Setup | Catches {positive} | Clears the rest | Accuracy if half are {positive} | If 10% are |")
    print("|---|---|---|---|---|")
    for s, (tp, tn) in rates.items():
        print(f"| {s} | {tp:.1%} | {tn:.1%} | {_mix(tp, tn, 0.5):.1%} | {_mix(tp, tn, 0.1):.1%} |")

    print(f"\nEach panel against each single model, by share of {positive} comments:\n")
    for a, b in itertools.product(panels, [s for s in SINGLES if s in by]):
        (tpa, tna), (tpb, tnb) = rates[a], rates[b]
        slope = (tpa - tpb) - (tna - tnb)  # how a's lead grows with the share of positives
        x = (tnb - tna) / slope if slope else math.inf
        if 0 < x < 1:
            low, high = (a, b) if tna > tnb else (b, a)
            line = f"equally accurate at {x:.0%} {positive}; {low} is more accurate below that, {high} above"
        else:
            line = f"{a if _mix(tpa, tna, 0.5) > _mix(tpb, tnb, 0.5) else b} is more accurate at every mix"
        only = [i for i in its if _right(by[a][i]) and not _right(by[b][i])]
        k = sum(by[a][i]["label"] == positive for i in only)
        agree = statistics.median(by[a][i]["human_agreement"] for i in only) if only else math.nan
        print(f"- {a} vs {b}: {line}. Of the {len(only)} items only {a} got right, {k} are {positive}; "
              f"median human agreement on them {agree:.2f}.")


def _right(r: dict) -> bool:
    return r["pred"] is not None and r["pred"] == r["label"]


def _spend(records: dict, setup: str, ids) -> float:
    """Dollars for the decisions in ids, priced as report.py prices them; nan if a price is unknown."""
    costs = [_cost(setup, records[i]) for i in ids]
    return math.nan if None in costs else sum(costs)


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


def _top(conf: dict, datasets: dict, shipped: dict) -> tuple[int, int]:
    """(right, shipped) for the rival's k most confident items per dataset, k = what the panel shipped."""
    right = total = 0
    for d, its in datasets.items():
        k = len(shipped[d])
        top = sorted(its, key=lambda i: -conf[i][0])[:k]
        right += sum(conf[i][1] for i in top)
        total += k
    return right, total


def _matched(conf: dict, datasets: dict, shipped: dict) -> float:
    """Pooled accuracy of the rival's k most confident items per dataset, k = what the panel shipped."""
    right, total = _top(conf, datasets, shipped)
    return right / total


def _tie_range(conf: dict, datasets: dict, shipped: dict) -> tuple[float, float, float]:
    """_matched at the worst order of the items tied at each cutoff, on average, and at the best."""
    lo = mean = hi = total = 0
    for d, its in datasets.items():
        k = len(shipped[d])
        if not k:
            continue
        ranked = sorted((conf[i] for i in its), key=lambda c: -c[0])
        cut = ranked[k - 1][0]
        above = sum(c[1] for c in ranked if c[0] > cut), sum(c[0] > cut for c in ranked)
        tied = [c[1] for c in ranked if c[0] == cut]
        need = k - above[1]
        lo += above[0] + max(0, need - (len(tied) - sum(tied)))
        mean += above[0] + need * sum(tied) / len(tied)
        hi += above[0] + min(need, sum(tied))
        total += k
    return lo / total, mean / total, hi / total


def _by_agreement(records: dict, ids: list, k: int) -> float:
    """Expected accuracy of the k items with the highest agreement, ties at the cutoff broken at random."""
    cut = sorted((records[i]["confidence"] for i in ids), reverse=True)[k - 1]
    above = [i for i in ids if records[i]["confidence"] > cut]
    tied = [i for i in ids if records[i]["confidence"] == cut]
    right = sum(_right(records[i]) for i in above)
    return (right + (k - len(above)) * sum(_right(records[i]) for i in tied) / len(tied)) / k


def _mix(tp: float, tn: float, share: float) -> float:
    """Accuracy when share of the items are positive, from the rates on each class."""
    return share * tp + (1 - share) * tn


def _sign_test(a: int, b: int) -> float:
    n, k = a + b, min(a, b)
    tail = sum(math.comb(n, x) for x in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


if __name__ == "__main__":
    main()
