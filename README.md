# TEMPO

TEMPO is a chess opening trainer. Learn a line with hints, then review it from memory. The app uses FSRS to schedule the next review.

| Folder | Purpose |
| --- | --- |
| `frontend/` | React browser app |
| `backend/` | Python API, SQLite demo data, and FSRS scheduling |
| `ml/` | Synthetic-client simulator, Lichess opening library, and [FSRS training](docs/topics/fsrs-training/fsrs-training.md) |
| `docs/` | Architecture and project documentation |

## Run locally

Open two PowerShell windows from the repository root.

**Backend**

```powershell
python -m pip install -r backend/requirements.txt
python -m backend.web
```

**Frontend**

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open [Tempo](http://127.0.0.1:5173/). Install dependencies once, then start both servers whenever you want to run the app.

## Terminal demo

From the repository root, run `.\backend\run-demo.cmd` in PowerShell. To demonstrate a wrong move and retry, run `.\backend\run-demo.cmd --side black --grade Again`. The demo prints the grade, stability, next review time in UTC, and player ID. Use that ID to find records in `practice_events` and `player_lines` in `backend/tempo_demo.sqlite`.

The tracked SQLite seed contains 2,719 Lichess lines across 91 opening families. Each line reaches at least White's fourth move. The app loads the 21 fitted FSRS weights from `backend/fitted_global.csv`. The presentation telemetry in `backend/synthetic_reviews.csv` is separate from the training dataset in `ml/data/tempo_v1/`.

The browser app and terminal demo write practice history to the database. To keep the tracked seed pristine, copy it to a scratch location and pass the copy with `--database`.

See the [project documentation](docs/PROJECT_CONTEXT.md) for architecture and documentation build instructions.
