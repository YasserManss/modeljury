# Benchmark results

Five setups, 2,850 decisions each, on the same items. Every number below is measured, not estimated.
Laya only ran in the pilot (50 items per dataset) and is marked partial.

## Full run (2026-10-05, openjury added 2026-10-06)

**Setup.** 500 items per dataset, 350 for JudgeBench, which has only that many usable pairs; seed 0;
the same items for every setup. Raw records: [`results/full.jsonl`](results/full.jsonl).
Full table: [`results/full_report.md`](results/full_report.md).

| Name | What it is |
|---|---|
| Closed panel | modeljury with GPT-6 Luna, Gemini 3.5 Flash Lite, Claude Haiku 4.5 (`panel-mixed`) |
| openjury | modeljury with five cheap open-weight models, one per company: DeepSeek V4.1 Flash, GLM 5.3 Flash, MiMo V2.6 Flash, Qwen3.8 Flash, Gemma 4 26B-A4B (`openjury`) |
| Open panel | modeljury with Qwen 3.6 35B-A3B, Gemma 4 26B-A4B, Nemotron 3.5 Lightning, reasoning off (`panel-open`) |
| Jev | TypeSafe Jev 1.13 via OpenRouter's SystemOne endpoint (`jev-openrouter`) |
| Opus | Claude Opus 5.5 alone, same prompt and parser as a juror (`large-opus`) |

All models were reached through OpenRouter, so latency is comparable. Cost per decision uses
OpenRouter list prices on 2026-10-05 and the tokens each call actually used.

Reasoning is off for every openjury juror except GLM 5.3 Flash, which rejects
`reasoning: {enabled: false}` with a 400 and runs at `effort: minimal` instead.

### Overall

| Setup | Accuracy (95% CI) | Latency p50 / p95 / max | $ per 1,000 decisions |
|---|---|---|---|
| Opus | 83.1% ± 1.4 | 5.39 / 9.38 / 65.0 s | 5.79 |
| openjury | 80.1% ± 1.5 | 3.84 / 17.2 / 1915.1 s | 0.61 |
| Closed panel | 79.4% ± 1.5 | 2.86 / 7.92 / 49.1 s | 1.18 |
| Jev | 78.4% ± 1.5 | 0.55 / 0.69 / 1.4 s | 0.03 |
| Open panel | 76.4% ± 1.6 | 1.67 / 5.20 / 183.8 s | 0.23 |

**Both panels are entirely open-weight and can run on your own hardware or on-prem.** Every openjury
juror publishes its weights — `deepseek-ai/DeepSeek-V4.1-Flash`, `zai-org/GLM-5.3-Flash`,
`XiaomiMiMo/MiMo-V2.6-Flash-RL`, `Qwen/Qwen3.8-Flash-Next`, `google/gemma-4-26B-A4B-it` — as does
every juror in the open panel. Run that way there are no API fees and no per-decision cost, and no
data leaves your network. The dollar figures above are what OpenRouter charged to put every setup on
identical items under identical conditions. Note the footprint: MiMo V2.6 Flash is 309B total
parameters (15B active) and DeepSeek V4.1 Flash is also a sparse mixture-of-experts, so this is
datacenter hardware, not a workstation. Neither Jev nor Claude Opus 5.5 can be self-hosted at all.

Paired tests, counting items where exactly one of the two was right:

| Comparison | Split | p |
|---|---|---|
| Opus vs openjury | 229 vs 143 | < 0.0001 (Opus better) |
| Opus vs closed panel | 243 vs 137 | < 0.0001 (Opus better) |
| Opus vs Jev | 301 vs 165 | < 0.0001 (Opus better) |
| openjury vs open panel | 222 vs 116 | < 0.0001 (openjury better) |
| openjury vs Jev | 194 vs 144 | 0.008 (openjury better) |
| openjury vs closed panel | 136 vs 116 | 0.23 (tie) |
| Closed panel vs Jev | 204 vs 174 | 0.14 (tie) |
| Jev vs open panel | 248 vs 192 | 0.009 (Jev better) |

