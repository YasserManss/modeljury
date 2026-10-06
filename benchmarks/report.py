"""Summarise run.py results as markdown tables.

    python report.py results/pilot.jsonl

For each dataset and setup:
  accuracy        right answers / all items (no answer counts as wrong)
  coverage        share shipped without review (panels only)
  shipped acc     accuracy on the shipped items
  error recall    share of wrong answers that were flagged for review
  matched acc     for setups that can't flag (single models, Laya, Jev): accuracy on
                  their most confident items, at the same coverage as the reference panel
  latency         p50 / p95 seconds per decision (a panel waits for its slowest juror)
  $/1k            cost per 1,000 decisions from recorded tokens and PRICES
  human AUROC     on datasets with several human labels: how well the flag (or low
                  confidence) picks out items where humans disagreed; 0.5 is chance

"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

# $ per million tokens (input, output). Self-hosted and free models are 0.
PRICES = {
    "panel-local": (0, 0),
    "panel-free": (0, 0),
    "laya": (0, 0),
    "jev": (0.042, 0),
    "jev-openrouter": (0.042, 0),
    "large-claude": (4.0, 20.0),
}
# OpenRouter models, priced per juror call. List price, $ per million tokens (input, output), 2026-10-05.
MODEL_PRICES = {
    "openai/gpt-6-luna": (0.10, 0.50),
    "google/gemini-3.5-flash-lite": (0.30, 2.50),
    "anthropic/claude-haiku-4.5": (1.00, 5.00),
    "anthropic/claude-opus-5.5": (4.0, 20.0),
    "qwen/qwen3.6-35b-a3b": (0.15, 1.00),
    "google/gemma-4-26b-a4b-it": (0.09, 0.30),
    "nvidia/nemotron-3.5-lightning": (0.06, 0.16),
    "openai/gpt-6.1-sol": (2.0, 10.0),
    "deepseek/deepseek-v4.1-flash": (0.30, 1.20),
    "z-ai/glm-5.3-flash": (0.15, 0.50),
    "xiaomi/mimo-v2.6-flash": (0.14, 0.28),
    "qwen/qwen3.8-flash": (0.15, 0.47),
}
AMBIGUOUS_BELOW = 0.8  # human agreement under this counts as "humans disagreed"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path)
    p.add_argument("--reference", default=None, help="panel whose coverage sets matched acc")
    args = p.parse_args()

    records = [json.loads(line) for line in args.results.read_text().splitlines()]
    by = defaultdict(list)
    for r in records:
        by[(r["dataset"], r["setup"])].append(r)

    datasets = sorted({d for d, _ in by})
    setups = sorted({s for _, s in by}, key=lambda s: (s.startswith("panel") is False, s))
    reference = args.reference or next((s for s in setups if s.startswith("panel") and "/" not in s), None)

    print(f"Results from {args.results}  (reference panel for matched acc: {reference})\n")
    for d in datasets:
        ref_cov = _coverage(by.get((d, reference), []))
        human = any(r["human_agreement"] is not None for r in by[(d, setups[0])] if (d, setups[0]) in by)
        print(f"### {d}\n")
        head = "| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |"
        if human:
            head += " human AUROC |"
        print(head)
        print("|" + "---|" * (head.count("|") - 1))
        for s in setups:
            rs = by.get((d, s))
            if rs:
                print(_row(s, rs, ref_cov, human))
        for s in setups:
            cut = sum(1 for r in by.get((d, s), []) if r.get("truncated"))
            if cut:
                print(f"\n⚠ {s}: input was cut off on {cut} items, so its score here is not comparable.")
        print()


def _row(setup: str, rs: list[dict], ref_cov: float | None, human: bool) -> str:
    n = len(rs)
    correct = [r["pred"] == r["label"] for r in rs]
    acc = sum(correct) / n
    flags = [r.get("needs_review") for r in rs]
    can_flag = all(f is not None for f in flags)

    cov = shipped = recall = matched = "–"
    if can_flag:
        ship = [c for c, f in zip(correct, flags) if not f]
        cov = _pct(len(ship) / n)
        shipped = _pct(sum(ship) / len(ship)) if ship else "–"
        errors = [f for c, f in zip(correct, flags) if not c]
        recall = _pct(sum(errors) / len(errors)) if errors else "–"
    elif ref_cov is not None:
        k = round(ref_cov * n)
        ranked = sorted(zip(rs, correct), key=lambda x: -(_conf(x[0]) or 0))[:k]
        matched = _pct(sum(c for _, c in ranked) / k) if k else "–"

    lats = sorted(r["latency_s"] for r in rs if r.get("latency_s") is not None)
    lat = f"{_q(lats, 0.5):.2f} / {_q(lats, 0.95):.2f}" if lats else "–"

    per_decision = [_cost(setup, r) for r in rs]
    cost = "?" if None in per_decision else f"{statistics.mean(per_decision) * 1000:.2f}"

    row = f"| {setup} | {n} | {_pct(acc)} | {cov} | {shipped} | {recall} | {matched} | {lat} | {cost} |"
    if human:
        row += f" {_human_auroc(rs, can_flag)} |"
    return row


def _cost(setup: str, r: dict) -> float | None:
    """Dollars for one decision, or None if a price is unknown."""
    if r.get("votes"):  # a panel: price each juror's call by its model
        total = 0.0
        for v in r["votes"]:
            price = MODEL_PRICES.get(v["juror"].split("#")[0]) or PRICES.get(setup)
            if price is None:
                return None
            total += (v["prompt_tokens"] * price[0] + v["completion_tokens"] * price[1]) / 1e6
        return total
    price = MODEL_PRICES.get(r.get("model", "")) or PRICES.get(setup.split("/")[0])
    if price is None:
        return None
    return (r["prompt_tokens"] * price[0] + r["completion_tokens"] * price[1]) / 1e6


def _coverage(rs: list[dict]) -> float | None:
    flags = [r.get("needs_review") for r in rs]
    if not rs or any(f is None for f in flags):
        return None
    return sum(not f for f in flags) / len(flags)


def _conf(r: dict) -> float | None:
    return r.get("probability") if r.get("probability") is not None else r.get("confidence")


def _human_auroc(rs: list[dict], can_flag: bool) -> str:
    """AUROC of 'unsure' score for separating human-ambiguous items from clear ones."""
    pts = []
    for r in rs:
        if r["human_agreement"] is None:
            continue
        if can_flag:
            score = (1 - (r.get("confidence") or 0)) + (1 if r["needs_review"] else 0)
        elif _conf(r) is not None:
            score = 1 - _conf(r)
        else:
            continue
        pts.append((score, r["human_agreement"] < AMBIGUOUS_BELOW))
    pos = [s for s, amb in pts if amb]
    neg = [s for s, amb in pts if not amb]
    if not pos or not neg:
        return "–"
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return f"{wins / (len(pos) * len(neg)):.2f}"


def _q(xs: list[float], q: float) -> float:
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def _pct(x: float) -> str:
    return f"{x:.0%}"


if __name__ == "__main__":
    main()
