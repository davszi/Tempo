# Results (mean over the three seeds; app clock)

Test log-loss per seed and mean; lower is better. Difference columns: arm b minus arm a.

| Arm | 20261111 | 20261121 | 20261131 | Mean | Hold-out mean | RMSE vs true pass chance | AUC | Median abs days error |
|---|---|---|---|---|---|---|---|---|
| defaults | 0.1991 | 0.2289 | 0.2088 | 0.2123 | 0.2202 | 0.0773 | 0.832 | 6.42 |
| A1 | 0.1916 | 0.2165 | 0.2018 | 0.2033 | 0.2115 | 0.0642 | 0.836 | 8.47 |
| A1c | 0.1912 | 0.2157 | 0.2019 | 0.2029 | 0.2112 | 0.0628 | 0.835 | 11.48 |
| A1c-pass | 0.1778 | 0.2020 | 0.1907 | 0.1902 | 0.1980 | 0.0415 | 0.868 | 5.53 |
| A1c-acc | 0.1775 | 0.2016 | 0.1909 | 0.1900 | 0.1982 | 0.0417 | 0.868 | 5.75 |
| A1c-R | 0.1773 | 0.2013 | 0.1908 | 0.1898 | 0.1982 | 0.0405 | 0.868 | 6.05 |
| A1c (60 d) | 0.1911 | 0.2172 | 0.2023 | 0.2036 | 0.2123 | 0.0663 | 0.835 | 11.74 |
| A1c-pass (60 d) | 0.1775 | 0.2024 | 0.1915 | 0.1905 | 0.1984 | 0.0422 | 0.868 | 5.66 |
| A1c-acc (60 d) | 0.1781 | 0.2017 | 0.1918 | 0.1905 | 0.1986 | 0.0432 | 0.868 | 6.29 |

| Question | a | b | Mean difference (b − a) | 95 % interval | Per seed | Verdict |
|---|---|---|---|---|---|---|
| Q1 meaning of R | A1c | A1c-pass | -0.0121 | [-0.0143, -0.0099] | -0.0129, -0.0125, -0.0107 | established |
| Q2 training target | A1c-pass | A1c-acc | -0.0002 | [-0.0004, +0.0001] | -0.0003, -0.0003, +0.0000 | no difference shown |
| Q2 training target, 60 days | A1c-pass (60 d) | A1c-acc (60 d) | -0.0000 | [-0.0004, +0.0003] | +0.0003, -0.0006, +0.0001 | no difference shown |
| Q3 trainer | A1 | A1c | -0.0003 | [-0.0006, -0.0000] | -0.0003, -0.0007, +0.0001 | inconclusive |
