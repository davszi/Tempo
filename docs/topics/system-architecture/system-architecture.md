# TEMPO system architecture

This record captures the first-version design discussed for TEMPO. The application uses a Python backend and SQLite. It has Learning and Repeating modes that write to a shared practice history. See [project context](../../PROJECT_CONTEXT.md) for TEMPO's terminology and team-level decisions.

## Components and data flow

The [architecture diagram](component-flow.mmd) shows the live Python application and offline training. In the live application, solid arrows show requests and dashed arrows show responses. The offline arrows show where data and the trained model go.

| Component | Responsibility |
|---|---|
| Chess UI | Displays the board, Learning line selection and move arrows, and Repeating retry feedback. |
| UI controller | Loads lines, starts sessions, checks attempted moves against the repertoire move, and records practice events. It requests the next line for Repeating. |
| SQLite | Stores opening lines and each player's practice events, including past suggestions. |
| ML controller | Loads the player's repertoire, practice history, and past suggestions. It calls the ML engine, records the suggestion when a line is selected, and returns the result to the UI controller. |
| ML engine | Uses FSRS and the review planner to return a line ID or indicate that no line is due. It uses line IDs and practice history as inputs so the planner can be reused beyond chess. |
| Offline training | Synthetic clients generate simulated practice history in a CSV. A Python training script reads the CSV and writes the general model artifact that the ML engine loads. SQLite holds real player events. |

## Learning and Repeating

In **Learning**, the player chooses an opening and line. The UI controller loads the moves from SQLite. The board highlights the expected move with an arrow. A matching move advances the line, and a wrong move leaves the board at the same position for a guided retry. Completing the session adds the line to the player's repertoire.

In **Repeating**, the UI controller requests the next line from the ML controller. When the planner returns a line ID, the UI controller loads the line from SQLite and opens it automatically. The player recalls each move without hints. A wrong move is taken back immediately so the player can retry from the same position.

With an empty repertoire, the UI directs the player to Learning. For a player who has learned a line and has no suggestion history, the ML controller passes an empty history and uses the initial FSRS schedules. The first-version rule is to pick the most overdue line, with the earliest learned line breaking ties. If no line is due, the UI shows that state.

## Review scheduling

The planner derives the player's repertoire from completed Learning sessions. It calculates each line's next review date from the initial schedule and the ratings and timestamps of completed Repeating sessions. The initial scheduling rule, how ratings are assigned, how FSRS and the trained model share line selection, and when personalization runs still need team decisions.
