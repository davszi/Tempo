"""Synthetic clients: hidden memory weights + behavioural traits."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import SimConfig
from .fsrs6 import DEFAULT_W, LOWER_W, UPPER_W, FSRS6, forgetting_factor


@dataclass
class Persona:
    agent_name: str
    archetype: str
    w: np.ndarray            # 21 hidden FSRS-6 weights (the "truth"); C = w20
    baseline_ms: float
    mu: float
    sigma: float
    beta: float
    alpha: float
    desired_retention: float
    new_line_prob: float
    skip_day_prob: float
    n_lines: int
    study_hour: float

    @property
    def memory(self) -> FSRS6:
        return FSRS6(self.w)

    def hidden_row(self) -> dict:
        row = {"agent_name": self.agent_name, "archetype": self.archetype}
        row.update({f"w{i}": float(x) for i, x in enumerate(self.w)})
        row["C_true"] = float(self.w[20])
        row["F_true"] = float(forgetting_factor(self.w[20]))
        for k in ("baseline_ms", "mu", "sigma", "beta", "alpha", "desired_retention",
                  "new_line_prob", "skip_day_prob", "n_lines", "study_hour"):
            row[k] = getattr(self, k)
        return row


def _u(rng, lo_hi):
    lo, hi = lo_hi
    return float(rng.uniform(lo, hi))


def sample_population(cfg: SimConfig, rng: np.random.Generator) -> list[Persona]:
    names = list(cfg.archetypes)
    probs = np.array([cfg.archetypes[n].weight for n in names], float)
    probs /= probs.sum()
    j = cfg.trait_jitter
    out = []
    for i in range(cfg.n_agents):
        name = names[rng.choice(len(names), p=probs)]
        a = cfg.archetypes[name]

        w = DEFAULT_W.copy()
        w[0:4] *= a.init_stability_mult
        w[8] += a.growth_shift
        if a.C is not None:
            w[20] = a.C
        noise = np.exp(rng.normal(0.0, cfg.weight_noise, 21))
        if cfg.freeze_short_term_weights:
            noise[17:20] = 1.0
        w = w * noise
        w[0:4] = np.sort(w[0:4])  # S0(Again) <= S0(Hard) <= S0(Good) <= S0(Easy)
        w = np.clip(w, LOWER_W, UPPER_W)

        jit = np.exp(rng.normal(0.0, j, 4))
        out.append(Persona(
            agent_name=f"synth_{name}_{i:04d}",
            archetype=name,
            w=w,
            # ranges from the synthetic-clients record 3.1
            baseline_ms=float(np.clip(a.baseline_ms * jit[0], 150, 500)),
            mu=a.mu + float(rng.normal(0.0, j)),
            sigma=a.sigma * jit[1],
            beta=a.beta * jit[2],
            alpha=float(np.clip(a.alpha * jit[3], 0.1, 0.5)),
            desired_retention=_u(rng, cfg.desired_retention),
            new_line_prob=_u(rng, cfg.new_line_prob),
            skip_day_prob=_u(rng, cfg.skip_day_prob),
            n_lines=int(rng.integers(cfg.lines_per_agent[0], cfg.lines_per_agent[1] + 1)),
            study_hour=float(rng.uniform(7, 22)),
        ))
    return out
