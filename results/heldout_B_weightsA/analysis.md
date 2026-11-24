# Per-case evaluation

## Descriptive statistics

| config | cases | valid ranks | no deviation | errors | K | mean rank [95% CI] | median | IQR | top-1 | top-3 | top-5 | top-10 | mean SAE [95% CI] | MR ties best/worst | published MR / SAE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heuristic_uniform | 200 | 200 | 0 | 0 | [81] | 18.99 [16.91, 21.18] | 17.0 | 7-25 | 0.0% | 13.0% | 20.5% | 37.0% | 0.7001 [0.6593, 0.7398] | 18.46 / 19.34 | - |
| beta | 200 | 200 | 0 | 0 | [81] | 8.08 [7.22, 9.00] | 7.0 | 3-10 | 4.0% | 26.0% | 39.0% | 77.5% | 0.8303 [0.8005, 0.8576] | 7.55 / 10.17 | 38.03 / 0.3267 -> DIFFERENT |
| kl | 200 | 200 | 0 | 0 | [81] | 9.17 [8.04, 10.41] | 6.0 | 4-10 | 5.0% | 17.0% | 45.5% | 77.0% | 0.8014 [0.7653, 0.8354] | 8.08 / 10.97 | 36.21 / 0.2812 -> DIFFERENT |

## Paired comparisons (positive improvement = second method better)

| comparison | metric | pairs | mean A | mean B | mean improvement [95% CI] | median impr. | better/equal/worse | rank-biserial | p (Wilcoxon) | p (Holm) |
|---|---|---|---|---|---|---|---|---|---|---|
| kl vs beta | rank | 200 | 8.08 | 9.17 | -1.09 [-2.125, -0.09475] | -1 | 75/18/107 | -0.149 | 0.0817 | 0.0817 |
| kl vs heuristic_uniform | rank | 200 | 18.99 | 9.17 | 9.82 [7.595, 12.19] | 6 | 148/6/46 | 0.680 | 2e-16 | 4e-16 |
| beta vs heuristic_uniform | rank | 200 | 18.99 | 8.08 | 10.91 [8.83, 13.05] | 9 | 142/3/55 | 0.733 | 4.68e-19 | 1.4e-18 |
| kl vs beta | sae | 200 | 0.8303 | 0.8014 | 0.02896 [9.443e-05, 0.05901] | 0 | 91/10/99 | 0.052 | 0.534 | 0.534 |
| kl vs heuristic_uniform | sae | 200 | 0.7001 | 0.8014 | -0.1013 [-0.1553, -0.04806] | -0.04225 | 86/0/114 | -0.268 | 0.00103 | 0.00206 |
| beta vs heuristic_uniform | sae | 200 | 0.7001 | 0.8303 | -0.1303 [-0.1758, -0.08421] | -0.08801 | 66/7/127 | -0.436 | 1.53e-07 | 4.59e-07 |

## Mean rank by parameter class / deviation magnitude

| group | n | heuristic_uniform | beta | kl |
|---|---|---|---|---|
| deviation 15-25% | 28 | 20.36 | 12.89 | 16.32 |
| deviation 5-15% | 107 | 19.23 | 7.28 | 7.24 |
| deviation |dev| <= 5% | 63 | 17.62 | 7.05 | 9.00 |
| pipe: diameter | 182 | 18.54 | 7.38 | 8.23 |
| pipe: roughness | 18 | 23.50 | 15.11 | 18.67 |
