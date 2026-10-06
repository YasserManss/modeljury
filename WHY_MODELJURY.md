# Why modeljury

**The question this answers: which of your AI's decisions can ship, and which need a person?**

Every number here is measured on 2,850 decisions from six public datasets, against two
alternatives — a frontier model and a purpose-built decision model — on identical items. The full
record, including where modeljury loses, is in [benchmarks/RESULTS.md](benchmarks/RESULTS.md).
The headline panel is `openjury`: five cheap open-weight models from five companies (DeepSeek V4.1
Flash, GLM 5.3 Flash, MiMo V2.6 Flash, Qwen3.8 Flash, Gemma 4 26B-A4B).

## The problem

Once AI makes decisions in a business process — refunds, moderation, triage, compliance checks,
reviewing AI output — there are two usual options, and both are bad:

- **Trust every decision.** Mistakes reach customers, and nobody knows which ones.
- **Have a person check everything.** Slow, costly, and it removes the reason for automating.

A confidence score helps less than it seems. A model that is confidently wrong looks exactly like a
model that is confidently right.

## What modeljury does

It asks a small panel of models instead of one. When they agree, the decision ships. When they
disagree, it goes to a person **with each dissenting model's reason**, so the reviewer knows where
to look.

```python
result.verdict       # "legit"
result.needs_review  # True
result.dissent       # [("claude-haiku-4.5", "fraud", "Shipping address changed after purchase")]
```

The idea of a panel of models isn't new (Verga et al., 2024, ["Replacing Judges with
Juries"](https://arxiv.org/abs/2404.18796)). What's measured here is how well disagreement works as
a flag for human review.

## Where it wins

### 1. Near-frontier reliability on what ships, at a tenth of the cost

openjury shipped 71% of decisions without review, and **89.6%** of those were right. Claude Opus 5.5,
shipping its most confident answers at the same rate, was right **90.5%** of the time (95% interval
on the difference: −2.3 to 0.0 points) — at **$5.79 per 1,000 decisions against $0.61**.

Against Jev, a purpose-built decision model, at the same rate: 89.6% against 87.1%
(+1.3 to +3.5 points). The advantage concentrates where judgment is hard:

| Task | openjury ships correctly | Jev ships correctly |
|---|---|---|
| Comparing two long answers (JudgeBench) | **96%** | 89% |
| Ambiguous inference (ChaosNLI) | **81%** | 73% |
| Hate speech | **84%** | 80% |

On long answer comparisons, **the error rate of what ships is under half Jev's**: 4% against 11%.
That is the shape of real review work — comparing a document to a policy, a response to a rubric,
a change to a standard. (Opus, at its most confident, shipped no errors here.)

### 2. It beats each of its own models

The obvious alternative to a panel is its best model alone, shipping its most confident answers.
Every panel tested beat every one of its jurors at the same automation rate. For openjury the margin
over its best juror is small (89.6% against 88.9%); for the closed panel it is clear (87.5% against
85.0%, +1.2 to +3.5 points).

### 3. It beats a frontier model on subjective judgment

On hate speech, where annotators themselves disagree, openjury was right **76%** of the time against
**71%** for Claude Opus 5.5 — 50 items where only the panel was right, against 28 the other way
(p = 0.02). What it shipped was right 84% of the time, against Opus's 78%.

One model has one set of blind spots. Five models from five companies do not share all of them.
Nothing scored well here — 76% is still 24% wrong — but the panel was wrong less often.

### 4. Open weights, no lock-in

Every openjury juror publishes its weights, so the panel can run inside your network, where neither
Jev nor Claude Opus 5.5 can. Be realistic about the hardware: openjury includes sparse models of
several hundred billion parameters, which is datacenter hardware. The smaller open panel (Qwen 3.6
35B-A3B, Gemma 4 26B-A4B, Nemotron 3.5 Lightning) shipped 87.2% correct at 66% coverage. These runs
went through OpenRouter; a self-hosted benchmark is still to do.

Any OpenAI-compatible endpoint works, plus Claude natively. If a provider raises prices, deprecates
a model, or has an outage, you change a string — you do not rebuild your pipeline.

### 5. Every flagged decision comes with reasons

Jev and Opus return a number. modeljury returns the dissenting juror, its answer, and its one-line
reason. A reviewer starts from "the shipping address changed after purchase", not from "0.62".

That is also the audit trail: for every decision, who voted what and why.

### 6. No single point of failure

In the full run, Claude Opus 5.5 returned nothing on one item — its safety classifier declined an
exam question about viral virulence. A single model that refuses returns nothing at all.

When a juror refuses, errors, or answers invalidly, the others still vote and the decision is
**flagged, not lost**. openjury's 21 failed juror votes in 14,250 calls were all absorbed this way,
including five safety-filter refusals on hate-speech items.

## What it does not do

Stated plainly, because anyone evaluating this will check:

- **It is not the most accurate option overall.** Claude Opus 5.5 scored 83.1% against openjury's
  80.1%, and wins clearly on tasks with many options (banking intents, 90% vs 79%) and on comparing
  long answers (95% vs 83%).
- **It is not the cheapest or fastest.** Jev costs $0.03 per 1,000 decisions and answers in 0.55 s.
  openjury costs about 20 times more and takes about 4 s typically, 17 s at p95.
- **It does not make AI accurate on subjective questions.** On hate speech every setup scored
  71–76%. Panels can agree and still be wrong; a human stays essential there.
- **Panels wait for their slowest juror.** In the benchmark the slowest openjury decision took
  1,915 s, because a juror with no `max_tokens` set kept generating. Set `max_tokens` on every
  juror to bound that.

**The honest summary: modeljury is not the most accurate or the cheapest way to make a decision.
It is a cheap, reliable way to know which decisions you can trust — and it tells you why.**

## The economics

Against Jev at the same automation rate, openjury costs **$0.58 more per 1,000 decisions** and ships
about **17 fewer wrong decisions per 1,000 decisions** (210 errors shipped against 260, out of 2,850).

It pays for itself if a single wrong decision costs you more than **about 3 cents**. (The closed
panel, at $1.18 per 1,000, breaks even at about 11 cents.)

A wrongly approved refund, a missed policy violation, a bad merge, a compliance miss: all cost more
than 3 cents.

## How to evaluate it

Four weeks, one real decision flow, three numbers:

1. **Automation rate** — what share ships without review. Expect roughly 65–75%.
2. **Escaped errors** — wrong decisions that shipped, against your current process. Expect roughly
   10 per 100 shipped on hard tasks; measure yours.
3. **Review time** — how long a reviewer takes with the dissent reasons, against without.

modeljury is MIT-licensed and installs with `pip install modeljury`. There is nothing to procure
and nothing to lock into for the pilot.

## Reproducing these numbers

Everything is in [benchmarks/](benchmarks/): the datasets (all public), the setups, the runner, and
the raw per-decision records. `python report.py results/full.jsonl` prints the per-dataset tables,
and `python stats.py results/full.jsonl` the paired tests, shipped-accuracy comparisons and
bootstrap intervals.
