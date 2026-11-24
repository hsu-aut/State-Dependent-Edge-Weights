# Per-case evaluation

## Descriptive statistics

| config | cases | valid ranks | no deviation | errors | K | mean rank [95% CI] | median | IQR | top-1 | top-3 | top-5 | top-10 | mean SAE [95% CI] | MR ties best/worst | published MR / SAE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heuristic | 2419 | 2419 | 0 | 0 | [81] | 15.20 [14.63, 15.76] | 11.0 | 5-19 | 0.0% | 16.5% | 25.9% | 47.4% | 0.7122 [0.7013, 0.7231] | 14.79 / 15.64 | 39.76 / 0.3949 -> DIFFERENT |

## Paired comparisons (positive improvement = second method better)

| comparison | metric | pairs | mean A | mean B | mean improvement [95% CI] | median impr. | better/equal/worse | rank-biserial | p (Wilcoxon) | p (Holm) |
|---|---|---|---|---|---|---|---|---|---|---|

## Mean rank by parameter class / deviation magnitude

| group | n | heuristic |
|---|---|---|
| deviation 15-25% | 219 | 18.96 |
| deviation 5-15% | 1338 | 15.24 |
| deviation |dev| <= 5% | 856 | 14.06 |
| pipe: diameter | 2394 | 15.19 |
| pipe: roughness | 25 | 15.96 |
