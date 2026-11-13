"""Synthetic client: a simulated player that runs Learning and Repeating Mode
sessions and emits review-session records.

Owner: docs/topics/synthetic-clients/record.md

The client does not decide *when* or *which* line to practise; the caller
(later the review planner or a data-generation driver) passes the line and the
simulation day. The client only answers "what happens if this player runs this
line now?".

Lines are described by ``LineSpec``: a unique line id, an opening name and
the number of repertoire moves M the player has to recall. Opening names are
not unique (different move orders reach the same named opening), so the
client keys its memory by ``line_id``. ``tempo_ml.openings`` builds these
from the opening library in ``openings/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence

import numpy as np

from ..review_dataset import SessionRecord, calculate_session_grade
from .latency import sample_move_time_ms
from .memory import LineMemory, MultiplicativeStability, StabilityModel, next_reps, retrievability
from .traits import ARCHETYPES, ClientTraits, TraitDistribution

DEFAULT_MAX_ATTEMPTS_PER_MOVE = 5


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
class MoveEvent:
    """One repertoire move in a session.

    Attributes:
        index: 0-based position of the move within the line's repertoire moves.
        attempt_times_ms: Latency of each attempt; all but the last were wrong
            (Repeating Mode retracts a wrong move and the client retries).
        first_attempt_correct: Whether the first attempt was the repertoire move.
    """

    index: int
    attempt_times_ms: tuple[float, ...]
    first_attempt_correct: bool

    @property
    def time_ms(self) -> float:
        return float(sum(self.attempt_times_ms))


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
        times: list[float] = []
        first_correct = False
        for attempt in range(self.max_attempts_per_move):
            times.append(sample_move_time_ms(self.traits, R, reps, self._rng))
            correct = self._rng.random() < R
            if attempt == 0:
                first_correct = correct
            if correct:
                break
        return MoveEvent(index=index, attempt_times_ms=tuple(times), first_attempt_correct=first_correct)

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
