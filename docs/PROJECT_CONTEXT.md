# Project context

TEMPO is a chess app that helps players keep the openings they have learned, by telling them which line to practise next. This file is the shared background every agent on the team reads first: what TEMPO is, the concepts it is built on, which parts are being built now, and how to build and review the repository's documentation.

> **What the TEMPO sections are.** Sections 1–10 below explain what TEMPO is, the concepts it is built on, and which parts are being built now.
>
> **What they are not.** They are not a specification. Apart from the few points marked as decided, no design decisions have been made yet for the parts listed under "What we are building now". Each part will be discussed by the team, and those discussions will decide how it is implemented. When your work reaches a question these sections leave open, raise it with your team member instead of assuming an answer.

Source: official project page, https://www.core-network.ai/ai-team-projects/tempo (these sections differ from it on one deliberate point, see section 9).

## Read first

Follow the [task routes](../AGENTS.md#read-before-the-relevant-action) before the action they govern.

## 1. TEMPO in one sentence

TEMPO teaches you an opening with arrows, then tests you without them, and its AI learns your personal memory well enough to choose the right line for you to practise each day.

Put differently: TEMPO is a chess app that helps players **keep** the openings they have learned, by telling them which line to practise next.

## 2. The problem it solves

Learning a new opening is not the hard part. The hard part of studying alone is deciding *what* to study.

Most existing trainers make that decision with a fixed rule: the same rule for every user, for the life of the product. A fixed rule cannot notice that one player holds a sharp tactical line for weeks while losing a quiet positional one in days. TEMPO's answer is a planner that learns how one specific player remembers and forgets.

## 3. Core vocabulary

Please use these terms consistently so discussions across agents line up.

- **Opening**: a named chess opening (for example the Ruy López or the Sicilian Defence), played from White's or Black's side.
- **Line**: one specific sequence of moves inside an opening (a variation). The line is the unit that is learned, tested and suggested.
- **Repertoire move**: the move a line prescribes in a given position. A played move either is the repertoire move or it is not.
- **Repertoire**: the set of lines a player has learned and wants to keep.
- **Session**: one run through a line, in either mode.
- **Record of what you know / practice history**: the single shared record that both modes write to.
- **Review planner**: the "brain" of the app, which picks the next line to repeat.
- **Suggestion**: the one line the planner returns.
- **Synthetic client**: a simulated player used to generate training data (see section 7).

## 4. The two modes

### Learning Mode: learn it with help

- The **player** chooses which line to learn.
- An arrow on the board shows the move to play.
- If the player goes the wrong way, they are guided back before the move can land.

### Repeating Mode: prove it without help

- The **app** chooses the line. The player cannot pick which line to review; the line is the model's call.
- No hints and no arrows.
- A mistake is not played out on the board. The wrong move is taken back and the player tries again.

Both modes write to the same record of what the player knows.

## 5. How the app decides what to practise: the review planner

The review planner sits behind both modes.

- **It reads** the player's repertoire, their practice history, and its own earlier suggestions.
- **It returns** one line: the line that should be repeated next.
- **It starts general, then personalises.** It begins as a general model and is then fine-tuned on one player's own play.
- **It is not chess-specific by intent.** The planner is designed as a general "what should I practise next?" system. Chess is simply where it is tested first, because results are clear-cut: a move either is the repertoire move or it is not.

## 6. FSRS in brief

The ML engine will contain **FSRS** (Free Spaced Repetition Scheduler), an established open-source spaced-repetition algorithm. In plain terms, FSRS describes the memory of each item with a few quantities:

- **Stability**: roughly how long the memory lasts.
- **Difficulty**: how hard the item is for this person.
- **Retrievability**: the chance of recalling the item right now, which falls as time passes.

After each review, FSRS updates these values based on how the review went, usually expressed as a grade such as Again, Hard, Good or Easy.

How FSRS and the learned planner share the work inside the ML engine is one of the topics for discussion.

## 7. Training data: synthetic clients

**Decided:** the data used to train the ML engine's parameters will be generated synthetically. Synthetic clients, meaning simulated players, will produce practice histories that mimic real human patterns of memorisation and forgetting.

How this is done is open. **Questions to discuss:** which human memory patterns the synthetic clients should reproduce, and what those patterns are based on; how varied the clients need to be (for example, a player who keeps sharp tactical lines for weeks but loses quiet positional ones in days); how to check that the synthetic data is realistic enough; which parameters it is used to train (FSRS, the planner model, or both); how it relates to the later fine-tuning on a real player's own play.

## 8. What we are building now

Four parts are in scope at this stage. The descriptions below say what each part is *for*. They deliberately do not say how it will work, what it contains in detail, or exactly where the boundaries between parts lie. The questions listed under each part are starting points for the team discussions, not decisions.

### 8.1 Database layer

**Purpose:** holds the shared record that both modes write to and that the planner learns from.

From the concept, the system needs to keep, somewhere:

- the openings and lines (what can be learned),
- each player's repertoire,
- practice history from both modes, including what was recalled, what was missed, and how long moves took,
- the planner's past suggestions.

**Questions to discuss:** what exactly is stored and at what level of detail; which of the items above belong to this layer and which belong elsewhere (for example inside the ML engine); how data for one player is kept separate from general data; whether synthetic training data sits alongside real player data; what the other parts need from this layer.

### 8.2 Practice controller

**Purpose:** the bridge between the user interface and the rest of the system.

Behaviour from the concept that touches this part:

- starting a session in Learning Mode on a line the player chose,
- starting a session in Repeating Mode on the line the model chose, with no way for the player to pick another,
- checking played moves against the repertoire move,
- guidance in Learning Mode (arrow, guided back on a wrong move),
- taking back a wrong move in Repeating Mode so the player can try again,
- capturing the outcome of each session for the shared record.

**Questions to discuss:** which of these behaviours live in this controller and which live in the UI or elsewhere; whether anything beyond "try again" is shown after a mistake in Repeating Mode, given the no-hints rule; what the Practice controller asks of the other parts and what it hands back; what happens when a session is interrupted or abandoned.

### 8.3 ML controller

**Purpose:** the bridge between the rest of the app and the ML engine.

Behaviour from the concept that touches this part:

- asking for the next line to repeat,
- passing on what the engine needs to learn from a player's play.

**Questions to discuss:** what triggers a request for a suggestion; when and how often training or fine-tuning happens; what the engine needs as input and returns as output; how the controller relates to the database layer; what role, if any, it plays in feeding synthetic data to the engine.

### 8.4 ML engine

**Purpose:** the review planner itself, including FSRS.

From the concept:

- it returns one line to repeat next, based on repertoire, practice history and its own past suggestions,
- it starts as a general model and is fine-tuned on one player's play,
- its parameters are trained on synthetic data from simulated players (section 7),
- it is meant to work as a general "what should I practise next?" system, with chess as the first domain.

**Questions to discuss:** what kind of model the planner is; how per-player fine-tuning works; how FSRS and the learned model relate; how a brand-new player with no history is handled; how chess-specific details are kept from leaking into a planner meant to be general.

## 9. The earlier prototype

An earlier HTML prototype of TEMPO exists, but it is not part of the repository, so you will not have access to it. Everything from it that matters for the current work is recorded here.

**Settled behaviour for Repeating Mode:**

1. **Mistakes are not played out.** This follows the prototype: after a mistake, the wrong move is taken back and the player tries again. The opponent's punishment is not played out on the board. This is a deliberate difference from the official project page, which describes the punishment playing out before the position rewinds.
2. **The player cannot choose the line to review.** The model picks the line to repeat, as the official project page describes. Unlike in the prototype, the player has no way to start a review on a line of their own choosing. Learning Mode is unaffected: there the player still chooses the line to learn.

**Ideas from the prototype that may come up in discussions** (none of them decided):

- classifying wrong moves by severity (inaccuracy, mistake, blunder),
- measuring response time per move,
- turning a session into an Again / Hard / Good / Easy grade based on accuracy and speed,
- showing per-line memory values to the player,
- drilling a line from both sides of the board,
- after learning a line: redo it with guidance, redo it without guidance, or move on to the next line,
- suggesting a new line for the player to learn.

**Words team members may use from the prototype:** "learn" means Learning Mode; "practice" or "drill" means a Repeating Mode session; "Repertory" means repertoire; a "discovered" line is one the player has learned at least once.

## 10. Working guidelines for agents

- Treat sections 1–9 as context, not as a spec. The only settled points are the Repeating Mode behaviour (sections 4 and 9) and the use of synthetic clients for training data (section 7). Do not present any other design choice as settled.
- When a question is open, lay out options and trade-offs and flag it for team discussion.
- Use the vocabulary in section 3.
- If the official project page or any other material conflicts with this file, point out the difference instead of resolving it silently.
- Remember that the planner is meant to be general beyond chess, and that both modes feed one shared record.

## Repository map

- `.docs-kit/`: initialize the shared-kit Git submodule at the project's reviewed revision.
- `docs/site/site.toml`: site identity, source repository/ref and navigation.
- `docs/topics/home/index.md`: rendered landing page and automatic site map.
- `docs/topics/guide/guide.md`: canonical starter architecture and adoption checklist.
- `docs/topics/guide/index.md`: human-facing visual authoring guide.
- `docs/topics/fsrs-training/fsrs-training.md`: synthetic-client simulator, FSRS training method and results.
- `docs/topics/opening-library/opening-library.md`: opening library and side classification.
- `ml/ml_1000bots/`: synthetic-client simulator and FSRS training code; install and run commands in `ml/ml_1000bots/README.md`.
- `ml/ml_1000bots/openings/`: opening library files and the scripts that classify them.
- `ml/ml_1000bots/data/tempo_v1/`: dataset of the first training run; other generated datasets in `ml/ml_1000bots/data/` are ignored by Git.
- `ml/ml_1000bots/runs/`: one folder per training run with its parameters, results and raw outputs.
- `docs/open/OPEN.md`: unfinished-work routes.
- `docs/worklog.md`: append-only chronology.
- `.build/docs/`: ignored generated output, never source.

- `frontend/`: React browser application. See [frontend ownership and scope](topics/frontend/frontend.md).
- `backend/`: Python application, requirements, and demo data.

## Build and review

### Python backend

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m backend.web
```

The server listens on `127.0.0.1:8000` and uses the SQLite catalog and FSRS weights in `backend/`. Run `.\backend\run-demo.cmd` from the repository root for the terminal demo.

### Frontend development

Use Node.js 22.12 or later in the Node 22 line (or another Vite-supported release). From the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

With the Python backend running, open `http://127.0.0.1:5173`. Stop the server with Ctrl+C. Run `npm run build` in `frontend/` for TypeScript checking and a production build; `npm run typecheck` checks TypeScript alone. Generated `dist/` and installed `node_modules/` are ignored. Frontend commands do not build the documentation website.

Run `npm test` in `frontend/` for the Learning demo's sample-line, guided-retry and castling checks. This uses Node's built-in test runner and experimental TypeScript stripping on the recorded Node 22 environment.

### Documentation website

Run from the project root after initializing the submodule. Use Python 3.12 or the later version supported by the pinned kit.

```bash
python -m pip install -r .docs-kit/requirements.txt
python .docs-kit/docsite.py build --project .
python .docs-kit/docsite.py build --project . --check
python .docs-kit/docsite.py lint --project .
```

For an iteration, append `--page guide` to build; this does not validate unrelated output. For browser review:

```bash
python -m http.server 8321 --bind 127.0.0.1 --directory .build/docs
```

Open `http://127.0.0.1:8321/html/guide.html` through the approved browser surface. Check the listener's owner before reuse. Review wide, narrow and paired reading; inspect keyboard focus, reduced motion, no-JavaScript fallback and print. Consult the kit README for shared-engine development checks; Node.js is needed only for applicable JavaScript checks, not ordinary content builds.

## Documentation hosting

The [GitHub Pages workflow](../.github/workflows/pages.yml) checks out the pinned Documentation Kit, builds `.build/docs`, and runs strict lint before deploying. It publishes from `main`. The Pages artifact contains the generated documentation site.

A repository administrator enables the workflow under **Settings → Pages → Build and deployment → Source → GitHub Actions**. Once the first deployment succeeds, the workflow's `github-pages` environment shows the live URL.

## Documentation index

[Documentation reading index](index.md) · [Starter topic record](topics/guide/guide.md) · [Open work](open/OPEN.md) · [Worklog](worklog.md).
