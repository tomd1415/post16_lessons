# Lesson 1 design/system inventory

Scope: This inventory captures the reusable UI patterns, behaviors, and data structures in the Lesson 1 resource pack. It is the baseline for future lessons and the platform shell.

## Source of truth
- Lesson 1 pages: `web/lessons/lesson-1/`
- Core shared assets (extracted): `web/core/app.css`, `web/core/app.js`
- Lesson 1 data: `web/lessons/lesson-1/assets/data.js` (global `window.LESSON1_DATA`)

## File structure (Lesson 1)
- Hubs
  - `web/lessons/lesson-1/index.html` (teacher hub)
  - `web/lessons/lesson-1/student.html` (student hub)
- Activities
  - `web/lessons/lesson-1/activities/01-what-is-a-computer.html`
  - `web/lessons/lesson-1/activities/02-key-terms-match.html`
  - `web/lessons/lesson-1/activities/03-decomposition-robo-chef.html`
  - `web/lessons/lesson-1/activities/04-patterns-recipes.html`
  - `web/lessons/lesson-1/activities/05-abstraction-filter.html`
  - `web/lessons/lesson-1/activities/06-algorithm-sorting.html`
  - `web/lessons/lesson-1/activities/07-big-problems.html`
  - `web/lessons/lesson-1/activities/08-mini-assessment.html`
- Teacher resources
  - `web/lessons/lesson-1/teacher/lesson-plan.html`
  - `web/lessons/lesson-1/teacher/print-cards.html`
  - `web/lessons/lesson-1/teacher/answer-key.html`

## Visual design tokens (core CSS)
Defined in `:root` in `web/core/app.css`.
- Colors
  - `--bg` #0b0f14, `--panel` #121824, `--panel2` #0f1420
  - `--text` #e8eef6, `--muted` #b9c6d8
  - `--accent` #6aa6ff
  - `--good` #49d17a, `--bad` #ff5d5d, `--warn` #ffc857
  - `--border` rgba(255,255,255,.14)
- Radius and shadows
  - `--radius` 16px, `--radius2` 22px, `--shadow` 0 12px 30px rgba(0,0,0,.35)
- Typography
  - `--sans` system UI stack
  - `--mono` monospace stack
- Layout
  - `--maxw` 1100px, `--pad` 18px

## Core layout patterns (CSS classes)
- `body` uses a dark gradient background and 18px base font size
- `.container` centered max width with padding
- `.topbar` sticky header with blur and border
- `.nav-row` holds the global nav and breadcrumb row
- `.row` flex row for buttons and quick actions
- `.grid` plus modifiers `.cols2`, `.cols3` for responsive grids
- `.split` two-column layout with sticky `.nav` (defined but not currently used)
- `.card` primary panel container with rounded corners and shadow

## Core UI components
- Buttons: `.btn` with variants `.primary`, `.good`, `.bad`
- Global nav: `.global-nav` with `.nav-item` (adds `.active` for current page)
- Breadcrumbs: `.breadcrumb` with `.crumb-sep` and `.crumb-current`
- Pills: legacy `.pill` markup (removed at runtime and replaced by global nav)
- Notes: `.note` with variants `.warn`, `.good`, `.bad`
- Badges/tags: `.badge`, `.tag`
- Keyboard callouts: `.kbd`
- Tables: `.table` with muted header styling
- Inputs: `.input`, `textarea`, `select`
- Toasts: `.toast` + `.toast.show`
- Print controls: `.no-print` is hidden on print

## Print styles
Defined in `@media print` in `web/core/app.css`.
- Hides `.topbar`, `.nav`, `.no-print`
- Removes box shadows
- Converts background to white and text to black
- `teacher/print-cards.html` adds extra print-specific rules for card layout

## Behavior patterns (core JS)
Defined in `web/core/app.js`.
- Helpers: `$`, `$$`
- Local storage wrapper: `store.get`, `store.set`, `store.del` (JSON payloads)
- Toast messages: `toast(msg)` (auto hides in 2.4s)
- Teacher mode
  - Toggle button `#teacherToggle`
  - Query param `?teacher=1` forces on (staff roles only)
  - Storage key `tlac_teacher_mode`
  - Shows/hides `.teacher-only` blocks
  - Sets `document.documentElement.dataset.teacher`
