# Benchmark results

Work in progress. Only one setup has run so far. Each section records what ran, how, and what to
be careful about.

## Pilot 1: Laya alone (2026-10-04)

**Setup.** Laya 0.3.27 (`convaiinnovations/laya`, Apache 2.0), self-hosted on CPU only
(AMD Ryzen 7 5800X3D, torch 2.14.1+cpu), `max_len=8192`, one decision at a time.
50 items per dataset, sampled with seed 0 (`python run.py --setups laya --n 50`).
Raw records: [`results/pilot.jsonl`](results/pilot.jsonl). Full table: [`results/pilot_report.md`](results/pilot_report.md).

| Dataset | Task | Options | Accuracy | Human AUROC | Latency p50 / p95 (CPU) |
|---|---|---|---|---|---|
| Measuring Hate Speech | Is this comment hate speech? | 2 | 82% | 0.75 | 0.14 / 0.22 s |
| BoolQ | Yes/no question about a passage | 2 | 80% | – | 0.22 / 0.35 s |
| ChaosNLI (MNLI) | Entailment, neutral or contradiction | 3 | 58% | 0.58 | 0.17 / 0.22 s |
| VitaminC | Does the evidence support the claim? | 3 | 54% | – | 0.16 / 0.22 s |
| JudgeBench | Which of two answers is correct? | 2 | 48% | – | 2.55 / 4.33 s |
| Banking77 | Which of 77 intents? | 77 | 30% | – | 0.47 / 0.51 s |

Cost: $0, self-hosted. Errors: none.

**Human AUROC** is measured on the datasets with several human labels per item. It shows how well
Laya's low confidence picks out items where humans disagreed (agreement under 80%):
0.5 is chance, 1.0 is perfect.

**Observations**

- **JudgeBench is beyond it.** It scores at chance (48%; always answering "A" would score 66% on
  this sample). With the default 512-token input, 49 of 50 items were cut off and it scored 62%,
  which was an artifact of the truncation. Every run now uses `max_len=8192`.
- **Many options hurt.** 30% on Banking77's 77 intents.
- **Its confidence tracks human disagreement on hate speech** (0.75), but barely on ChaosNLI (0.58).

**Caveats**

- **50 items is a small sample.** Each accuracy is uncertain by roughly ±10–14 points (95%
  interval). The full run uses 500 items per dataset.
- **Latency is CPU latency.** Laya is built for GPUs; its authors report about 33 ms per decision on a
  T4. Don't compare these latencies with API models.
- **Measuring Hate Speech is sampled 50/50** hateful / not hateful, because hateful comments are rare.
  Accuracy on the natural mix would differ.
- **ChaosNLI is licensed CC BY-NC 4.0** (non-commercial). The records here keep only item IDs,
  labels and predictions, not the text.
- **Laya's own documentation says it ships over-confident** and recommends recalibrating its
  probabilities on your data. This run uses them as they come.

## Still to run

| Setup | Needs |
|---|---|
| Free modeljury panel (Gemma 4 31B, Nemotron 3 Super, Inkling Small) | `OPENROUTER_API_KEY`, no credit |
| Paid modeljury panel (GPT-6 Luna, Gemini 3.5 Flash Lite, Mistral Small) | OpenRouter credit, about $0.25 for the pilot |
| Single large models (Claude Opus 5.5, GPT-6.1 Sol) | OpenRouter credit, about $6 for the pilot |
| Jev | `TYPESAFE_API_KEY` |
| Laya on a GPU | A free GPU, for realistic latency |

Comparisons between setups only mean something on the same sample, so every setup uses the same
seed-0 items.