openjury's accuracy edge over the closed panel is **not** statistically distinguishable from zero.
Its advantage is in the flag, below, not in the verdict.

### Accuracy by dataset

| Dataset | n | Opus | openjury | Closed panel | Jev | Open panel |
|---|---|---|---|---|---|---|
| BoolQ | 500 | 92% | **93%** | 91% | 91% | 90% |
| VitaminC | 500 | 85% | 83% | 81% | 80% | 79% |
| JudgeBench | 350 | **95%** | 83% | 82% | 80% | 78% |
| Banking77 | 500 | **90%** | 79% | 79% | 80% | 73% |
| ChaosNLI | 500 | 69% | 69% | 68% | 65% | 66% |
| Measuring Hate Speech | 500 | 71% | **76%** | **76%** | 75% | 73% |

All three panels beat Opus on hate speech, where annotators themselves disagree; the closed panel's
margin there is 46 items to 23 (p = 0.008). openjury is the only setup to beat Opus on BoolQ. Opus
wins JudgeBench and Banking77 decisively.

### The flag: how reliable is what ships without review?

A panel ships the decisions its jurors agree on. For each dataset the single models ship the same
number of decisions, their most confident ones, and all are then scored on what they shipped.

Each single model is ranked by its own confidence signal: Jev by the probability it assigns the
winning option, Opus by the confidence it states in its reply. Items with equal confidence are
ordered arbitrarily (30% of Jev's answers carry probability 1.0, 13% of Opus's carry 0.85). The
panels use their own flag, not a confidence score.

openjury, shipping 71% of decisions (2,012 of 2,850):

| Dataset | openjury | Jev | Opus |
|---|---|---|---|
| BoolQ | 95% | 96% | 96% |
| VitaminC | 90% | 88% | 91% |
| JudgeBench | **96%** | 89% | 100% |
| Banking77 | 92% | 92% | 98% |
| ChaosNLI | **81%** | 73% | 81% |
| Measuring Hate Speech | **84%** | 80% | 78% |
| **Pooled** | **89.6%** | 86.6% | 92.0% |

Differences in pooled shipped accuracy, 95% bootstrap intervals:
openjury minus Jev **+1.0 to +5.0 points**; openjury minus Opus −4.3 to −0.7 points.

Closed panel, shipping 74% of decisions:

| Dataset | Closed panel | Jev | Opus |
|---|---|---|---|
| BoolQ | 94% | 96% | 96% |
| VitaminC | 90% | 88% | 91% |
| JudgeBench | **95%** | 89% | 100% |
| Banking77 | 89% | 89% | 98% |
| ChaosNLI | **77%** | 71% | 80% |
| Measuring Hate Speech | **81%** | 80% | 77% |
| **Pooled** | **87.5%** | 86.1% | 90.2% |

Differences in pooled shipped accuracy, 95% bootstrap intervals:
closed panel minus Jev **+0.4 to +2.7 points**; closed panel minus Opus −3.6 to −1.5 points.

Open panel, shipping 66% of decisions: pooled 87.2%, against Jev 88.3% (−2.1 to +0.5) and
Opus 91.1% (−5.5 to −2.9). It wins ChaosNLI (78% vs 74%) and VitaminC (92% vs 91%) against Jev.

**The two panels head to head.** They ship different shares, so comparing their pooled numbers
directly favours openjury, which ships less. Ranking both by juror agreement and holding coverage
equal:

