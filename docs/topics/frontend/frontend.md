# Frontend dashboard milestone

## Current Learning and Review flow

The React app uses the Python API in `backend/web.py` for the opening catalog, move checks, Learning completion, and Review. Completing a line saves it to the player's SQLite repertoire. The review planner selects the line, the board hides the move arrow, and completion stores the FSRS grade and next review date. The frontend uses a browser-local demo player ID. The prototype milestones below describe earlier revisions.

Since 2026-11-13 the Learning list shows only lines the backend marks `learnable`: lines that no other line in their family extends. When several of those lines share a name, each card shows the moves from where it first differs from the others, for example "7…Be6 8.f3", computed by `distinguishingMoves` in `frontend/src/lib/learning.ts`. [Opening catalog structure](../opening-catalog/opening-catalog.md) owns these rules. The change has a unit test in `frontend/tests/learning.test.mjs`. With Node.js 26.13.1, `npm test` passed 4 tests and `npm run build` passed; the live Learning page listed 1,889 lines with distinct labels on same-name lines and no console errors.

## Scope and ownership

Zeel owns the React frontend in `frontend/`. The frontend implements the dashboard, navigation, opening library and a guided Learning demo using sample data. The combined Repeating & reviews destination and settings are placeholders. Backend, database and ML implementation are outside this change.

## Learning library and guided board

On 2026-11-12, Zeel supplied an opening-card reference image and requested its layout idea while preserving TEMPO's existing colors and fonts. Learning mode groups board-preview cards under King's Pawn Openings, with White-side labels, learned-line counts, guided-move counts and functional bookmarks. Ruy López, Italian Game and Scotch Game are frontend sample lines, not a query of the database catalog. Retention percentages from the reference image are not included because no model-backed values are available.

Selecting a card opens a White-side guided lesson. An SVG arrow points from the prescribed piece's source square to its destination, with the same coordinates written next to the board. The learner clicks/taps a piece and destination, or uses Tab and Enter. A wrong move leaves the position unchanged and displays retry feedback. A correct White move includes the scripted Black reply and updates the arrow. Castling updates both king and rook. Restart resets the line. Completion marks the line learned in this Learning visit; returning to the library preserves those marks and bookmarks until the Learning page unmounts or the browser reloads.

`chess.js` 1.4.0 validates sample positions and supplies move coordinates. `frontend/src/lib/learning.ts` is a demo adapter only: real session checking, completion records and history remain the backend Practice controller's responsibility. No backend files or authentication flow are changed. Only the White-side sample experience is implemented; no data is persisted or submitted to the backend, and the arrow is confined to Learning mode.

Validation: `npm test` passed three tests covering every sample line and preview, rejected off-line moves, automatic replies and castling. `npm run build` passed TypeScript and production bundling. Browser checks completed a Ruy López session, rejected e2-e3 without changing position, played Black's reply, updated Learned to 1/1, toggled an Italian bookmark, and advanced using Enter on mobile. Visual checks used 1440-by-1000 desktop and 390-by-844 mobile layouts, with no horizontal page overflow on mobile and no browser console errors. Captures are `.build/frontend-review/learning-library.jpg` and `.build/frontend-review/learning-session.jpg`. These are frontend demo checks, not verification of backend integration or training results.

Navigation update on 2026-11-12: Repeating mode and Review planner share the `practice` destination, labeled Repeating & reviews (Review on mobile). Settings is absent from the main and bottom navigation; the bottom-left profile avatar opens it. Mobile also exposes a profile button in the top bar, and the drawer retains the profile entry. Settings remains directly addressable at `#settings`. `npm run build` passed. Browser checks verified opening Settings from the desktop and drawer profile buttons, the combined mobile review destination, and returning to Dashboard. Preview: `.build/frontend-review/dashboard-profile-navigation.jpg`.

## Design source

Adapted from the user-supplied `Tempo - Chess Learning.zip`, specifically its `src/App.tsx` and `src/index.css`, exported from Figma file `RuaZoTR5SPWuefaVP1TYHO`, Code Layer `2:3`. Dashboard colors, typography, Lucide icons, chess glyphs, cards and chart structure come from that export. The authentication photograph is not used on the dashboard. The original archive stays unchanged in Downloads.

The export's local-storage account/password implementation, lesson logic, review scheduling and Figma-specific development scripts are not included. The app opens directly into the dashboard with sample data. No authentication or backend requests are implemented.

## Requested simplification

On 2026-11-12, Zeel also requested removal of Opening lines learned, Reviews due today and the entire Upcoming reviews section. The dashboard now contains the welcome area and Start learning / Start review actions. Removed the unused schedule component, date helpers, progress types, mock practice data and associated styles. The sample profile remains. TypeScript checking and the production build passed via `npm run build`; the refreshed browser confirmed the removed content is absent and the remaining actions render. Preview capture: `.build/frontend-review/dashboard-actions-only.jpg`.

