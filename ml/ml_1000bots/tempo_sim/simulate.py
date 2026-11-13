"""Run the population through days of study and collect telemetry."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from .config import SimConfig
from .fsrs6 import DEFAULT_W, FSRS6, MemoryState
from .persona import sample_population
from .play import OpeningLine, grade, make_catalogue, next_reps, play_line


@dataclass
class LineProgress:
    line: OpeningLine
    true: MemoryState     # agent's hidden memory
    app: MemoryState      # what the app believes (default weights in phase 1)
    last_day: int
    due_day: int
    last_grade: int
    reps: int = 0         # practice count for m_practice (synthetic-clients record 3.5)


def _schedule(app_model: FSRS6, st: MemoryState, day: int, dr: float) -> int:
    return day + max(1, int(round(app_model.interval_for(st.stability, dr))))


def simulate(cfg: SimConfig):
    rng = np.random.default_rng(cfg.seed)
    catalogue = make_catalogue(cfg, rng)
    personas = sample_population(cfg, rng)
    app_model = FSRS6(DEFAULT_W)
    t0 = datetime.fromisoformat(cfg.start_date)

    reviews, moves, truth = [], [], []
    rid = 0

    for p in personas:
        true_model = p.memory
        order = rng.permutation(len(catalogue))[: p.n_lines]
        to_learn = deque(catalogue[i] for i in order)
        active: list[LineProgress] = []

        on_break_until = -1
        for day in range(cfg.horizon_days):
            if day < on_break_until:
                continue
            if rng.random() < cfg.break_prob:
                on_break_until = day + int(rng.integers(cfg.break_days[0], cfg.break_days[1] + 1))
                continue
            if rng.random() < p.skip_day_prob:
                continue

            # One study session per day; its clock advances with every line,
            # so rows of the same day get increasing timestamps.
            hour = float(np.clip(p.study_hour + rng.normal(0, 1.0), 0, 22.5))
            clock = t0 + timedelta(days=day, hours=hour)

            # ---- Repeating: due lines, most overdue first ----
            due = sorted((lp for lp in active if lp.due_day <= day),
                         key=lambda lp: lp.due_day)[: cfg.max_reviews_per_day]
            for lp in due:
                t = day - lp.last_day
                r_true = true_model.retrievability(t, lp.true.stability)
                att = play_line(p, lp.line, r_true, lp.reps, rng, cfg.recall_mode)
                g = grade(att.accuracy, att.total_time_ms, lp.line.n_moves, p.baseline_ms, cfg)
                status = "relearning" if lp.last_grade == 1 else "review"
                reviews.append(dict(
                    agent_name=p.agent_name, opening_name=lp.line.name, review_status=status,
                    t_days=float(t), grade=g, total_time_ms=round(att.total_time_ms),
                    accuracy=round(att.accuracy, 4),
                    line_id=lp.line.line_id, review_id=rid, day=day,
                    timestamp=clock.isoformat(timespec="seconds"),
                    n_moves=lp.line.n_moves, n_correct=int(att.correct.sum()),
                    baseline_ms=round(p.baseline_ms)))
                for k in range(lp.line.n_moves):
                    moves.append(dict(review_id=rid, ply=int(lp.line.plies[k]),
                                      correct=int(att.correct[k]),
                                      time_ms=round(float(att.time_ms[k]))))
                new_true = true_model.step(lp.true, t, g)
                truth.append(dict(
                    review_id=rid, R_true=r_true, recalled=int(att.recalled),
                    reps_before=lp.reps,
                    S_before=lp.true.stability, D_before=lp.true.difficulty,
                    S_after=new_true.stability, D_after=new_true.difficulty,
                    R_app=app_model.retrievability(t, lp.app.stability)))

                lp.true = new_true
                lp.app = app_model.step(lp.app, t, g)
                lp.last_day, lp.last_grade = day, g
                lp.reps = next_reps(lp.reps, att.clean)
                lp.due_day = _schedule(app_model, lp.app, day, p.desired_retention)
                clock += timedelta(milliseconds=att.total_time_ms,
                                   seconds=float(rng.uniform(5, 20)))
                rid += 1

            # ---- Learning: guided drill of a new line (logged as status "new") ----
            if to_learn and rng.random() < p.new_line_prob:
                line = to_learn.popleft()
                g = cfg.learn_grade
                lp = LineProgress(line, true_model.init_state(g), app_model.init_state(g),
                                  day, 0, g)
                lp.due_day = _schedule(app_model, lp.app, day, p.desired_retention)
                active.append(lp)
                reviews.append(dict(
                    agent_name=p.agent_name, opening_name=line.name, review_status="new",
                    t_days=0.0, grade=g, total_time_ms=None, accuracy=None,
                    line_id=line.line_id, review_id=rid, day=day,
                    timestamp=clock.isoformat(timespec="seconds"),
                    n_moves=line.n_moves, n_correct=None, baseline_ms=round(p.baseline_ms)))
                truth.append(dict(
                    review_id=rid, R_true=None, recalled=None, reps_before=0,
                    S_before=None, D_before=None, S_after=lp.true.stability,
                    D_after=lp.true.difficulty, R_app=None))
                rid += 1

    return personas, catalogue, reviews, moves, truth
