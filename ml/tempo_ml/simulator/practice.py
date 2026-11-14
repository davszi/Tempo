"""Practice policy of the synthetic clients: repertoire, active days, new
lines and review scheduling (the data-collection policy of ``generate.py``).

- Each client gets a side and a repertoire of real lines from a few families.
- On an active day the client first reviews due lines (oldest due first, up to
  a daily budget), then learns 1-3 new lines. A new line gets a Learning Mode
  session and, a few minutes later, a Repeating Mode session.
- After every Repeating Mode session the next due time is a grade-based
  interval (Again: 1 day; Hard: x1.2; Good: x2.5; Easy: x3.5 of the previous
  interval) times log-normal noise. This is deliberately not FSRS's own
  scheduler. Retries of a wrong move happen inside a session (``recall.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..catalog import SIDES, OpeningLine
from .clients import ARCHETYPES, SessionOutcome, SyntheticClient, TraitDistribution

# Grade -> interval multiplier of the practice policy (Again resets to 1 day).
INTERVAL_FACTOR = {2: 1.2, 3: 2.5, 4: 3.5}


@dataclass(frozen=True)
class GenerationConfig:
    seed: int = 20261111
    clients_per_archetype: int = 100
    horizon_days: int = 180
    repertoire_size: tuple[int, int] = (15, 40)
    families_per_client: tuple[int, int] = (2, 6)
    min_moves: int = 2
    new_lines_per_day: tuple[int, int] = (1, 3)
    daily_review_budget: tuple[int, int] = (8, 30)
    active_day_prob: tuple[float, float] = (0.5, 0.95)
    interval_noise_sigma: float = 0.35
    max_interval_days: float = 365.0
    # Std of the per-client trait spread around each archetype (TraitDistribution).
    trait_std: dict[str, float] = field(
        default_factory=lambda: {
            "baseline_ms": 25.0, "mu": 0.15, "sigma": 0.05,
            "beta": 0.2, "alpha": 0.04, "C": 0.05,
        }
    )


@dataclass
class ClientPlan:
    client: SyntheticClient
    side: str
    repertoire: list[OpeningLine]
    p_active: float
    review_budget: int
    new_per_day: tuple[int, int]


def _pick_repertoire(
    lines: list[OpeningLine], side: str, cfg: GenerationConfig, rng: np.random.Generator
) -> list[OpeningLine]:
    """A few families, then lines from them.

    Families are drawn uniformly: the backend catalog has no family
    popularity (the old library's ``n_games``); see the retraining plan's
    open questions.
    """
    eligible = [l for l in lines if l.playable_by(side) and l.moves_for(side) >= cfg.min_moves]
    by_family: dict[str, list[OpeningLine]] = {}
    for l in eligible:
        by_family.setdefault(l.family, []).append(l)
    families = sorted(by_family)
    order = rng.permutation(len(families))

    size = int(rng.integers(cfg.repertoire_size[0], cfg.repertoire_size[1] + 1))
    n_fam = int(rng.integers(cfg.families_per_client[0], cfg.families_per_client[1] + 1))
    pool: list[OpeningLine] = []
    for k, idx in enumerate(order):
        if k >= n_fam and len(pool) >= size:
            break
        pool.extend(by_family[families[idx]])

    chosen: list[OpeningLine] = []
    names: set[str] = set()
    for idx in rng.permutation(len(pool)):
        line = pool[idx]
        if line.name in names:
            continue  # keep (agent, opening_name) unique
        chosen.append(line)
        names.add(line.name)
        if len(chosen) == size:
            break
    return chosen


def build_plans(lines: list[OpeningLine], cfg: GenerationConfig) -> list[ClientPlan]:
    root = np.random.SeedSequence(cfg.seed)
    n = cfg.clients_per_archetype * len(ARCHETYPES)
    seeds = root.spawn(n + 1)
    policy_rng = np.random.default_rng(seeds[-1])

    plans: list[ClientPlan] = []
    k = 0
    for archetype, mean in ARCHETYPES.items():
        dist = TraitDistribution.diagonal(mean, cfg.trait_std)
        for i in range(1, cfg.clients_per_archetype + 1):
            client = SyntheticClient(
                name=f"synth_{archetype}_{i:03d}",
                traits=dist.sample(policy_rng),
                seed=seeds[k],
                archetype=archetype,
            )
            side = SIDES[int(policy_rng.integers(2))]
            plans.append(
                ClientPlan(
                    client=client,
                    side=side,
                    repertoire=_pick_repertoire(lines, side, cfg, policy_rng),
                    p_active=float(policy_rng.uniform(*cfg.active_day_prob)),
                    review_budget=int(policy_rng.integers(cfg.daily_review_budget[0], cfg.daily_review_budget[1] + 1)),
                    new_per_day=cfg.new_lines_per_day,
                )
            )
            k += 1
    return plans


def _next_interval(grade: int, last: float, cfg: GenerationConfig, rng: np.random.Generator) -> float:
    if grade == 1:
        base = 1.0
    else:
        base = max(1.0 if grade < 4 else 2.0, last * INTERVAL_FACTOR[grade])
    return float(min(cfg.max_interval_days, base * rng.lognormal(0.0, cfg.interval_noise_sigma)))


def simulate_client(plan: ClientPlan, cfg: GenerationConfig, rng: np.random.Generator):
    """Run one client's whole practice history. Yields (OpeningLine, SessionOutcome)."""
    c = plan.client
    queue = list(plan.repertoire)  # lines not yet introduced, in introduction order
    due: dict[str, float] = {}
    last_iv: dict[str, float] = {}
    by_id = {l.line_id: l for l in plan.repertoire}
    gap = 60.0 / 86400.0  # one minute between sessions

    def after_review(line: OpeningLine, out: SessionOutcome, t: float) -> None:
        iv = _next_interval(out.record.grade, last_iv.get(line.line_id, 1.0), cfg, rng)
        last_iv[line.line_id] = iv
        due[line.line_id] = t + iv

    for day in range(cfg.horizon_days):
        if rng.random() > plan.p_active:
            continue
        t = day + float(rng.uniform(0.3, 0.7))

        todo = sorted((d, lid) for lid, d in due.items() if d < day + 1.0)[: plan.review_budget]
        for _, lid in todo:
            line = by_id[lid]
            out = c.review(line.as_line(plan.side), t)
            yield line, out
            t += out.record.total_time_ms / 86_400_000.0 + gap
            after_review(line, out, t)

        n_new = int(rng.integers(plan.new_per_day[0], plan.new_per_day[1] + 1))
        for _ in range(min(n_new, len(queue))):
            line = queue.pop(0)
            spec = line.as_line(plan.side)
            out = c.learn(spec, t)
            yield line, out
            t += out.record.total_time_ms / 86_400_000.0 + 3 * gap
            out = c.review(spec, t)
            yield line, out
            t += out.record.total_time_ms / 86_400_000.0 + gap
            after_review(line, out, t)
