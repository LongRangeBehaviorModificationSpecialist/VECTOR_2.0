# VECTOR 0.94 — field test, 29 September 2026

Notes for the build on branch `9-29-Actual-Test`: what it is, what
changed since the last build, what was checked, and what to do before
and during the search. Written 28-Sep-2026.

The branch is `fix/logo-launcher-and-navbar-width` with the original
author's two newest commits merged in and fixed. Nothing here has been
sent to the original project yet; if the test goes well, this is what a
pull request to it would contain.

---

## Before you leave

1. **Download the branch** from GitHub — the green **Code** button on
   the `9-29-Actual-Test` branch, then **Download ZIP** — and unzip it
   somewhere that is not a synced folder (OneDrive, iCloud Drive).
2. **Start it once tonight, with internet.** Double-click
   `Start VECTOR.bat` (Windows) or `Start VECTOR.command` (macOS). The
   first start installs what VECTOR needs, which takes a few minutes and
   needs a connection. After that it starts straight away and needs no
   internet at all: every page, script and style is served by VECTOR
   itself.
   - Windows may show a SmartScreen warning: **More info → Run anyway**.
   - macOS may refuse an app from an unidentified developer: right-click
     `Start VECTOR.command` → **Open** → **Open**.
3. **Sign in as `admin`** with the one-time password printed in the
   console window (also saved in `db/FIRST_RUN_PASSWORD.txt`), and
   choose a new password when asked.
