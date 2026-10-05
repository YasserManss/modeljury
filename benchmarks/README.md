# Benchmarks

Compares modeljury panels with single models and decision models (Laya, Jev) on public datasets:
accuracy, how well each one knows when to ask a human, cost and latency.
Results so far are in [RESULTS.md](RESULTS.md).

This folder is not part of the `modeljury` package and has its own dependencies.

## Setup

```sh
cd benchmarks
uv venv .venv
VIRTUAL_ENV=.venv uv pip install -r requirements.txt --index-strategy unsafe-best-match
```

## Run

```sh
USE_TF=0 .venv/bin/python run.py --setups laya --n 50 --out results/pilot.jsonl
.venv/bin/python report.py results/pilot.jsonl
```

Setups (see `setups.py`): `laya`, `panel-free`, `panel-mixed`, `large-claude`, `jev`, `panel-local`.
Paid setups read `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY` or `TYPESAFE_API_KEY`.
Rerunning with the same `--out` skips decisions already recorded.

Once the datasets are downloaded, set `HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1`. Otherwise the
`datasets` library checks Hugging Face for updates on every run, and that check can hang.

## Datasets

| Name | Source | License |
|---|---|---|
| boolq | `google/boolq` | CC BY-SA 3.0 |
| vitaminc | `tals/vitaminc` | CC BY-SA 3.0 |
| banking77 | PolyAI GitHub CSV | CC BY 4.0 |
| judgebench | `ScalerLab/JudgeBench` | MIT |
| chaosnli | `earino/chaosnli` (mirror of the authors' files) | CC BY-NC 4.0 |
| mhs | `ucberkeley-dlab/measuring-hate-speech` | CC BY 4.0 |

Datasets are downloaded at run time and never committed.
