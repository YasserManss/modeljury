# Why modeljury

**The question this answers: which of your AI's decisions can ship, and which need a person?**

Every number here is measured on 2,850 real decisions across six public datasets, against two
alternatives — a frontier model and a purpose-built decision model — on identical items. The full
record, including where modeljury loses, is in [benchmarks/RESULTS.md](benchmarks/RESULTS.md).

## The problem

Once AI makes decisions in a business process — refunds, moderation, triage, compliance checks,
reviewing AI output — there are two usual options, and both are bad:

- **Trust every decision.** Mistakes reach customers, and nobody knows which ones.
- **Have a person check everything.** Slow, costly, and it removes the reason for automating.

A confidence score doesn't solve this. A model that is confidently wrong looks exactly like a model
that is confidently right.

## What modeljury does

It asks a small panel of models instead of one. When they agree, the decision ships. When they
disagree, it goes to a person **with each dissenting model's reason**, so the reviewer knows where
to look.

```python
result.verdict       # "legit"
result.needs_review  # True
result.dissent       # [("claude-haiku-4.5", "fraud", "Shipping address changed after purchase")]
```

## Where it wins

### 1. It ships more reliable decisions than a purpose-built decision model

At the same level of automation — both shipping 74% of decisions without review — what the panel
shipped was right **87.5%** of the time, against **86.1%** for Jev, a specialist decision model
(95% interval on the difference: **+0.4 to +2.7 points**).

The advantage concentrates where judgment is hard:

| Task | modeljury ships correctly | Jev ships correctly |
|---|---|---|
| Comparing two long answers (JudgeBench) | **95%** | 89% |
| Ambiguous inference (ChaosNLI) | **77%** | 71% |
| Hate speech | **81%** | 80% |

On long answer comparisons, **the error rate of what ships is roughly halved**: 5% against 11%.
That is the shape of real review work — comparing a document to a policy, a response to a rubric,
a change to a standard.

### 2. It beats a frontier model on subjective judgment

On hate speech, where annotators themselves disagree, the panel was right **76%** of the time
against **71%** for Claude Opus 5.5 — 46 items where only the panel was right, against 23 the other
way (p = 0.008). What it shipped was right 81% of the time, against Opus's 77%.

One model has one set of blind spots. Three models from three companies do not share all of them.
Nothing scored well here — the panel's 76% is still 24% wrong — but the panel was wrong less often.

### 3. One fifth the cost of a frontier model, twice the speed

| | Claude Opus 5.5 | modeljury closed panel |
|---|---|---|
| Cost per 1,000 decisions | $5.79 | **$1.18** |
| Typical latency | 5.4 s | **2.9 s** |
| Accuracy of shipped decisions | 90.2% | 87.5% |

**4.9× cheaper and 1.9× faster, for 2.7 points of shipped accuracy.** Whether that trade is worth it
is a business decision, and it is yours to make per workflow — not a limit of the tool.

### 4. It can run practically for free, on your own hardware

The open panel uses only open-weight models (Qwen, Gemma, Nemotron). Run on your own hardware it has
**no API fees and no per-decision cost**, and no data leaves your network. It still scored **76.4%**,
and its flag shipped decisions that were right **87.2%** of the time — 0.3 points off what the paid
closed panel ships, and 1.1 points off the specialist model.

On most tasks it is also the best of any setup at catching its own mistakes:

| Task | Open panel flagged | Closed panel flagged |
|---|---|---|
| Banking intent (77 options) | **77%** | 58% |
| Evidence checking | **74%** | 59% |
| Ambiguous inference | **69%** | 56% |
| Comparing two long answers | 59% | **82%** |

For regulated industries — healthcare, finance, government — this matters: neither Jev nor Claude
Opus 5.5 can run inside your network, and the open panel can.

### 5. Every flagged decision comes with reasons

Jev and Opus return a number. modeljury returns the dissenting juror, its answer, and its one-line
reason. A reviewer starts from "the shipping address changed after purchase", not from "0.62".

That is also the audit trail: for every decision, who voted what and why.

### 6. No single point of failure

In the full run, Claude Opus 5.5 returned nothing on one item — its safety classifier declined an
exam question about viral virulence (`finish_reason: content_filter`). A single model that refuses
returns nothing at all.

When a juror refuses, errors, or answers invalidly, the panel's other jurors still vote and the
decision is **flagged, not lost**. Two invalid juror answers in the open panel's full run were
caught and routed to review automatically.

### 7. No vendor lock-in

Any OpenAI-compatible endpoint, plus Claude natively. Swap a juror in one line. If a provider raises
prices, deprecates a model, or has an outage, you change a string — you do not rebuild your pipeline.

## What it does not do

Stated plainly, because anyone evaluating this will check:

- **It is not the most accurate option overall.** Claude Opus 5.5 scored 83.1% against the closed
  panel's 79.4%, and wins clearly on tasks with many options (banking intents, 90% vs 79%) and on
  comparing long answers (95% vs 82%).
- **It is not the cheapest or fastest.** Jev costs $0.03 per 1,000 decisions and answers in 0.55 s.
  The closed panel is ~40× more expensive and ~5× slower.
- **It does not make AI accurate on subjective questions.** On hate speech every setup scored
  71–76%. Panels can agree and still be wrong; a human stays essential there.
- **Panels have a long tail.** The slowest single decision took 49 s (closed) and 184 s (open),
  because a panel waits for its slowest juror.

**The honest summary: modeljury is not the most accurate or the cheapest way to make a decision.
It is the most reliable way to know which decisions you can trust — and the only one that tells you
why.**

## The economics

The closed panel costs **$1.15 more per 1,000 decisions** than the cheapest alternative, and ships
about **14 fewer wrong decisions per 1,000** (125 errors per 1,000 shipped against 139).

It pays for itself if a single wrong decision costs you more than **about 8 cents**.

A wrongly approved refund, a missed policy violation, a bad merge, a compliance miss: all cost more
than 8 cents.

## How to evaluate it

Four weeks, one real decision flow, three numbers:

1. **Automation rate** — what share ships without review. Expect roughly 66–74%.
2. **Escaped errors** — wrong decisions that shipped, against your current process. Expect roughly
   12 per 100 shipped on hard tasks; measure yours.
3. **Review time** — how long a reviewer takes with the dissent reasons, against without.

modeljury is MIT-licensed and installs with `pip install modeljury`. There is nothing to procure
and nothing to lock into for the pilot.

## Reproducing these numbers

Everything is in [benchmarks/](benchmarks/): the datasets (all public), the setups, the runner, and
the raw per-decision records. `python report.py results/full.jsonl` regenerates every table.
