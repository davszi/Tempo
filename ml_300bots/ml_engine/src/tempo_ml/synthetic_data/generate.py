"""Generate a synthetic review-session dataset from synthetic clients.

    python -m tempo_ml.synthetic_data.generate --out <dir> [--seed N] [--clients-per-archetype N]

Each client gets a side (white or black) and a repertoire of real lines from
the opening library, then practises for ``horizon_days`` days under a
*data-collection practice policy* (below). The policy only decides when and
which line is practised; what happens in a session comes from the client model
(docs/topics/synthetic-clients/record.md).

Practice policy (per client, randomised per client within the config ranges):

- On an active day the client first reviews due lines (oldest due first, up to
  a daily budget), then learns a few new lines. A new line gets a Learning Mode
  session and, a few minutes later, a Repeating Mode session ("redo without
  guidance").
- After every Repeating Mode session the next due time is a grade-based interval
  (Again: 1 day; Hard: x1.2; Good: x2.5; Easy: x3.5 of the previous interval)
  multiplied by log-normal noise. Noise, skipped days and the daily budget
  make reviews early or overdue, so the data covers a wide range of t/S, which
  fitting a forgetting curve needs. This is deliberately not FSRS's own
  scheduler, so the data does not only contain intervals FSRS would choose.

Outputs in ``<dir>``:

- ``sessions.csv``: the review-dataset schema, chronological per client. Within
  one client every opening name is unique, so (agent_name, opening_name) is a
  line's identity.
- ``ground_truth.csv``: hidden per-session state (true R, S, reps, p_clean).
  For evaluation only; never a model input.
- ``clients.csv``, ``repertoires.csv``: who the clients are and what they learned.
- ``manifest.json``: config, row counts, SHA-256 of every output and input.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from ..openings import DEFAULT_LINES_CSV, SIDES, OpeningLine, load_opening_lines
from ..review_dataset import CSV_COLUMNS, SessionRecord
from ..synthetic_clients import ARCHETYPES, SessionOutcome, SyntheticClient, TraitDistribution

GROUND_TRUTH_COLUMNS = (
    "agent_name", "archetype", "side", "line_id", "opening_name", "num_moves",
    "day", "mode", "review_status", "t_days", "grade", "accuracy", "blunders",
    "retrievability", "p_clean", "stability_before", "stability_after",
    "reps_before", "reps_after",
)

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
    """A few families (weighted by popularity in real games), then lines from them."""
    eligible = [l for l in lines if l.playable_by(side) and l.moves_for(side) >= cfg.min_moves]
    by_family: dict[str, list[OpeningLine]] = {}
    for l in eligible:
        by_family.setdefault(l.family, []).append(l)
    families = sorted(by_family)
    weights = np.array([by_family[f][0].family_games + 1.0 for f in families])
    order = rng.choice(len(families), size=len(families), replace=False, p=weights / weights.sum())

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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit(start: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=start, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return None


def generate(out_dir: Path, cfg: GenerationConfig, lines_csv: Path = DEFAULT_LINES_CSV) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    lines = load_opening_lines(lines_csv)
    plans = build_plans(lines, cfg)
    sched_seq = np.random.SeedSequence([cfg.seed, 1]).spawn(len(plans))

    counts = {"sessions": 0, "learning_mode": 0, "repeating_mode": 0}
    status_counts: dict[str, int] = {}
    grade_counts: dict[int, int] = {}

    with (out_dir / "sessions.csv").open("w", newline="", encoding="utf-8") as fs, \
         (out_dir / "ground_truth.csv").open("w", newline="", encoding="utf-8") as fg:
        ws = csv.DictWriter(fs, fieldnames=CSV_COLUMNS)
        wg = csv.DictWriter(fg, fieldnames=GROUND_TRUTH_COLUMNS)
        ws.writeheader()
        wg.writeheader()
        for plan, seq in zip(plans, sched_seq):
            rng = np.random.default_rng(seq)
            for line, out in simulate_client(plan, cfg, rng):
                r: SessionRecord = out.record
                ws.writerow(r.to_row())
                m = line.moves_for(plan.side)
                wg.writerow({
                    "agent_name": r.agent_name, "archetype": plan.client.archetype,
                    "side": plan.side, "line_id": line.line_id, "opening_name": r.opening_name,
                    "num_moves": m, "day": round(out.day, 6), "mode": out.mode,
                    "review_status": r.review_status, "t_days": r.t_days, "grade": r.grade,
                    "accuracy": r.accuracy, "blunders": out.blunder_count,
                    "retrievability": round(out.retrievability, 6),
                    "p_clean": round(out.retrievability ** m, 6) if out.mode == "repeating" else 1.0,
                    "stability_before": "" if out.stability_before is None else round(out.stability_before, 6),
                    "stability_after": round(out.stability_after, 6),
                    "reps_before": out.reps_before, "reps_after": out.reps_after,
                })
                counts["sessions"] += 1
                counts["learning_mode" if out.mode == "learning" else "repeating_mode"] += 1
                status_counts[r.review_status] = status_counts.get(r.review_status, 0) + 1
                grade_counts[r.grade] = grade_counts.get(r.grade, 0) + 1

    with (out_dir / "clients.csv").open("w", newline="", encoding="utf-8") as f:
        cols = ["agent_name", "archetype", "side", "baseline_ms", "mu", "sigma", "beta", "alpha",
                "C", "F", "repertoire_size", "p_active", "review_budget"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in plans:
            t = p.client.traits.as_dict()
            w.writerow({"agent_name": p.client.name, "archetype": p.client.archetype, "side": p.side,
                        **{k: round(v, 6) for k, v in t.items()},
                        "repertoire_size": len(p.repertoire), "p_active": round(p.p_active, 4),
                        "review_budget": p.review_budget})

    with (out_dir / "repertoires.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["agent_name", "line_id", "opening_name", "family", "num_moves"])
        for p in plans:
            for l in p.repertoire:
                w.writerow([p.client.name, l.line_id, l.name, l.family, l.moves_for(p.side)])

    manifest = {
        "generator": "tempo_ml.synthetic_data.generate",
        "config": asdict(cfg),
        "stability_model": asdict(plans[0].client.stability_model),
        "max_attempts_per_move": plans[0].client.max_attempts_per_move,
        "counts": {**counts, "clients": len(plans),
                   "review_status": dict(sorted(status_counts.items())),
                   "grade": {str(k): v for k, v in sorted(grade_counts.items())}},
        "inputs": {"opening_lines.csv": _sha256(Path(lines_csv))},
        "outputs": {p.name: _sha256(p) for p in sorted(out_dir.glob("*.csv"))},
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "platform": platform.platform()},
        "source_commit": _git_commit(Path(__file__).parent),
        "seconds": round(time.time() - started, 1),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=GenerationConfig.seed)
    ap.add_argument("--clients-per-archetype", type=int, default=GenerationConfig.clients_per_archetype)
    ap.add_argument("--horizon-days", type=int, default=GenerationConfig.horizon_days)
    ap.add_argument("--lines", type=Path, default=DEFAULT_LINES_CSV)
    a = ap.parse_args(argv)
    cfg = GenerationConfig(seed=a.seed, clients_per_archetype=a.clients_per_archetype,
                           horizon_days=a.horizon_days)
    m = generate(a.out, cfg, a.lines)
    print(json.dumps(m["counts"], indent=2))
    print(f"wrote {a.out} in {m['seconds']} s")


if __name__ == "__main__":
    main()
