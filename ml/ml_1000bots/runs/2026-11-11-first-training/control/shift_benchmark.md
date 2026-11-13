# Shift benchmark: trained weights on new populations

Global fit: `runs/2026-11-11-first-training/fitted_global.csv`. 200 fresh agents per scenario; every review scored.

## log-loss (lower is better)

| scenario | reviews | default | global fit | archetype fit | oracle | gain of global fit vs default [95%] | gap closed |
|---|---|---|---|---|---|---|---|
| control (same as training) | 20370 | 0.3964 | 0.3917 | 0.3921 | 0.3866 | +0.0047 [+0.0023, +0.0073] | 48% |

## RMSE (lower is better)

| scenario | default | global fit | archetype fit | oracle |
|---|---|---|---|---|
| control (same as training) | 0.0457 | 0.0157 | 0.0181 | 0.0144 |

## AUC (higher is better)

| scenario | default | global fit | archetype fit | oracle |
|---|---|---|---|---|
| control (same as training) | 0.6874 | 0.6880 | 0.6868 | 0.7037 |
