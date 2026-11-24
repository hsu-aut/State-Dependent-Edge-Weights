# Per-case evaluation

## Descriptive statistics

| config | cases | valid ranks | no deviation | errors | K | mean rank [95% CI] | median | IQR | top-1 | top-3 | top-5 | top-10 | mean SAE [95% CI] | MR ties best/worst | published MR / SAE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heuristic_uniform | 2419 | 2419 | 0 | 0 | [81] | 20.13 [19.45, 20.79] | 17.0 | 7-27 | 0.0% | 13.5% | 21.7% | 35.1% | 0.6883 [0.6772, 0.6999] | 19.61 / 20.46 | - |

## Paired comparisons (positive improvement = second method better)

| comparison | metric | pairs | mean A | mean B | mean improvement [95% CI] | median impr. | better/equal/worse | rank-biserial | p (Wilcoxon) | p (Holm) |
|---|---|---|---|---|---|---|---|---|---|---|

## Mean rank by parameter class / deviation magnitude

| group | n | heuristic_uniform |
|---|---|---|
| deviation 15-25% | 219 | 25.30 |
| deviation 5-15% | 1338 | 20.14 |
| deviation |dev| <= 5% | 856 | 18.64 |
| pipe: diameter | 2394 | 20.09 |
| pipe: roughness | 25 | 23.32 |
