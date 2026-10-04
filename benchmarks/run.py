"""Run setups over dataset samples and append one JSON record per decision.

    python run.py --setups panel-local laya --n 50
    python run.py --setups jev --n 500 --out results/full.jsonl

Re-running with the same --out skips decisions already recorded, so a long run can resume.
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import data
from setups import SETUPS


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--setups", nargs="+", default=["laya"], choices=list(SETUPS))
    p.add_argument("--datasets", nargs="+", default=list(data.LOADERS), choices=list(data.LOADERS))
    p.add_argument("--n", type=int, default=50, help="items per dataset")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--workers", type=int, default=4, help="items decided in parallel")
    p.add_argument("--out", type=Path, default=Path("results/pilot.jsonl"))
    args = p.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if args.out.exists():
        for line in args.out.read_text().splitlines():
            r = json.loads(line)
            done.add((r["setup"], r["id"]))

    samples = {name: data.sample(name, args.n, args.seed) for name in args.datasets}
    for setup_name in args.setups:
        setup = SETUPS[setup_name]()
        for name, items in samples.items():
            todo = [it for it in items if (setup_name, it["id"]) not in done]
            start = time.time()
            with ThreadPoolExecutor(args.workers) as pool, args.out.open("a") as f:
                for item, record in zip(todo, pool.map(lambda it: _decide(setup, it), todo)):
                    record.update(
                        setup=setup_name, id=item["id"], dataset=name, label=item["label"],
                        human_agreement=item["human_agreement"], n_options=len(item["options"]),
                    )
                    f.write(json.dumps(record) + "\n")
                    f.flush()
            print(f"{setup_name:13} {name:11} {len(todo):4} decisions in {time.time() - start:6.1f}s")


def _decide(setup, item: dict) -> dict:
    try:
        return setup.decide(item)
    except Exception as e:  # record and keep going; one bad item shouldn't stop a long run
        return dict(pred=None, needs_review=None, confidence=None, latency_s=None,
                    prompt_tokens=0, completion_tokens=0, error=f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