4. **Do a practice run**: open a case, add an agent, a room, an item,
   print a report, export it. Then **clear the practice away**: stop
   VECTOR and delete the `db` folder. (Start New Case would clear the
   case, but the audit trail is never cleared, so the practice would
   stay in the real case's trail.) The next start makes a fresh `db`
   with a new one-time admin password — sign in and change it again,
   then **delete `db/FIRST_RUN_PASSWORD.txt`**.
5. **Create an account for each agent** who will enter data: **Welcome,
   admin → Admin Panel → Add New User**. Each gets a one-time password,
   shown once — write it down before closing the message. They choose
   their own at first sign-in. (Accounts live in `db`, so create them
   after step 4, not before.)
6. **If tablets or phones will be used**, turn on **Network access** in
   the Admin Panel, then stop and start VECTOR. **Help → Connect a
   Device** then shows the address to type on the other device. Both
   devices must be on the same network, and a guest network usually
   cannot reach the laptop. It is plain HTTP: use a network you control.

Do **not** copy the `db` folder from this development machine. It holds
the fictional demo case, and its audit trail fails its own check at
entry 63 (see below). A fresh download has no `db` folder and starts
clean.

## On the day

- **Start**: double-click the launcher; the browser opens at
  <http://localhost:8080>. Keep the console window open — closing it
  stops VECTOR.
- **Order of work**: Case → Agents → Rooms → Evidence → People → Notes →
  Files → Reports, as on the home page.
- **Messages**: prompts ("the Name field is required") and confirmations
  fade after a few seconds. A message saying something did **not**
  happen — not saved, not deleted, not imported, not exported, an
  attachment that no longer matches its hash — stays until **OK** is
  pressed. If one of those appears, read it before carrying on.
- **Idle sign-out**: a device left alone for 60 minutes signs itself
  out, with a warning a minute before. Saved records are kept; anything
  typed into a form but not yet saved is lost.
- **Photographs**: on a phone or tablet the Files page has **Take a
  photograph**, which opens the camera straight into the case. Each file
  is hashed (SHA-256) the moment it arrives.
- **Before leaving the scene**:
  1. Reports page → fill in the end time when it offers.
  2. Print what is needed. Printed reports now carry "Page X of Y".
  3. **Export** — CSV, JSON or **Both**, with a password if the file
     will travel. The file downloads through the browser.
  4. Check the export is where you expect it and opens. Copy it off the
     laptop.
  5. **Welcome, admin → Audit Trail → Check the trail**: it should say
     every entry matches.
- **Stopping**: Welcome → **Shutdown** (admins), or close the console
  window.

## What came from the original project

Two commits by the original author, merged as they are, with their
edits carried into the files this branch had split pages into:

**be7daa0 "edited UI" (25-Sep) and ba5b96f "slight UI improvements"
(28-Sep)**

- Every button has more padding and a dashed border when the pointer
  is over it (`hover-border-white` / `hover-border-blue`).
- The home page and Reports page buttons are larger and laid out in
  rows, built from tables (`home_page_buttons`, `action_buttons`,
  `report_buttons`).
- Messages that used to stay until OK now fade after four seconds
  (`WARN_TIMEOUT`), confirmations after three and a half
  (`CONFIRM_TIMEOUT`); red error messages became amber.
- Dialog buttons say what they act on: **Update Evidence**, **Delete
  Agent** rather than **Update**, **Delete**.
- **New Files report** (Reports → Print File List): every attachment
  with its type, upload time, who uploaded it and its SHA-256.
- Printed reports: "Page X of Y" at the foot, bordered evidence tables,
  table headers repeated on each page, "N/A" in empty fields.
- **Exports are recorded in the audit trail** (new **EXPORT** filter on
  the Audit Trail page), and the CSV manifest records a SHA-256 of each
  table's CSV. The JSON layout is version 1.2.
- SHA-256 digests are written in capitals.
- Two columns renamed: `PERSONS.SUSPECTNOTE` → `PERSONNOTE`, and
  `FILES.FILEHASHEDAT` → `FILEHASHEDDATETIME`.
- Import and export success messages reworded; the console printout
  after an export or import removed.
- Much of the code reformatted (long lines split).

All of that is kept. The only places this build departs from it are the
fixes below.

## What was fixed on top of it

Found by trying the author's commits against a copy of a real database,
by running the tests, and by a walk-through of the running application
on a fresh database.

1. **An existing database would not open** (0485770). The column
   renames had no migration, so VECTOR stopped at startup with
   `no such column: PERSONS.PERSONNOTE` for every database made before
   them. Both renames now go through the existing migration: the columns
   are renamed in place after the usual backup, and older exports import
   with their notes and hashing times. A database opened once by the
   author's version — which added the new hashing column empty beside
   the old one — has the old times copied across.
2. **Every attachment collected before was reported as altered**
   (0c2fc13). The new capital-letter digests were compared as text with
   the lower-case ones already recorded, so an export of untouched files
   said "these attachments no longer match the SHA-256 recorded when they
   were collected" and wrote `FILEHASHMATCHES: false` into the manifest;
   an import of an older export would have marked every file unverified.
   Digests are now compared as digests. Nothing stored is rewritten, and
   the Files page and Files report show every digest in capitals.
3. **The audit trail could fail its own check after an upgrade**
   (09dc84f). This one was in this branch's own code, from 24-Sep, and
   was found because the demo database failed "Check the trail" at entry
   63. When an older database was upgraded, the date rewrites wrote audit
   entries *before* the old entries were fingerprinted, so the first new
   entry was chained onto nothing. The upgrade now fingerprints first,
   and never fills in an old entry that a later one was already chained
   past. The demo database stays reported as broken at entry 63 —
   correctly: nothing may re-seal a trail after the fact. A new database
   is not affected.
4. **Failure messages vanished after four seconds** (9d1d3a0). Kept for
   prompts and confirmations; a message that says something did not
   happen stays until OK again (`ZERO_TIMEOUT`, the author's own name for
   it). Colours stay amber, as the author made them. Also:
   - "Nothing was imported (ln 1354), and…" — a debugging note in a
     message users see — removed.
   - "User "x" deleted.Their open sessions…" — the missing space put back.
   - Start New Case showed two "deleted" messages; now one.
   - An export whose audit record fails no longer leaves its staging
     folder behind.
5. **A test that could not fail, and lint** (42d67ba). Reformatting had
   turned `assert not missing, "…"` into `assert (not missing, "…")`, a
   tuple that is always true — the check that every button the Help page
   names exists could never fail. Also an unused import and a dropped
   `# noqa`.
6. **The Files report printed upload times in UTC with no zone**
   (63c0481). A photograph uploaded at 23:05 on the 28th printed as
   "2026-09-29 03:05:35.241675". It now prints "09-28-2026 23:05:35
   UTC-04:00", as the Files page shows it. Found in the walk-through.
7. **This branch's own buttons** (Check the trail, Show older entries,
   the idle warning) take the author's hover style (3b8ee66).
