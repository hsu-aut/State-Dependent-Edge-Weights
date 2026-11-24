# Per-case evaluation

## Descriptive statistics

| config | cases | valid ranks | no deviation | errors | K | mean rank [95% CI] | median | IQR | top-1 | top-3 | top-5 | top-10 | mean SAE [95% CI] | MR ties best/worst | published MR / SAE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| beta | 2419 | 2419 | 0 | 0 | [81] | 7.45 [7.24, 7.66] | 7.0 | 3-10 | 6.1% | 26.4% | 40.5% | 78.2% | 0.7951 [0.7857, 0.8047] | 7.39 / 7.72 | 38.03 / 0.3267 -> DIFFERENT |
| kl | 2419 | 2419 | 0 | 0 | [81] | 8.15 [7.88, 8.42] | 6.0 | 4-10 | 5.9% | 20.2% | 48.4% | 80.1% | 0.7893 [0.7786, 0.7996] | 8.03 / 8.52 | 36.21 / 0.2812 -> DIFFERENT |

## Paired comparisons (positive improvement = second method better)

| comparison | metric | pairs | mean A | mean B | mean improvement [95% CI] | median impr. | better/equal/worse | rank-biserial | p (Wilcoxon) | p (Holm) |
|---|---|---|---|---|---|---|---|---|---|---|
| kl vs beta | rank | 2419 | 7.449 | 8.153 | -0.7036 [-1, -0.4138] | 0 | 973/257/1189 | -0.060 | 0.016 | 0.016 |
| kl vs beta | sae | 2419 | 0.7951 | 0.7893 | 0.005857 [-0.002804, 0.01446] | -0.02108 | 995/146/1278 | -0.074 | 0.00238 | 0.00238 |

## Mean rank by parameter class / deviation magnitude

| group | n | beta | kl |
|---|---|---|---|
| deviation 15-25% | 219 | 10.19 | 9.93 |
| deviation 5-15% | 1338 | 7.62 | 8.01 |
| deviation |dev| <= 5% | 856 | 6.43 | 7.92 |
| pipe: diameter | 2394 | 7.37 | 8.06 |
| pipe: roughness | 25 | 14.72 | 17.16 |
