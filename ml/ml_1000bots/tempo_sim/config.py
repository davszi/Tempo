"""All tunable knobs in one place. Override any field from a JSON file:

    python generate.py --config my_config.json

The client model follows the team specification in
docs/topics/synthetic-clients/record.md, the dataset and grading follow
docs/topics/review-dataset/record.md. Ranges are (low, high) for uniform
sampling unless noted.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass
class Archetype:
    """A benchmark client profile (synthetic-clients record, section 4)."""
    weight: float                      # share of the population
    # --- behaviour: theta = <baseline_ms, mu, sigma, beta, alpha, F, C> ---
    baseline_ms: float = 300.0         # motor / UI latency floor (ms)
    mu: float = -0.2                   # log-normal hesitation median parameter (seconds)
    sigma: float = 0.40                # log-normal hesitation shape
    beta: float = 1.0                  # effort: strain = exp(beta * (1 - R))
    alpha: float = 0.25                # practice automaticity: 1 / (1 + alpha * reps)
    # --- hidden memory (FSRS-6 truth) ---
    C: float | None = None             # decay power = w20 (None: FSRS-6 default 0.1542);
                                       # F = 0.9^(-1/C) - 1 follows from C
    init_stability_mult: float = 1.0   # scales w0..w3 (how well a fresh line sticks)
    growth_shift: float = 0.0          # added to w8 (how fast stability grows on success)


def _default_archetypes():
    # Benchmark archetypes, synthetic-clients record section 4 (Stage 1 demo).
    return {
        "fast": Archetype(weight=1 / 3, baseline_ms=220, mu=-0.6, sigma=0.45,
                          beta=0.4, alpha=0.35, C=0.65),
        "balanced": Archetype(weight=1 / 3, baseline_ms=300, mu=-0.2, sigma=0.40,
                              beta=1.0, alpha=0.25, C=0.50),
        "diligent": Archetype(weight=1 / 3, baseline_ms=380, mu=0.3, sigma=0.35,
                              beta=2.2, alpha=0.20, C=0.35),
    }


@dataclass
class SimConfig:
    seed: int = 7
    n_agents: int = 300
    horizon_days: int = 180
    start_date: str = "2026-01-05"

    # ---- population ----
    archetypes: dict = field(default_factory=_default_archetypes)
    # Per-agent log-normal noise on every FSRS weight (0 = all agents of an
    # archetype share identical weights; use 0 + one archetype to check that
    # the optimizer recovers a known parameter vector).
    weight_noise: float = 0.15
    # Per-agent spread of the behaviour traits around the archetype values:
    # baseline_ms, sigma, beta, alpha are multiplied by exp(N(0, trait_jitter)),
    # mu gets + N(0, trait_jitter). 0 = every agent equals its archetype.
    trait_jitter: float = 0.10
    # w17..w19 only act on same-day reviews, which this simulator never
    # produces, so they are left at default (they are unidentifiable here).
    freeze_short_term_weights: bool = True

    # ---- opening catalogue ----
    # Path (relative to the tempo_sim project folder) to the classified
    # Lichess opening library; None = made-up lines.
    openings_file: str | None = "openings/lichess_openings_classified.csv"
    n_openings: int = 300                # lines drawn from the library
    user_moves: tuple = (4, 16)          # moves the player has to produce

    # ---- study habits / app scheduler ----
    lines_per_agent: tuple = (15, 40)
    new_line_prob: tuple = (0.15, 0.40)  # P(learn a new line on a study day)
    skip_day_prob: tuple = (0.05, 0.35)  # P(no study at all that day)
    # Occasional breaks (holidays, exams). Without them almost every review
    # happens near desired retention and the decay C is poorly identified.
    break_prob: float = 0.015            # P(a break starts on a given day)
    break_days: tuple = (4, 30)
    desired_retention: tuple = (0.80, 0.95)
    max_reviews_per_day: int = 15
    learn_grade: int = 3                 # guided drill is logged as GOOD

    # ---- recall ----
    # "line": one dice roll against R decides whether the whole line is
    #         recalled (recalled -> every move right, forgotten -> at least one
    #         blunder). The pass rate then equals R, so fitted weights can be
    #         checked against the hidden truth.
    # "move": every move is right with probability R, as literally written in
    #         the synthetic-clients record 3.3. A line of M moves is then clean
    #         with probability R^M.
    recall_mode: str = "line"

    # ---- grading (review-dataset record, section 3) ----
    easy_ms: float = 500.0               # mean cognitive delay per move < easy_ms -> Easy
    hard_ms: float = 1800.0              # > hard_ms -> Hard, in between -> Good

    train_frac: float = 0.8              # split is BY AGENT, never by row

    @classmethod
    def load(cls, path: str | None) -> "SimConfig":
        cfg = cls()
        if not path:
            return cfg
        with open(path) as f:
            raw = json.load(f)
        for k, v in raw.items():
            if k.startswith("_"):
                continue
            if k == "archetypes":
                cfg.archetypes = {n: Archetype(**a) for n, a in v.items()}
            elif not hasattr(cfg, k):
                raise KeyError(f"unknown config field: {k}")
            else:
                setattr(cfg, k, tuple(v) if isinstance(v, list) else v)
        if cfg.recall_mode not in ("line", "move"):
            raise ValueError(f"recall_mode must be 'line' or 'move', not {cfg.recall_mode!r}")
        return cfg

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, indent=2)