8. **Version 0.94, 28-Sep-2026** on the About page, and the first-run
   banner's first rule lined up with the others (eb2364a).

The tests the author's commits broke were updated where the change was
intended (exports now return the file and a message; JSON is 1.2) and
put back where the change was not (the "legacy" test fixtures had been
renamed to the new column names, so they no longer tested a legacy
database).

## What was checked

- **445 tests pass** (429 before the merge; the 16 new ones cover the
  fixes). The author's own suite on their commits: 18 failures and 9
  errors.
- **ruff** (the CI lint job): clean.
- **Six page simulations** — export, import with and without a password,
  Delete All, the Admin Panel, the Files page, record editing and
  renumbering — all pass, driving the real pages.
- **A copy of this machine's database** opens and migrates: notes kept,
  columns renamed, backup made.
- **Walk-through of the real application on a fresh database**: first
  run and the forced password change; opening a case; a required-field
  prompt; the Files page with one attachment hashed the old way and one
  the new way; the Files report; an export in both formats (no false
  integrity warning, both files marked as matching, both exports in the
  audit trail); Check the trail (all entries match); the Admin Panel;
  the Reports page.
- **The top bar** measured at 375, 1280, 1320, 1366, 1440, 1599, 1600
  and 1920 px: one line at every width, nothing wider than the screen.
  It is 80 px tall now rather than 68, from the author's taller buttons.

## Worth knowing

- **Agent roster.** Agent names are remembered from scene to scene in
  `parts/agents.json` on the laptop, not in the case. This development
  machine's roster holds a test entry ("Brand, New"); a fresh download
  has none.
- **Page counters on printed reports** ("Page X of Y") need a current
  Chrome or Edge; other browsers may leave them off.
- **Network access is plain HTTP.** Fine on a hotspot or network you
  control; do not use it on a public network.
- **Import replaces the whole case.** It asks first, and a failed import
  leaves the case as it was, but a successful one replaces everything
  except this laptop's audit trail.
- **Held back:** the "save a copy of the database before Start New
  Case" change (`feature/new-case-db-copy`) is not in this build.

## Commits in this build since the last one

| Commit | What |
|--------|------|
| be7daa0, ba5b96f | The original author's two commits |
| ee952bb | Merge, with their edits carried into the split files |
| 0485770 | fix: a database or export from before the renames opens again |
| 0c2fc13 | fix: an attachment hashed in lower case is not reported as altered |
| 09dc84f | fix: upgrading a database no longer breaks the audit trail's chain |
| 9d1d3a0 | fix: a message saying something did not happen stays until OK |
| 42d67ba | fix: the lint job passes again, and a Help test can fail again |
| 3b8ee66 | style: this branch's own buttons take upstream's hover borders |
| 63c0481 | fix: the Files report prints upload times in local time |
| eb2364a | chore: version 0.94, and the first-run banner lines up |

Each commit message has the full reasoning.

## If it goes well

A pull request from this branch to the original project, with these
notes as its description. Two things to raise with the author when it
is offered: the column renames need the migration entries in commit
0485770 for anyone who already has a case database, and the capital
letters in digests need comparing as digests (0c2fc13).

## Notes from the day

_(Anything that went wrong or was awkward, to fix before the pull
request.)_

-