| Coverage | openjury ships correctly | Closed panel ships correctly |
|---|---|---|
| 70.6% (openjury's own) | **89.4%** | 87.5% |
| 73.8% (closed panel's own) | **88.6%** | 87.5% |

Per 1,000 decisions shipped without review: openjury 104 wrong, closed panel 125, open panel 128.

### Catching its own mistakes

Share of a setup's wrong answers that it sent to review (`error recall`):

| Dataset | openjury | Closed panel | Open panel |
|---|---|---|---|
| Banking77 | 72% | 58% | **77%** |
| VitaminC | 53% | 59% | **74%** |
| ChaosNLI | 68% | 56% | **69%** |
| JudgeBench | **85%** | 82% | 59% |
| Measuring Hate Speech | **52%** | 42% | 48% |
| BoolQ | 38% | **40%** | 39% |
| Pooled | **63.0%** | 55.4% | 63.9% |

Single models have no equivalent: they return an answer and a confidence score, with no reasons.

### Reliability

| Setup | Failures | Decisions with no verdict |
|---|---|---|
| Jev | 0 | 0 |
| Opus | 1 safety-classifier refusal | 1 |
| Closed panel | 0 | 27 hung juries |
| openjury | 21 failed juror votes of 14,250 calls (0.15%) | 16 hung juries |
| Open panel | 2 invalid answers, both flagged | 72 hung juries and invalid answers |

Opus returned empty content with `finish_reason: content_filter` on one JudgeBench item, an exam
question about viral virulence. The panels have no single point of failure: when a juror refuses or
errors, the others still vote and the decision is flagged rather than lost. openjury's 21 failures
were spread across all five jurors (Qwen 11, MiMo 5, DeepSeek 3, GLM 1, Gemma 1) and every one was
absorbed this way. All five of MiMo's were its own safety filter declining hate-speech items
("the request was rejected because it was considered high risk") — the same failure that cost Opus a
decision outright, except the panel still returned one.

**Runaway generations.** Three of openjury's 2,850 decisions had a juror generate until it hit its
context limit — 131,072 tokens twice (GLM, DeepSeek) and 65,536 once (Gemma) — on long JudgeBench
items, despite reasoning being off. Those three cases cost $0.25, which is 14% of openjury's total
spend, and produced the 1,915-second worst-case latency. Without them the panel costs $0.52 per
1,000 instead of $0.61. The cause is that no `max_tokens` is set for these jurors, so a model that
starts looping can generate to a million-token context. p99 latency is 45 s and only 22 of 2,850
decisions took over 60 s, so the tail is narrow but extreme. **Any production panel should set a
hard `max_tokens` per juror.**

No rate limits in any run. Total cost of the full run: about $22.43, of which openjury was $1.73.

## Pilots (50 items per dataset)

Earlier, smaller runs, kept for the record. Only Laya has no full-run results.

## Pilot 1: Laya alone (2026-10-04) — partial

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

## Pilot 2: modeljury panel (2026-10-05)

**Setup.** Panel of the fastest model from each of three companies, via OpenRouter:
GPT-6 Luna (no temperature setting), Gemini 3.5 Flash Lite and Claude Haiku 4.5 (temperature 0).
Same seed-0 items as Pilot 1, 4 decisions in parallel. 300 decisions, 0 juror failures, about $0.37.
"GPT-6 Luna alone" is the panel's first juror, read from the same calls.

| Dataset | Panel accuracy | Ships without review | Accuracy of shipped | Errors flagged | GPT-6 Luna alone | Luna at the same coverage | Laya |
|---|---|---|---|---|---|---|---|
| BoolQ | 92% | 88% | 95% | 50% | 96% | 98% | 80% |
| VitaminC | 84% | 80% | 95% | 75% | 82% | 88% | 54% |
| JudgeBench | 74% | 52% | 96% | 92% | 88% | 96% | 46% |
| Banking77 | 70% | 78% | 82% | 53% | 80% | 82% | 30% |
| ChaosNLI | 66% | 54% | 67% | 47% | 48% | 48% | 58% |
| Measuring Hate Speech | 74% | 78% | 77% | 31% | 70% | 72% | 82% |

"Luna at the same coverage" ships Luna's most confident answers, using its self-reported
confidence, as many as the panel ships, and scores those.

| Juror | Accuracy (all 300) | Latency median / p95 / max |
|---|---|---|
| GPT-6 Luna | 77% | 2.8 / 8.6 / 22.7 s |
| Gemini 3.5 Flash Lite | 75% | 1.2 / 2.0 / 4.4 s |
| Claude Haiku 4.5 | 75% | 1.5 / 2.5 / 6.7 s |

Panel cost: $0.66–3.33 per 1,000 decisions (most of it Haiku), against $0.05–0.41 for Luna alone.
Panel latency (it waits for the slowest juror): median 2.2–3.0 s, 6.7 s on JudgeBench; p95 up to 22 s on JudgeBench.

**Observations**

- **The flag works on checkable tasks.** On BoolQ, VitaminC and JudgeBench, shipped decisions are
  95–96% correct, and on JudgeBench `needs_review` caught 92% of the errors.
- **The panel's verdict doesn't beat its best juror.** Luna alone is more accurate on BoolQ, Banking77
  and JudgeBench (88% vs 74%: the two weaker jurors outvoted it). At equal coverage the panel matches
  or beats Luna's self-reported confidence on 5 of 6 datasets, losing on BoolQ (95% vs 98%).
- **Weak on subjective tasks.** On hate speech the panel was often unanimously wrong (31% of errors
  flagged), and on ChaosNLI its flags barely track human disagreement (AUROC 0.54).
  Laya does better on hate speech (82%).

**Caveats** are as for Pilot 1: 50 items per dataset (about ±10–14 points), and Laya's latency is CPU.

**Earlier attempts, discarded:** Mistral Small was rate-limited on OpenRouter (166 of 300 calls failed);
Muse Glimmer 30B and GLM 5.3 Flash reasoned at length (calls up to 70+ s); Llama 4 Scout often ignored
the JSON format; the free models were blocked or rate-limited.

## Pilot 3: Claude Opus 5.5 alone (2026-10-05) — superseded by the full run

**Setup.** `anthropic/claude-opus-5.5` via OpenRouter, no temperature setting (it rejects one),
thinking on (it can't be turned off), `max_tokens` 16000. Same prompt and parser as a modeljury juror,
same seed-0 items. 300 decisions, 0 errors, about $1.87.

| Dataset | Panel accuracy | Opus accuracy | Panel's shipped accuracy | Opus at the same coverage | Panel $/1k | Opus $/1k | Panel latency p50 / p95 | Opus latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|
| BoolQ | 92% | 94% | 95% | 95% | 0.75 | 3.21 | 2.5 / 4.2 s | 4.5 / 8.9 s |
| VitaminC | 84% | 90% | 95% | 95% | 0.70 | 3.96 | 2.5 / 4.4 s | 5.2 / 7.7 s |
| JudgeBench | 74% | 90% | 96% | 100% | 3.33 | 15.74 | 6.7 / 22.3 s | 7.1 / 14.2 s |
| Banking77 | 70% | 90% | 82% | 92% | 1.44 | 6.51 | 3.0 / 5.1 s | 4.7 / 7.4 s |
| ChaosNLI | 66% | 68% | 67% | 78% | 0.73 | 4.30 | 3.0 / 5.6 s | 5.8 / 10.4 s |
| Measuring Hate Speech | 74% | 62% | 77% | 72% | 0.66 | 3.96 | 2.2 / 4.0 s | 5.6 / 10.0 s |

Overall accuracy: panel 77%, Opus 82%, Laya 58%.
Human AUROC (how well low confidence or the flag finds items humans disagreed on):
Opus 0.53 on ChaosNLI and 0.75 on hate speech, panel 0.54 and 0.57.

**Observations**

- **Opus is more accurate overall** (82% vs 77%) and on 5 of 6 datasets, most clearly on Banking77
  (77 options) and JudgeBench.
- **On checkable tasks the panel ships about as reliably as Opus.** At equal coverage they tie on
  BoolQ and VitaminC (95%), and Opus leads on JudgeBench (100% vs 96%).
- **The panel is about 4–6 times cheaper and roughly twice as fast** (median), except JudgeBench's
  slowest calls, where Opus is better (p95 14 s vs 22 s).
- **On hate speech the panel beats Opus** (74% vs 62%), but Opus's confidence tracks human
  disagreement better there (0.75 vs 0.57).
- **Opus's self-reported confidence is a strong flag:** at equal coverage it matches or beats the
  panel's flag on 5 of 6 datasets.

**Caveats** as before: 50 items per dataset, so differences under about 15 points may be noise.

## Pilot 4: open-weights panel (2026-10-05)

**Setup.** Qwen 3.6 35B-A3B, Gemma 4 26B-A4B and Nemotron 3.5 Lightning via OpenRouter,
temperature 0, reasoning off. Same seed-0 items. 300 decisions, 0 juror failures, under $0.10.
Muse Glimmer 30B was tried as the third juror and dropped: it rejects reasoning off, and at the
lowest effort it took 5.7 s typically and up to 26 s.

## Pilot 5: Jev (2026-10-05)

**Setup.** `typesafe/jev-1.13` through OpenRouter's SystemOne endpoint
(`https://openrouter.ai/api/v1/systemone`, the same request format as TypeSafe's API), one choice
question per item. Same seed-0 items. 300 decisions, 0 errors, about $0.01 in total.

## All setups in the pilot (50 items per dataset)

| Setup | Accuracy (300) | Latency p50 / p95 | $ per 1k decisions |
|---|---|---|---|
| Claude Opus 5.5 | 82% | 5.5 / 9.9 s | 3.21–15.74 |
| Closed panel (GPT-6 Luna, Gemini 3.5 Flash Lite, Claude Haiku 4.5) | 77% | 2.8 / 8.7 s | 0.66–3.33 |
| Open panel (Qwen 3.6 35B-A3B, Gemma 4 26B-A4B, Nemotron 3.5 Lightning) | 76% | 1.7 / 5.5 s | 0.11–0.80 |
| Jev 1.13 | 76% | 0.5 / 0.7 s | 0.01–0.08 |
| Laya 0.3.27 (CPU), partial | 58% | 0.2 / 3.0 s | 0 |

Accuracy, then shipped accuracy (panels) or accuracy of the most confident answers at the closed
panel's coverage (single models):

| Dataset | Opus | Closed panel | Open panel | Jev | Laya |
|---|---|---|---|---|---|
| BoolQ | 94% / 95% | 92% / 95% | 88% / 93% | 90% / 95% | 80% / 80% |
| VitaminC | 90% / 95% | 84% / 95% | 86% / 95% | 86% / 95% | 54% / 60% |
| JudgeBench | 90% / 100% | 74% / 96% | 70% / 68% | 72% / 88% | 46% / 42% |
| Banking77 | 90% / 92% | 70% / 82% | 66% / 87% | 72% / 82% | 30% / 38% |
| ChaosNLI | 68% / 78% | 66% / 67% | 74% / 82% | 64% / 67% | 58% / 59% |
| Measuring Hate Speech | 62% / 72% | 74% / 77% | 74% / 79% | 74% / 74% | 82% / 87% |

The open panel ships its own share of decisions (44–84%), so its second numbers are not at
exactly the closed panel's coverage.

**Observations**

- **Jev is the strongest competitor:** the same overall accuracy as either panel, 3–6 times faster
  and 10–100 times cheaper, and at equal coverage it ships about as reliably as the closed panel on
  4 of 6 datasets.
- **The closed panel's clearest win over Jev is JudgeBench** (long answer comparisons): 96% shipped
  accuracy against 88% for Jev at the same coverage.
- **The open panel matches the closed one on accuracy at about a fifth of the cost and is faster.**
  Its flag is better on ChaosNLI and Banking77 and poor on JudgeBench (68% shipped accuracy).
- **Opus remains the most accurate**, at the highest cost and latency.

## Still to run

| Setup | Needs |
|---|---|
| Laya, full run on a GPU | A free GPU |
| A second large model (GPT-6.1 Sol) | About $15 |
| Self-hosted open panel, for latency and throughput | A GPU server |

Comparisons between setups only mean something on the same sample, so every setup uses the same
seed-0 items.
