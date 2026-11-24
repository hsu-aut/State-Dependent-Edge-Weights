# Per-case evaluation

## Descriptive statistics

| config | cases | valid ranks | no deviation | errors | K | mean rank [95% CI] | median | IQR | top-1 | top-3 | top-5 | top-10 | mean SAE [95% CI] | MR ties best/worst | published MR / SAE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| beta | 200 | 200 | 0 | 0 | [81] | 7.90 [7.17, 8.68] | 7.0 | 4-10 | 4.0% | 22.5% | 38.0% | 75.5% | 0.8045 [0.7751, 0.8306] | 7.32 / 10.11 | 38.03 / 0.3267 -> DIFFERENT |
| kl | 200 | 200 | 0 | 0 | [81] | 9.03 [7.88, 10.28] | 6.0 | 4-9 | 4.5% | 16.5% | 42.5% | 80.5% | 0.8011 [0.7647, 0.8353] | 7.84 / 11.59 | 36.21 / 0.2812 -> DIFFERENT |

## Paired comparisons (positive improvement = second method better)

| comparison | metric | pairs | mean A | mean B | mean improvement [95% CI] | median impr. | better/equal/worse | rank-biserial | p (Wilcoxon) | p (Holm) |
|---|---|---|---|---|---|---|---|---|---|---|
| kl vs beta | rank | 200 | 7.9 | 9.03 | -1.13 [-2.135, -0.16] | -1 | 78/20/102 | -0.067 | 0.435 | 0.435 |
| kl vs beta | sae | 200 | 0.8045 | 0.8011 | 0.00346 [-0.02486, 0.03305] | -0.03336 | 69/9/122 | -0.142 | 0.088 | 0.088 |

## Mean rank by parameter class / deviation magnitude

| group | n | beta | kl |
|---|---|---|---|
| deviation 15-25% | 28 | 12.18 | 16.25 |
| deviation 5-15% | 107 | 7.28 | 7.20 |
| deviation |dev| <= 5% | 63 | 6.83 | 8.83 |
| pipe: diameter | 182 | 7.30 | 8.13 |
| pipe: roughness | 18 | 13.94 | 18.11 |
