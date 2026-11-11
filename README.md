# TEMPO

TEMPO is a Python and SQLite chess-opening trainer. The local demo walks through Learning, Repeating, and FSRS scheduling using a line from the Lichess catalog.

## Run the presentation demo

1. Open PowerShell in the project folder. For a fresh setup, install the dependencies with `python -m pip install -r requirements.txt`.
2. Run `.\run-demo.cmd`. It starts a fresh demo player, completes both practice modes, and prints the grade, stability, and next review time in UTC.
3. To show a wrong move and retry, run `.\run-demo.cmd --side black --grade Again`. The other supported grades are `Hard`, `Good`, and `Easy`.
4. In DB Browser for SQLite, open `demo/tempo_demo.sqlite`. Use **Browse Data** and the printed player ID to locate the saved events in `practice_events` and the schedule in `player_lines`.

The default demo uses Both sides and simulates a clean `Good` review. Each run records a new demo player in the same database.

## Present the architecture

Open `.build/docs/html/index.html` in a desktop browser and choose **System Architecture**. The local reader covers deployment, practice flow, and the live demo. The playable browser frontend is planned. The walkthrough runs through the Python backend.

To rebuild the docs after the site sources are tracked in Git, use:

```powershell
python -m pip install -r .docs-kit/requirements.txt
$env:PYTHONUTF8 = '1'
python .docs-kit/docsite.py build --project .
```

## Project layout

| Path | Purpose |
|---|---|
| `tempo/practice_controller.py` | Runs Learning and Repeating sessions and records move attempts. |
| `tempo/ml_controller.py` | Coordinates the review flow and stores results. |
| `tempo/ml_engine.py` | Grades reviews and calls Py-FSRS with the configured weights. |
| `tempo/store.py` | Owns the SQLite schema and transactions. |
| `tempo/offline/synthetic_clients.py` | Generates synthetic review telemetry for offline training. |
| `demo/` | Local presentation database, supplied weights, and synthetic review CSV. |
| `docs/` | Documentation source for the system architecture and datasets. |

## Demo data

- `demo/tempo_demo.sqlite` contains 3,865 Lichess opening lines across 140 families and the saved demo sessions.
- `demo/fitted_global.csv` contains the 21 supplied FSRS weights. The demo reads it at startup.
- `demo/synthetic_reviews.csv` contains 50,400 sessions from 30 simulated agents on one line per family. It is separate from the training run that produced the supplied weights.

To regenerate the synthetic CSV in an environment with Py-FSRS installed:

```powershell
python -m tempo.offline.synthetic_clients --database demo/tempo_demo.sqlite --one-line-per-family --clients-per-profile 10 --sessions 12 --seed 42 --output demo/synthetic_reviews.csv
```

The three demo files are local Git-ignored inputs and outputs. A fresh checkout needs copies of them for the presentation.
