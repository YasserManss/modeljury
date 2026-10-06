Results from results/full.jsonl  (reference panel for matched acc: panel-mixed)

### banking77

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |
|---|---|---|---|---|---|---|---|---|
| panel-mixed | 500 | 79% | 78% | 89% | 58% | – | 3.08 / 6.24 | 1.44 |
| panel-open | 500 | 73% | 63% | 90% | 77% | – | 1.60 / 3.12 | 0.26 |
| jev-openrouter | 500 | 80% | – | – | – | 89% | 0.55 / 0.67 | 0.07 |
| large-opus | 500 | 90% | – | – | – | 97% | 4.09 / 8.40 | 6.28 |
| openjury | 500 | 79% | 71% | 92% | 72% | – | 3.81 / 13.34 | 0.62 |

### boolq

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |
|---|---|---|---|---|---|---|---|---|
| panel-mixed | 500 | 91% | 90% | 94% | 40% | – | 2.42 / 4.87 | 0.80 |
| panel-open | 500 | 90% | 85% | 93% | 39% | – | 1.62 / 3.70 | 0.14 |
| jev-openrouter | 500 | 91% | – | – | – | 96% | 0.54 / 0.67 | 0.02 |
| large-opus | 500 | 92% | – | – | – | 96% | 4.10 / 10.96 | 3.47 |
| openjury | 500 | 93% | 89% | 95% | 38% | – | 3.26 / 11.62 | 0.31 |

### chaosnli

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k | human AUROC |
|---|---|---|---|---|---|---|---|---|---|
| panel-mixed | 500 | 68% | 60% | 77% | 56% | – | 3.41 / 6.70 | 0.74 | 0.57 |
| panel-open | 500 | 66% | 48% | 78% | 69% | – | 1.62 / 4.78 | 0.13 | 0.64 |
| jev-openrouter | 500 | 65% | – | – | – | 71% | 0.55 / 0.70 | 0.02 | 0.56 |
| large-opus | 500 | 69% | – | – | – | 80% | 5.74 / 8.06 | 4.33 | 0.63 |
| openjury | 500 | 69% | 51% | 81% | 68% | – | 3.88 / 13.32 | 0.26 | 0.60 |

### judgebench

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |
|---|---|---|---|---|---|---|---|---|
| panel-mixed | 350 | 82% | 59% | 95% | 82% | – | 6.29 / 18.75 | 3.38 |
| panel-open | 350 | 78% | 63% | 85% | 59% | – | 2.29 / 15.61 | 0.77 |
| jev-openrouter | 350 | 80% | – | – | – | 89% | 0.55 / 0.71 | 0.08 |
| large-opus | 350 | 95% | – | – | – | 100% | 6.54 / 13.36 | 15.13 |
| openjury | 350 | 83% | 58% | 96% | 85% | – | 10.42 / 67.02 | 2.57 |

### mhs

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k | human AUROC |
|---|---|---|---|---|---|---|---|---|---|
| panel-mixed | 500 | 76% | 74% | 81% | 42% | – | 2.18 / 4.08 | 0.66 | 0.56 |
| panel-open | 500 | 73% | 70% | 80% | 48% | – | 1.62 / 8.38 | 0.11 | 0.55 |
| jev-openrouter | 500 | 75% | – | – | – | 80% | 0.57 / 0.72 | 0.01 | 0.55 |
| large-opus | 500 | 71% | – | – | – | 77% | 5.74 / 8.77 | 4.07 | 0.64 |
| openjury | 500 | 76% | 73% | 84% | 52% | – | 3.57 / 13.17 | 0.23 | 0.56 |

### vitaminc

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |
|---|---|---|---|---|---|---|---|---|
| panel-mixed | 500 | 81% | 78% | 90% | 59% | – | 2.61 / 4.94 | 0.72 |
| panel-open | 500 | 79% | 68% | 92% | 74% | – | 1.53 / 3.76 | 0.13 |
| jev-openrouter | 500 | 80% | – | – | – | 88% | 0.53 / 0.65 | 0.02 |
| large-opus | 500 | 85% | – | – | – | 91% | 5.30 / 8.54 | 4.24 |
| openjury | 500 | 83% | 78% | 90% | 53% | – | 3.49 / 13.92 | 0.25 |

