"""Synthetic clients: archetypes, per-player trait spread, and the client
that runs Learning and Repeating Mode sessions.

Owner: docs/topics/synthetic-clients/record.md, sections 3.1 and 4.

theta = <baseline_ms, mu, sigma, beta, alpha, F, C>, where F is derived from C
so that R(t = S, S) = 0.9.

The client does not decide *when* or *which* line to practise; the caller
(``practice.py`` or a review planner) passes the line and the simulation day.
The client only answers "what happens if this player runs this line now?".

Lines are described by ``LineSpec``: a unique line id, an opening name and
the number of repertoire moves M the player has to recall. Opening names are
not unique (different move orders reach the same named opening), so the
client keys its memory by ``line_id``. ``tempo_ml.catalog`` builds these
from the opening catalog in ``backend/tempo_demo.sqlite``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Mapping, Protocol, Sequence

import numpy as np

from .grading import SessionRecord, calculate_session_grade
from .memory.multiplicative import LineMemory, MultiplicativeStability, StabilityModel, next_reps, retrievability
from .recall import DEFAULT_MAX_ATTEMPTS_PER_MOVE, MoveEvent, play_move, sample_move_time_ms

# Trait bounds from record section 3.1.
BASELINE_MS_RANGE = (150.0, 500.0)
ALPHA_RANGE = (0.1, 0.5)


@dataclass(frozen=True)
class ClientTraits:
    """Cognitive traits of one synthetic client.

    Attributes:
        baseline_ms: Physical motor / board-scan / UI latency floor (ms).
        mu: Log-space mean of the raw hesitation log-normal (seconds).
        sigma: Log-space dispersion of the raw hesitation log-normal.
        beta: Effort; scales cognitive strain when retrievability is low.
        alpha: Practice automaticity rate.
        C: Forgetting-curve decay power.
    """

    baseline_ms: float
    mu: float
    sigma: float
    beta: float
    alpha: float
    C: float

    def __post_init__(self) -> None:
        lo, hi = BASELINE_MS_RANGE
        if not lo <= self.baseline_ms <= hi:
            raise ValueError(f"baseline_ms must be in [{lo}, {hi}], got {self.baseline_ms}")
        if self.sigma <= 0.0:
            raise ValueError(f"sigma must be > 0, got {self.sigma}")
        if self.beta < 0.0:
            raise ValueError(f"beta must be >= 0, got {self.beta}")
        lo, hi = ALPHA_RANGE
        if not lo <= self.alpha <= hi:
            raise ValueError(f"alpha must be in [{lo}, {hi}], got {self.alpha}")
        if self.C <= 0.0:
            raise ValueError(f"C must be > 0, got {self.C}")

    @property
    def F(self) -> float:
        """Forgetting-curve scaling factor F = 0.9^(-1/C) - 1."""
        return 0.9 ** (-1.0 / self.C) - 1.0

    def as_dict(self) -> dict[str, float]:
        out = asdict(self)
        out["F"] = self.F
        return out


# Stage 1 benchmark archetypes (record section 4).
ARCHETYPES: Mapping[str, ClientTraits] = {
    "blitzer": ClientTraits(baseline_ms=220.0, mu=-0.6, sigma=0.45, beta=0.4, alpha=0.35, C=0.65),
    "balanced": ClientTraits(baseline_ms=300.0, mu=-0.2, sigma=0.40, beta=1.0, alpha=0.25, C=0.50),
    "diligent": ClientTraits(baseline_ms=380.0, mu=0.3, sigma=0.35, beta=2.2, alpha=0.20, C=0.35),
}

_TRAIT_NAMES = ("baseline_ms", "mu", "sigma", "beta", "alpha", "C")


def clamp_traits(values: Mapping[str, float]) -> ClientTraits:
    """Build ClientTraits, clamping each value into its permitted range."""
    v = dict(values)
    v["baseline_ms"] = float(np.clip(v["baseline_ms"], *BASELINE_MS_RANGE))
    v["alpha"] = float(np.clip(v["alpha"], *ALPHA_RANGE))
    v["sigma"] = max(float(v["sigma"]), 1e-3)
    v["beta"] = max(float(v["beta"]), 0.0)
    v["C"] = max(float(v["C"]), 1e-3)
    v["mu"] = float(v["mu"])
    return ClientTraits(**{k: v[k] for k in _TRAIT_NAMES})


@dataclass(frozen=True)
class TraitDistribution:
    """Multivariate normal over the trait vector, theta ~ N(mean, cov).

    This is the hook for Stage 2 calibration (review-dataset record, 4.2):
    a calibrated cohort supplies ``mean`` and ``cov``. Samples are clamped
    into the permitted trait ranges.

    Args:
        mean: Cohort mean traits.
        cov: 6x6 covariance in the order baseline_ms, mu, sigma, beta, alpha, C.
    """

    mean: ClientTraits
    cov: np.ndarray

    def __post_init__(self) -> None:
        cov = np.asarray(self.cov, dtype=float)
        if cov.shape != (len(_TRAIT_NAMES), len(_TRAIT_NAMES)):
            raise ValueError(f"cov must be {len(_TRAIT_NAMES)}x{len(_TRAIT_NAMES)}")
        object.__setattr__(self, "cov", cov)

    @classmethod
    def diagonal(cls, mean: ClientTraits, std: Mapping[str, float]) -> "TraitDistribution":
        """Independent traits with the given standard deviations (missing = 0)."""
        stds = np.array([float(std.get(name, 0.0)) for name in _TRAIT_NAMES])
        return cls(mean=mean, cov=np.diag(stds**2))

    def sample(self, rng: np.random.Generator) -> ClientTraits:
        mean_vec = np.array([getattr(self.mean, name) for name in _TRAIT_NAMES])
        draw = rng.multivariate_normal(mean_vec, self.cov)
        return clamp_traits(dict(zip(_TRAIT_NAMES, draw)))


def with_overrides(traits: ClientTraits, **overrides: float) -> ClientTraits:
    """Return a copy of ``traits`` with some fields replaced (validated)."""
    return replace(traits, **overrides)


class LineSpec(Protocol):
    """What the client needs to know about a line."""

    @property
    def line_id(self) -> str: ...

    @property
    def opening_name(self) -> str: ...

    @property
    def num_moves(self) -> int: ...


@dataclass(frozen=True)
class Line:
    """Minimal concrete LineSpec. ``line_id`` defaults to the opening name."""

    opening_name: str
    num_moves: int
    line_id: str = ""

    def __post_init__(self) -> None:
        if self.num_moves <= 0:
            raise ValueError(f"num_moves must be positive, got {self.num_moves}")
        if not self.line_id:
            object.__setattr__(self, "line_id", self.opening_name)


@dataclass(frozen=True)
class SessionOutcome:
    """Everything one simulated session produced.

    ``record`` is the dataset row. The remaining fields are ground truth that a
    real player would never expose; keep them out of planner inputs and use
    them only for evaluation.
    """

    record: SessionRecord
    mode: str  # "learning" or "repeating"
    day: float
    moves: tuple[MoveEvent, ...]
    blunder_count: int
    retrievability: float
    stability_before: float | None
    stability_after: float
    reps_before: int
    reps_after: int


@dataclass
class SyntheticClient:
    """A simulated player with fixed traits and per-line hidden memory.

    Args:
        name: Dataset ``agent_name``, e.g. ``synth_blitzer_01``.
        traits: Cognitive trait vector theta.
        seed: Seed for this client's private random stream.
        stability_model: Ground-truth stability dynamics.
        max_attempts_per_move: Cap on retries after a retracted wrong move; once
            reached, the client is assumed to find the move on that attempt.
    """

    name: str
    traits: ClientTraits
    seed: int | np.random.SeedSequence | None = None
    stability_model: StabilityModel = field(default_factory=MultiplicativeStability)
    max_attempts_per_move: int = DEFAULT_MAX_ATTEMPTS_PER_MOVE
    archetype: str | None = None
    _memory: dict[str, LineMemory] = field(default_factory=dict, init=False, repr=False)
    _rng: np.random.Generator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_attempts_per_move < 1:
            raise ValueError("max_attempts_per_move must be >= 1")
        self._rng = np.random.default_rng(self.seed)

    # ------------------------------------------------------------------ state

    def memory(self, line: LineSpec) -> LineMemory:
        """Ground-truth memory for a line (created empty on first access)."""
        return self._memory.setdefault(line.line_id, LineMemory())

    def knows(self, line: LineSpec) -> bool:
        mem = self._memory.get(line.line_id)
        return mem is not None and mem.seen

    def true_retrievability(self, line: LineSpec, day: float) -> float:
        """Ground-truth R for a line at ``day`` (0.0 if never seen)."""
        mem = self._memory.get(line.line_id)
        if mem is None or not mem.seen:
            return 0.0
        return retrievability(mem.elapsed(day), mem.stability, self.traits.C)

    # --------------------------------------------------------------- sessions

    def learn(self, line: LineSpec, day: float) -> SessionOutcome:
        """Run a Learning Mode session (arrows shown, the client follows them).

        Status is ``new`` on first exposure, ``learning`` afterwards. With the
        arrow showing the move, no retrieval is needed: accuracy is 1.0 and
        latency uses R = 1 (no cognitive strain).
        """
        mem = self.memory(line)
        status = "learning" if mem.seen else "new"
        t_days = mem.elapsed(day)
        R = 1.0 if not mem.seen else retrievability(t_days, mem.stability, self.traits.C)

        moves = tuple(
            MoveEvent(
                index=i,
                attempt_times_ms=(sample_move_time_ms(self.traits, 1.0, mem.reps, self._rng),),
                first_attempt_correct=True,
            )
            for i in range(line.num_moves)
        )

        s_before = mem.stability
        s_after = (
            self.stability_model.initial()
            if s_before is None
            else self.stability_model.after_success(s_before, R)
        )
        return self._finish(line, mem, day, status, "learning", t_days, R, moves, s_before, s_after)

    def review(self, line: LineSpec, day: float) -> SessionOutcome:
        """Run a Repeating Mode session (no hints; wrong moves are retracted).

        Each repertoire move's first attempt is correct with probability R.
        A wrong move is taken back and retried; every attempt's latency counts
        toward ``total_time_ms``. Status is ``relearning`` if the previous
        Repeating Mode session on this line had a blunder, else ``review``.
        """
        mem = self.memory(line)
        if not mem.seen:
            raise ValueError(
                f"{self.name} cannot review {line.opening_name!r}: line has not been learned"
            )
        status = "relearning" if mem.last_review_lapsed else "review"
        t_days = mem.elapsed(day)
        R = retrievability(t_days, mem.stability, self.traits.C)

        moves = tuple(self._play_move(i, R, mem.reps) for i in range(line.num_moves))
        blundered = any(not m.first_attempt_correct for m in moves)

        s_before = mem.stability
        s_after = (
            self.stability_model.after_lapse(s_before, R)
            if blundered
            else self.stability_model.after_success(s_before, R)
        )
        outcome = self._finish(line, mem, day, status, "repeating", t_days, R, moves, s_before, s_after)
        mem.last_review_lapsed = blundered
        return outcome

    # --------------------------------------------------------------- internal

    def _play_move(self, index: int, R: float, reps: int) -> MoveEvent:
        return play_move(index, R, reps, self.traits, self._rng, self.max_attempts_per_move)

    def _finish(
        self,
        line: LineSpec,
        mem: LineMemory,
        day: float,
        status: str,
        mode: str,
        t_days: float,
        R: float,
        moves: tuple[MoveEvent, ...],
        s_before: float | None,
        s_after: float,
    ) -> SessionOutcome:
        blunders = sum(1 for m in moves if not m.first_attempt_correct)
        total_ms = sum(m.time_ms for m in moves)
        grade = calculate_session_grade(
            blunder_count=blunders,
            total_time_ms=total_ms,
            num_moves=line.num_moves,
            baseline_ms=self.traits.baseline_ms,
        )
        record = SessionRecord(
            agent_name=self.name,
            opening_name=line.opening_name,
            review_status=status,
            t_days=round(float(t_days), 4),
            grade=grade,
            total_time_ms=int(round(total_ms)),
            accuracy=(line.num_moves - blunders) / line.num_moves,
        )

        reps_before = mem.reps
        mem.reps = next_reps(mem.reps, blundered=blunders > 0)
        mem.stability = s_after
        mem.last_session_day = day
        mem.sessions += 1

        return SessionOutcome(
            record=record,
            mode=mode,
            day=day,
            moves=moves,
            blunder_count=blunders,
            retrievability=R,
            stability_before=s_before,
            stability_after=s_after,
            reps_before=reps_before,
            reps_after=mem.reps,
        )


def build_population(
    counts: Mapping[str, int],
    seed: int,
    distributions: Mapping[str, TraitDistribution] | None = None,
    stability_model: StabilityModel | None = None,
) -> list[SyntheticClient]:
    """Create named clients per archetype, e.g. ``{"blitzer": 3, "diligent": 2}``.

    Without ``distributions`` every client of an archetype has exactly the
    benchmark traits from ``ARCHETYPES`` and differs only in its random stream.
    Pass a ``TraitDistribution`` per archetype (e.g. from Stage 2 calibration)
    to give each client its own sampled trait vector.

    Names follow the dataset convention ``synth_<archetype>_<NN>``. All
    randomness derives from ``seed``, so a population is reproducible.
    """
    root = np.random.SeedSequence(seed)
    total = sum(counts.values())
    child_seeds: Sequence[np.random.SeedSequence] = root.spawn(total + 1)
    trait_rng = np.random.default_rng(child_seeds[-1])

    clients: list[SyntheticClient] = []
    k = 0
    for archetype, n in counts.items():
        if n < 0:
            raise ValueError(f"count for {archetype!r} must be >= 0")
        dist = (distributions or {}).get(archetype)
        if dist is None and archetype not in ARCHETYPES:
            raise KeyError(f"unknown archetype {archetype!r}; pass a TraitDistribution for it")
        for i in range(1, n + 1):
            traits = dist.sample(trait_rng) if dist is not None else ARCHETYPES[archetype]
            kwargs = {} if stability_model is None else {"stability_model": stability_model}
            clients.append(
                SyntheticClient(
                    name=f"synth_{archetype}_{i:02d}",
                    traits=traits,
                    seed=child_seeds[k],
                    archetype=archetype,
                    **kwargs,
                )
            )
            k += 1
    return clients
