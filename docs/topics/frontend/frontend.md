# Frontend dashboard milestone

## Scope and ownership

Zeel owns the React frontend in `frontend/`. This milestone implements the dashboard and navigation using sample data. Learning mode, Repeating Mode, review planner and settings destinations are explicit placeholders. Backend, database and ML implementation are outside this change.

## Design source

Adapted from the user-supplied `Tempo - Chess Learning.zip`, specifically its `src/App.tsx` and `src/index.css`, exported from Figma file `RuaZoTR5SPWuefaVP1TYHO`, Code Layer `2:3`. Dashboard colors, typography, Lucide icons, chess glyphs, cards and chart structure come from that export. The authentication photograph is not used on the dashboard. The original archive stays unchanged in Downloads.

The export's local-storage account/password implementation, lesson logic, review scheduling and Figma-specific development scripts are not included. The app opens directly into the dashboard with sample data. No authentication or backend requests are implemented.

## Requested simplification

Follow-up sizing: learning and review actions use a 160px minimum height on desktop and 140px on mobile, larger icons and headings, and increased spacing. Upcoming reviews sizes to its content, with compact day tiles instead of stretching to fill a fixed-height row. The planner link aligns to the right on desktop. `npm run build` passed after this CSS change. Browser checks at 1280-by-850 and 390-by-844 confirmed the intended action heights and no horizontal page overflow; the desktop schedule was approximately 237px tall. These dimensions describe this checked layout, not a performance claim. Preview: `.build/frontend-review/dashboard-sized.jpg`.

On 2026-11-11, Zeel requested removal of the Memory retention chart, Accuracy, Review streak and Skills mastered cards, and the frontend preview banner. Those sections and their unused calculations, mock history and styles were removed. Upcoming reviews now spans the available content width. The welcome card, learned-line and due-review totals, actions and navigation remain.

Validation after removal: `npm run build` passed TypeScript checking and the production build. The refreshed live dashboard's accessibility tree confirmed that all five requested items are absent and the remaining dashboard sections are present. A preview capture is saved at `.build/frontend-review/dashboard-simplified.jpg`.

## Structure

- `frontend/src/App.tsx`: page selection, hash-based navigation, mobile menu and placeholder destinations.
- `frontend/src/components/`: dashboard, navigation, logo and upcoming review components.
- `frontend/src/mocks/dashboard.ts`: sample user and practice history; replace through an agreed backend interface later.
- `frontend/src/lib/dates.ts`: local calendar date helpers.
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
