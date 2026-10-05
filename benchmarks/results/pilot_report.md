Results from results/pilot.jsonl  (reference panel for matched acc: panel-mixed)

### banking77

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |
|---|---|---|---|---|---|---|---|---|
| panel-mixed | 50 | 70% | 78% | 82% | 53% | – | 3.02 / 5.11 | 1.44 |
| panel-open | 50 | 66% | 60% | 87% | 76% | – | 1.48 / 3.12 | 0.26 |
| jev-openrouter | 50 | 72% | – | – | – | 82% | 0.49 / 0.69 | 0.07 |
| large-opus | 50 | 90% | – | – | – | 92% | 4.65 / 7.35 | 6.51 |
| laya | 50 | 30% | – | – | – | 38% | 0.47 / 0.51 | 0.00 |

### boolq

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |
|---|---|---|---|---|---|---|---|---|
| panel-mixed | 50 | 92% | 88% | 95% | 50% | – | 2.52 / 4.15 | 0.75 |
| panel-open | 50 | 88% | 84% | 93% | 50% | – | 1.67 / 3.22 | 0.14 |
| jev-openrouter | 50 | 90% | – | – | – | 95% | 0.52 / 0.74 | 0.02 |
| large-opus | 50 | 94% | – | – | – | 95% | 4.48 / 8.85 | 3.21 |
| laya | 50 | 80% | – | – | – | 80% | 0.22 / 0.35 | 0.00 |

### chaosnli

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k | human AUROC |
|---|---|---|---|---|---|---|---|---|---|
| panel-mixed | 50 | 66% | 54% | 67% | 47% | – | 3.03 / 5.64 | 0.73 | 0.54 |
| panel-open | 50 | 74% | 44% | 82% | 69% | – | 1.76 / 11.88 | 0.13 | 0.67 |
| jev-openrouter | 50 | 64% | – | – | – | 67% | 0.52 / 0.61 | 0.02 | 0.60 |
| large-opus | 50 | 68% | – | – | – | 78% | 5.75 / 10.41 | 4.30 | 0.53 |
| laya | 50 | 58% | – | – | – | 59% | 0.17 / 0.22 | 0.00 | 0.58 |

### judgebench

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |
|---|---|---|---|---|---|---|---|---|
| panel-mixed | 50 | 74% | 52% | 96% | 92% | – | 6.66 / 22.29 | 3.33 |
| panel-open | 50 | 70% | 68% | 68% | 27% | – | 2.38 / 13.80 | 0.80 |
| jev-openrouter | 50 | 72% | – | – | – | 88% | 0.47 / 0.62 | 0.08 |
| large-opus | 50 | 90% | – | – | – | 100% | 7.05 / 14.23 | 15.74 |
| laya | 50 | 46% | – | – | – | 42% | 2.53 / 3.90 | 0.00 |

### mhs

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k | human AUROC |
|---|---|---|---|---|---|---|---|---|---|
| panel-mixed | 50 | 74% | 78% | 77% | 31% | – | 2.24 / 4.01 | 0.66 | 0.57 |
| panel-open | 50 | 74% | 68% | 79% | 46% | – | 1.67 / 4.35 | 0.11 | 0.63 |
| jev-openrouter | 50 | 74% | – | – | – | 74% | 0.53 / 0.74 | 0.01 | 0.66 |
| large-opus | 50 | 62% | – | – | – | 72% | 5.63 / 10.04 | 3.96 | 0.75 |
| laya | 50 | 82% | – | – | – | 87% | 0.14 / 0.22 | 0.00 | 0.75 |

### vitaminc

| setup | n | accuracy | coverage | shipped acc | error recall | matched acc | latency p50/p95 | $/1k |
|---|---|---|---|---|---|---|---|---|
| panel-mixed | 50 | 84% | 80% | 95% | 75% | – | 2.51 / 4.44 | 0.70 |
| panel-open | 50 | 86% | 78% | 95% | 71% | – | 1.52 / 2.38 | 0.12 |
| jev-openrouter | 50 | 86% | – | – | – | 95% | 0.52 / 0.67 | 0.02 |
| large-opus | 50 | 90% | – | – | – | 95% | 5.19 / 7.69 | 3.96 |
| laya | 50 | 54% | – | – | – | 60% | 0.16 / 0.22 | 0.00 |

