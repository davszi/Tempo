# Dataset sanity report: data/tempo_v1

- agents: 1000 (800 train / 200 val, split by agent)
- rows: 121532  (new 23927, review/relearning 97605)
- reviews per agent: median 90
- grade mix: Again 15.3%, Hard 10.1%, Good 59.5%, Easy 15.1%
- R_true at review: median 0.871, share < 0.7: 5.9%
- per-move time: median 1.17s, p90 2.43s
- label noise: P(pass | line recalled) 1.000, P(pass | forgotten) 0.000

## Predicting pass (grade > 1) on val agents

| model | log-loss | RMSE(bins) | AUC |
|---|---|---|---|
| oracle (true weights) | 0.3849 | 0.0126 | 0.692 |
| default FSRS-6 | 0.3930 | 0.0335 | 0.670 |
| constant mean | 0.4169 | 0.0082 | 0.500 |

Your optimizer should land between *default* and *oracle*.