- Role-based navigation
  - `#roleMenu` is rendered based on the signed-in role
  - Teacher hub links are hidden for pupils
- Utilities: `shuffle`, `uid`, `downloadText`, `printPage`

## Lesson 1 data contract
`web/lessons/lesson-1/assets/data.js` defines `window.LESSON1_DATA` with:
- `meta`: title, version, generated timestamp, offline flag
- `learningObjectives`: array of strings
- `terms`: list of `{term, definition}`
- `devices`: list of `{name, hint}`
- `recipes`: list of `{title, steps[]}`
- `abstractionPrompts`: list of `{title, question, items[{text, keep}], explain}`
- `bigProblems`: list of `{title, starter, exampleIdeas[]}`
- `quiz`: `{title, questions[]}` where questions are `mcq` or `short`

## Activity behavior inventory
All activities use localStorage state and optional export to JSON.

1) Activity 01 (What counts as a computer)
- File: `web/lessons/lesson-1/activities/01-what-is-a-computer.html`
- State key: `tlac_l1_a01_state`
- Behavior: select device card, place into a bin, optional reflection
- Export: `lesson1-what-is-a-computer.json`
- UI patterns: selectable cards, bins, move/remove controls

2) Activity 02 (Key terms match)
- File: `web/lessons/lesson-1/activities/02-key-terms-match.html`
- State key: `tlac_l1_a02_state`
- Behavior: match term to definition, flashcards toggle
- Teacher mode: shows correctness column and guidance block

3) Activity 03 (Decomposition - Robo-chef)
- File: `web/lessons/lesson-1/activities/03-decomposition-robo-chef.html`
- State key: `tlac_l1_a03_state`
- Behavior: editable function tree with add/edit/delete via prompts
- Export: `lesson1-robo-chef-decomposition.json`
- Print support

4) Activity 04 (Pattern recognition)
- File: `web/lessons/lesson-1/activities/04-patterns-recipes.html`
- State key: `tlac_l1_a04_state`
- Behavior: select common steps, build reusable template
- Export: `lesson1-pattern-recognition.json`
- Print support

5) Activity 05 (Abstraction filter)
- File: `web/lessons/lesson-1/activities/05-abstraction-filter.html`
- State key: `tlac_l1_a05_state`
- Behavior: select essentials, check results, teacher-only explanation
- Export: `lesson1-abstraction.json`

6) Activity 06 (Algorithms - sorting)
- File: `web/lessons/lesson-1/activities/06-algorithm-sorting.html`
- State key: `tlac_l1_a06_state`
- Behavior: line sort with up/down, circle heuristic, bubble sort demo
- Export: `lesson1-sorting.json`

7) Activity 07 (Big problems decomposition)
- File: `web/lessons/lesson-1/activities/07-big-problems.html`
- State key: `tlac_l1_a07_state`
- Behavior: add/edit/delete sub-problems, validate software idea requirement
- Export: `lesson1-big-problems.json`

8) Activity 08 (Mini assessment)
- File: `web/lessons/lesson-1/activities/08-mini-assessment.html`
- State key: `tlac_l1_a08_state`
- Behavior: MCQ + short answers, auto score summary, teacher key points
- Print support

## Cross-cutting conventions
- Every page includes:
  - Topbar with brand and teacher toggle
  - Global nav + breadcrumbs injected into `.topbar .container`
  - `.container` wrapper
  - Toast container `#toast` with `role="status"` and `aria-live="polite"`
- All activities persist to localStorage; pupils see latest state only
- Exports are always JSON files via `downloadText`
- Teacher hints are always inside `.teacher-only` blocks
- Print guidance appears in a footer `.no-print` block

## Known gaps (intentional in Lesson 1)
- No global progress tracking across activities
- No server-backed persistence
- No accounts or roles
- No analytics or attempt history beyond localStorage

## Implementation constraints to preserve
- Maintain the exact CSS variables, component classes, and spacing values
- Do not change teacher mode behavior or storage keys
- Keep activity interactions and localStorage structure intact
- Ensure print styles and `.no-print` behavior remain unchanged
