"""Generate a synthetic review-session dataset from synthetic clients.

    python -m tempo_ml.simulator.generate --out <dir> [--config configs/<name>.json]
        [--seed N] [--clients-per-archetype N] [--horizon-days N] [--catalog <sqlite>]

A config file sets any ``GenerationConfig`` field; command-line values win.

Each client gets a side (white or black) and a repertoire of real lines from
the opening catalog in ``backend/tempo_demo.sqlite``, then practises for ``horizon_days`` days under the
*data-collection practice policy* in ``practice.py``. The policy only decides when and
which line is practised; what happens in a session comes from the client model
(docs/topics/synthetic-clients/record.md).

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
from dataclasses import asdict, fields
from pathlib import Path

import numpy as np

from ..catalog import DEFAULT_CATALOG_DB, OpeningLine, load_opening_lines
from .grading import CSV_COLUMNS, SessionRecord
from .practice import GenerationConfig, build_plans, simulate_client

GROUND_TRUTH_COLUMNS = (
    "agent_name", "archetype", "side", "line_id", "opening_name", "num_moves",
    "day", "mode", "review_status", "t_days", "grade", "accuracy", "blunders",
    "retrievability", "p_clean", "stability_before", "stability_after",
    "reps_before", "reps_after",
)

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


def _catalog_sha256(lines: list[OpeningLine]) -> str:
    """Hash of the catalog content the generator used.

    The SQLite file itself also holds practice history, so its bytes change
    whenever the demo is used; this hashes only the lines.
    """
    h = hashlib.sha256()
    for l in lines:
        h.update("\x1f".join((l.line_id, l.eco, l.family, l.name, l.moves_uci,
                              l.family_side)).encode() + b"\n")
    return h.hexdigest()


def generate(out_dir: Path, cfg: GenerationConfig, catalog_db: Path = DEFAULT_CATALOG_DB) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    lines = load_opening_lines(catalog_db)
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

    if cfg.memory == "fsrs":  # each client's hidden FSRS-6 weights (truth, evaluation only)
        with (out_dir / "memory_weights.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["agent_name", *[f"w{i}" for i in range(21)]])
            for p in plans:
                w.writerow([p.client.name, *[round(x, 6) for x in p.client.stability_model.weights]])

    with (out_dir / "repertoires.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["agent_name", "line_id", "opening_name", "family", "num_moves"])
        for p in plans:
            for l in p.repertoire:
                w.writerow([p.client.name, l.line_id, l.name, l.family, l.moves_for(p.side)])

    manifest = {
        "generator": "tempo_ml.simulator.generate",
        "config": asdict(cfg),
        "stability_model": (asdict(plans[0].client.stability_model) if cfg.memory != "fsrs" else
                            {"model": "fsrs", "min_days": plans[0].client.stability_model.min_days,
                             "weight_noise": cfg.fsrs_weight_noise, "weights": "memory_weights.csv"}),
        "max_attempts_per_move": plans[0].client.max_attempts_per_move,
        "counts": {**counts, "clients": len(plans),
                   "review_status": dict(sorted(status_counts.items())),
                   "grade": {str(k): v for k, v in sorted(grade_counts.items())}},
        "inputs": {"opening_catalog": {"db": str(catalog_db), "lines": len(lines),
                                       "content_sha256": _catalog_sha256(lines)}},
        "outputs": {p.name: _sha256(p) for p in sorted(out_dir.glob("*.csv"))},
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "platform": platform.platform()},
        "source_commit": _git_commit(Path(__file__).parent),
        "seconds": round(time.time() - started, 1),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_config(path: Path) -> dict:
    """Read a JSON config of ``GenerationConfig`` fields (lists become tuples)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    known = {f.name for f in fields(GenerationConfig)}
    unknown = set(raw) - known
    if unknown:
        raise ValueError(f"unknown config keys: {sorted(unknown)}")
    return {k: tuple(v) if isinstance(v, list) else v for k, v in raw.items()}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--config", type=Path, help="JSON file of GenerationConfig fields, e.g. configs/multiplicative-memory.json")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--clients-per-archetype", type=int)
    ap.add_argument("--horizon-days", type=int)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_DB,
                    help="SQLite database holding the opening catalog")
    a = ap.parse_args(argv)
    values = load_config(a.config) if a.config else {}
    for key in ("seed", "clients_per_archetype", "horizon_days"):
        if getattr(a, key) is not None:
            values[key] = getattr(a, key)
    cfg = GenerationConfig(**values)
    m = generate(a.out, cfg, a.catalog)
    print(json.dumps(m["counts"], indent=2))
    print(f"wrote {a.out} in {m['seconds']} s")


if __name__ == "__main__":
    main()