Follow-up sizing: learning and review actions use a 160px minimum height on desktop and 140px on mobile, larger icons and headings, and increased spacing. Upcoming reviews sizes to its content, with compact day tiles instead of stretching to fill a fixed-height row. The planner link aligns to the right on desktop. `npm run build` passed after this CSS change. Browser checks at 1280-by-850 and 390-by-844 confirmed the intended action heights and no horizontal page overflow; the desktop schedule was approximately 237px tall. These dimensions describe this checked layout, not a performance claim. Preview: `.build/frontend-review/dashboard-sized.jpg`.

On 2026-11-11, Zeel requested removal of the Memory retention chart, Accuracy, Review streak and Skills mastered cards, and the frontend preview banner. Those sections and their unused calculations, mock history and styles were removed. Upcoming reviews now spans the available content width. The welcome card, learned-line and due-review totals, actions and navigation remain.

Validation after removal: `npm run build` passed TypeScript checking and the production build. The refreshed live dashboard's accessibility tree confirmed that all five requested items are absent and the remaining dashboard sections are present. A preview capture is saved at `.build/frontend-review/dashboard-simplified.jpg`.

## Structure

- `frontend/src/App.tsx`: page selection, hash-based navigation, mobile menu and placeholder destinations.
- `frontend/src/components/`: dashboard, navigation and logo components.
- `frontend/src/components/LearningPage.tsx` and `ChessBoard.tsx`: opening library, guided session and reusable board with SVG arrows.
- `frontend/src/data/openings.ts`: sample lines, preview positions and move explanations.
- `frontend/src/lib/learning.ts`: pure sample position and guided progression functions.
- `frontend/tests/learning.test.mjs`: sample-line and move-flow tests.
- `frontend/src/learning.css`: library and learning-session layout using the existing TEMPO theme.
- `frontend/src/mocks/dashboard.ts`: sample user profile; replace through an agreed backend interface later.
- `frontend/src/index.css`: styles adapted from the export, plus responsive and keyboard-accessibility fixes.
- `frontend/vite.config.ts`: standard React and Tailwind Vite plugins; no Figma-hosted runtime integration.

React 19, TypeScript, Vite 8 and Tailwind CSS 4 follow the exported stack. Node 22.14.0 and npm 11.3.0 are the local environment used for this work. Dependencies and their lockfile belong inside `frontend/`.

## Behavior and limits

The source implements dashboard actions that navigate to named placeholder destinations, hash-based back/forward navigation, and a mobile drawer with Escape, focus trapping and focus restoration. Background content is marked inert while the drawer is open. Desktop CSS permits scrolling on short displays instead of clipping the exported fixed-height layout. Mobile uses the exported top bar, drawer and bottom navigation. These behaviors still require runtime verification.

All displayed progress is illustrative, not a record of Zeel's actual play. The planner and move-checking boundaries still require team agreement. Google Fonts supplies DM Sans and Manrope, with system fallbacks if unavailable.

## Validation

On 2026-11-11, source inspection confirmed that the adapted frontend contains no `localStorage`, password handling or `fetch` calls. No backend, database or ML source files were changed.

`npm install` could not resolve the npm registry inside the sandbox. An approved `npm install --fetch-retries=0 --fetch-timeout=30000` reached the registry but stalled during file creation. A separate Node directory-creation check also stalled. Windows Defender Operational events with ID 1123 confirmed that `C:\Program Files\nodejs\node.exe` was blocked from modifying this OneDrive checkout. Both stalled processes were interrupted. Security settings were not changed.

The user chose to allow Node through Controlled Folder Access and will confirm when that is done. Resume with dependency installation, `npm run build`, and desktop/mobile browser review. No successful installation, TypeScript check, production build, running server or visual-fidelity result is claimed yet. Run commands are in the project context.

### Successful follow-up, 2026-11-11

The preceding paragraph records the initial blocker; it is now resolved. After the user confirmed Node was allowed, `npm install --fetch-retries=0 --fetch-timeout=30000` completed and npm reported zero vulnerabilities. `npm run build` passed TypeScript checking and the Vite 8.3.8 production build. Generated output is ignored in `frontend/dist/`; versions are retained in `frontend/package-lock.json`.

`npm run dev` serves the app at `http://127.0.0.1:5173/`. The current package script already fixes the port and enables strict-port behavior. Appending CLI port arguments failed because of npm argument parsing; the plain command succeeded. The server was relaunched outside the sandbox so the browser could connect. Preview session 67340 is retained for the user; Ctrl+C stops it.

Browser review confirmed the dashboard, learning destination placeholder, browser-back return, mobile menu opening, Escape dismissal with focus restored to the menu button, mobile Reviews destination and return to dashboard. Checked desktop layout and a 390-by-844 mobile viewport; DOM inspection reported no horizontal page overflow at that mobile size. No browser console errors were reported. A preview capture is retained at `.build/frontend-review/dashboard.jpg` (ignored). These are focused smoke checks, not exhaustive accessibility or cross-browser certification. Pixel-level comparison with a live Figma dashboard was unavailable; the exported dashboard source supplied the design reference.
