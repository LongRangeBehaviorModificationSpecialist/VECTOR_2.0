# V·E·C·T·O·R

**Virginia Evidence Collection, Tracking, Organization & Reporting**

A local web application for documenting the execution of a search
warrant: who was on site, how the premises were divided, what was
seized from where, who found it and who witnessed it. It prints the
scene paperwork and exports the case as an encrypted archive.

VECTOR runs on your own machine. Nothing is sent anywhere.

`Python 3.10+` · `NiceGUI 3.16` · `SQLite` · `Windows · macOS · Linux` · `231 tests`

> **About this fork.** VECTOR was created by SSA M. Sponheimer of the
> Virginia State Police NOVA/DC ICAC
> ([original repository](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0)).
> This fork stays in step with that project and adds security
> hardening, an audit trail, optional database encryption, a test suite
> and a cross-platform install. See
> [What this fork adds](#what-this-fork-adds), and the full list offered
> back to the original project in
> [pull request #2](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0/pull/2).

---

## Contents

- [What it does](#what-it-does)
- [What this fork adds](#what-this-fork-adds)
- [Quick start](#quick-start)
- [Requirements](#requirements)
- [Install](#install)
- [Run](#run)
- [Access from another device](#access-from-another-device)
- [Using it](#using-it)
- [Accounts and sessions](#accounts-and-sessions)
- [The audit trail](#the-audit-trail)
- [How data is protected](#how-data-is-protected)
- [Encrypting the case database](#encrypting-the-case-database)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Tests](#tests)
- [Demo data](#demo-data)
- [How the code is laid out](#how-the-code-is-laid-out)
- [Development](#development)
- [Credits](#credits)

---

## What it does

**On scene**

- **Case** — number, address, jurisdiction, and when the search began
  and ended
- **Agents** — everyone on site, kept in a roster that pre-fills the
  next warrant
- **Rooms** — the premises lettered A, B, C… and on to AA, AB, with two
  agents assigned to each
- **Evidence** — numbered automatically, with where it was found, who
  found it, and a witness who must be someone else
- **People** — suspects and others present
- **Notes** — timestamped narrative, attributed to whoever is signed in
- **Files** — photographs and documents, hashed the moment they arrive

**Afterwards**

- **Seven printable reports**, including the basic inventory left as
  the return copy
- **Export** as a ZIP of CSVs, a single JSON file, or both — optionally
  AES-256 encrypted
- **Import** either format back, with every attachment checked against
  the hash taken when it was collected

**Throughout**

- **An append-only audit trail** of every change, sign-in and wipe
- **Accounts** with one-time passwords, sign-in throttling and sessions
  an admin can end
- **Several devices at once** over a local network, when you choose to
  allow it
- **Optional encryption** of the case database itself

---

## What this fork adds

Everything the original does, plus:

| Area | Change |
|------|--------|
| **Access control** | The admin panel and shutdown require an admin account. Network access is off by default; `--lan` opts in |
| **Passwords** | A one-time password per account instead of a shared default; throttling and lockout on failed sign-ins; sessions an admin can end |
| **Audit trail** | Every create, edit, delete, wipe, import and sign-in, with field-level before and after |
| **Evidence integrity** | A SHA-256 taken when each file is uploaded, verified again at export and at import |
| **Encryption** | Optional SQLCipher encryption of both databases, with tools to convert either way |
| **Reliability** | Reports and export working; evidence numbering past item 9; room letters past Z; uploads over 1 MB; no more "database is locked"; imports that are all or nothing; failures explained in plain words |
| **Several devices** | Open pages refresh on their own when another device saves, and the case badge follows |
| **Data handling** | Case databases kept out of version control; a fictional demo case for evaluation; automatic schema upgrades with backups |
| **Maintainability** | Six hand-written entity pages replaced by declarations and one table-driven builder; one route table with one guard |
| **Install** | A double-click launcher that sets itself up, pinned dependencies, step-by-step Windows and macOS instructions, and a start that works from any folder |
| **Tests** | 275 tests covering reports, export round trips, the audit trail, migrations, sign-in and encryption |

It also carries the original project's most recent work — JSON export,
the active-case badge and guard, the capitalised column names and the
refreshed interface — with fixes made while bringing it across.

Every change, with the reasoning behind it, is listed in
[pull request #2](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0/pull/2)
to the original project.

---

## Quick start

With [Python 3.10 or newer](#requirements) installed, double-click the
launcher in the project folder:

- **Windows** — `Start VECTOR.bat`
- **macOS** — `Start VECTOR.command`

The first start sets up a `.venv` folder and installs what VECTOR needs,
which takes a few minutes and an internet connection; after that it
starts straight away. The same by hand:

**Windows**

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

**macOS / Linux**

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Your browser opens at <http://localhost:8080>, and the console prints a
one-time administrator password — see [First run](#first-run). To look
around with a worked example first, load the [demo case](#demo-data).

The sections below cover each step in full.

---

## Requirements

- **Python 3.10 or newer**
- About 200 MB of disk for the virtual environment

Check what you have:

```
python --version
```

If that reports Python 2, or "command not found", use `python3` in
place of `python` throughout.

**Windows** — install from [python.org](https://www.python.org/downloads/windows/).
Tick **"Add python.exe to PATH"** on the first screen of the installer.

**macOS** — the bundled `python3` is a stub. Install a real one from
[python.org](https://www.python.org/downloads/macos/) or with Homebrew:

```
brew install python
```

---

## Install

Clone the repository, then from inside the project folder:

**macOS / Linux**

```
python3 -m venv .venv
```

```
.venv/bin/pip install -r requirements.txt
```

**Windows**

```
python -m venv .venv
```

```
.venv\Scripts\pip install -r requirements.txt
```

No compiler is needed. Every dependency ships as a prebuilt wheel for
Windows, Intel Mac and Apple Silicon.

### Unit branding (optional)

The logos and the browser tab icon are not distributed with the
source. See [`static/README.md`](static/README.md) for the filenames.
VECTOR runs without them — each page shows just its title.

---

## Run

Double-click `Start VECTOR.bat` (Windows) or `Start VECTOR.command`
(macOS). It sets up `.venv` if it is missing, installs again if
`requirements.txt` has changed since the last start — after an update,
say — and then starts VECTOR. From a terminal instead:

**macOS / Linux**

```
.venv/bin/python main.py
```

**Windows**

```
.venv\Scripts\python main.py
```

Your browser opens at <http://localhost:8080>.

VECTOR runs only while that window is open. Closing it, or
pressing `Ctrl+C`, stops the application; nothing is left running in
the background.

### First run

VECTOR creates its databases and prints a one-time administrator
password:

```
==============================================================
  FIRST RUN - an administrator account has been created.
==============================================================
    Username:  admin
    Password:  64xhZN0pDYhwPG73
```

The same credentials are written to `db/FIRST_RUN_PASSWORD.txt` in case
the console scrolls. You will be asked to change the password
immediately; delete that file once you have.

Every password VECTOR issues — at first run, when an admin creates an
account, and when an admin resets one — is generated for that account
and shown **once**. There is no shared default. Write it down before
closing the message; it cannot be recovered, only reset again.

### Upgrading an existing database

If you already have databases from an earlier version, the first start
after upgrading brings them up to date. Each database is copied to a
timestamped `.bak` beside it before anything changes, and every step
runs once:

- **Names.** PERSONS, FILES and users take the upstream project's
  capitalised column names — `SUSPECTNAME` → `PERSONNAME`, `file_name`
  → `FILENAME`, `user_name` → `USERNAME`, and so on. Columns are renamed
  in place, so no row is copied and every password keeps working.
- **Constraints.** A table still carrying a unique constraint that
  blocked ordinary scenes — a second agent with no email address, a
  house with two bedrooms, the same photograph attached twice — is
  rebuilt without it.
- **Dates.** Case times and dates of birth stored as `YYYY-MM-DD` are
  rewritten as `MM-DD-YYYY`, the format the input masks now use. Each
  change is recorded in the audit trail.

A database from before the renames prints:

```
Schema migration: backed up app_data.db to app_data.db.bak-20260915-000534
Schema migration: PERSONS -> PERSONS, 4 column(s) renamed
Schema migration: files -> FILES, 9 column(s) renamed
Schema migration: backed up users.db to users.db.bak-20260915-000534
Schema migration: users -> users, 7 column(s) renamed
Schema migration: added FILES.FILENOTE
```

The write-ahead log is folded in before the copy, so the backup holds
the most recent entries too. Keep it until you have confirmed the case
looks right, then delete it — it is a full copy of the case.

Exports made by earlier versions, and by the upstream project, still
import: old table and column names are read as the names they became.

---

## Access from another device

By default VECTOR listens on **loopback only** — it is not reachable
from the network, and nothing on your Wi-Fi can see it.

To open it to other devices on the same network, add `--lan`:

**macOS / Linux**

```
.venv/bin/python main.py --lan
```

**Windows**

```
.venv\Scripts\python main.py --lan
```

The launchers pass arguments on, so `"Start VECTOR.bat" --lan` or
`"./Start VECTOR.command" --lan` from a terminal does the same.

Then browse from the other device to `http://<host-ip>:8080`. Find the
host's address with `ipconfig` on Windows or `ipconfig getifaddr en0`
on macOS.

Any device that reaches the port gets the login page, so several agents
can work the same case from tablets or laptops at once. The database is
in WAL mode, so simultaneous entries do not collide, and open pages
refresh on their own within a couple of seconds when another device
saves. A page waits while you have a dialog open, so an edit in progress
is never swept away.

> **Before you use `--lan`, understand what it means.**
>
> - **Traffic is unencrypted HTTP.** Passwords, suspect names,
>   addresses and dates of birth cross the network in the clear.
>   Anyone who can capture packets on that network can read them. Use
>   it only on a network you control, and prefer a dedicated hotspot
>   over a venue's Wi-Fi.
> - **Your firewall will ask.** Windows shows a Defender prompt the
>   first time — allow Python on **private** networks only. macOS
>   prompts to allow incoming connections.
> - **Shut it down when you are finished**, and do not leave `--lan`
>   in a shortcut you use by default.

### Settings

All optional, read from the environment:

| Variable                | Default     | Effect                                   |
|-------------------------|-------------|------------------------------------------|
| `VECTOR_HOST`           | `127.0.0.1` | Interface to bind. `--lan` sets `0.0.0.0` |
| `VECTOR_PORT`           | `8080`      | Port to listen on                        |
| `VECTOR_MAX_UPLOAD_MB`  | `512`       | Largest accepted attachment              |
| `VECTOR_MAX_IMPORT_MB`  | `2048`      | Largest export accepted back by Import   |
| `VECTOR_NO_BROWSER`     | unset       | Set to `1` to not open a browser on start |
| `VECTOR_DB_DIR`         | `db/`       | Where the databases live                 |
| `VECTOR_DB_KEY`         | unset       | Passphrase for an encrypted database     |
| `VECTOR_DB_KEY_FILE`    | unset       | File holding the passphrase              |
| `VECTOR_NO_PROMPT`      | unset       | Set to `1` to never prompt for it        |
| `VECTOR_REQUIRE_ENCRYPTION` | unset   | Set to `1` to refuse a plaintext database |

---

## Using it

Work top to bottom; each step feeds the next.

1. **Case** — press **Start New Case** on the home page, then enter the
   number, address, jurisdiction and start time (`MM-DD-YYYY HH:MM`).
   If a case is already open, VECTOR warns before clearing it
2. **Agents** — everyone on site. Saved to a roster that
   auto-populates at the next scene
3. **Rooms** — letter the premises A, B, C…, assign two agents to each
4. **Evidence** — item numbers are assigned automatically. Room and
   agent fields are drawn from steps 2 and 3
5. **People** — suspects and others present
6. **Notes** — timestamped narrative entries
7. **Files** — photographs and documents, stored in the case database
8. **Reports** — seven printable layouts, including the basic
   inventory used as the return copy

The open case's number is shown in the top bar on every page. Until a
case is open, the other pages refuse new entries and say why.

A one-page version of this, with export and Delete All Data, is under
**Help → Help** in the top bar.

### Getting a case out

**Export** offers two formats — or **Both** at once — downloaded through
your browser and optionally sealed with an AES-256 password. The file
arrives on whichever device you exported from, a tablet on `--lan`
included, and lands wherever that browser saves downloads:

| Format | What it is | Use it for |
|--------|-----------|------------|
| **CSV** | A ZIP with one CSV per table, attachments as files, plus a SHA-256 manifest | Opening in Excel, or reading the case without VECTOR |
| **JSON** | One self-contained file, attachments embedded as base64 | Handing the case to another tool or system |

Both carry the audit trail, and both record the SHA-256 taken when each
attachment was collected — so a file that has changed since is flagged
on the way out, and again on the way back in.

**Import** takes either format: choose the file, and VECTOR works out
which format it is from the file itself. It replaces everything currently
loaded. The one thing it will not replace is this machine's audit
trail: the import is appended to it instead, so the receiving machine
keeps its own history of what happened here.

An import is all or nothing. If any part of the file cannot be read,
nothing is imported, the case is left exactly as it was, and the message
says which table the problem was in.

---

## Accounts and sessions

**Creating an account.** An admin enters a username in the Admin Panel
and gets a one-time password back, shown once. The new account must
change it at first sign-in and is never an admin.

**Resetting one.** The reset button issues a fresh one-time password,
ends every session that account has open, and clears any sign-in lock.
A reset that left the old session working would not be a reset.

**Failed sign-ins.** After three failures VECTOR starts pausing before
each attempt, and after ten it locks the account for fifteen minutes.
Failures older than thirty minutes are forgotten, so attempts spread
across a shift never accumulate into a lock. Every attempt — successful
or not — is in the audit trail.

The numbers are deliberately forgiving. An agent mistyping a password
at 3am on a scene must not be shut out of evidence logging.

A locked account shows **LOCKED** in the Admin Panel's Sign-in column,
and an admin clears it with the padlock button without changing the
password.

**Signing everyone out.** Admin Panel → Sessions → *Sign Everyone Out*
ends every session on every device at once. Use it when a device goes
missing, or when someone leaves the team. Deleting or resetting a single
account signs out only that account.

Session state is persisted, so an invalidation survives a restart of the
server.

---

## The audit trail

Every change to case data is recorded — creations, edits, deletions,
bulk wipes, imports, and both successful and failed logins. Admins read
it at **Welcome → Audit Trail**.

Each entry records when (UTC), who, what action, which record, and the
field-level before and after. Deletions keep the complete row, so a
mis-click is recoverable from the trail even though the record is gone.

Three properties worth knowing:

- **It is append-only.** Nothing in the application can edit or remove
  an entry, including an administrator.
- **It survives "Delete All Data".** A wipe is exactly the event the
  trail exists to record, so it is never cleared.
- **It travels with the case.** Exports include `AUDIT.csv`. An import
  does *not* overwrite the local trail — it appends a record of the
  import instead, so the receiving machine's own history stays intact.

The trail is captured at the database layer rather than in each page,
so a new screen cannot accidentally skip it.

---

## How data is protected

Be clear about this before deciding where VECTOR runs.

| Data | At rest | Notes |
|------|---------|-------|
| Case data — suspects, evidence, notes | **Plaintext by default** | Encryptable — see below. Otherwise anyone who opens `db/app_data.db` reads all of it |
| Attachments — photographs, documents | **Plaintext by default** | Same file, same choice |
| Login passwords | **Hashed** | bcrypt; not recoverable, not reversible |
| Exported archive | **Encrypted, if you ask** | AES-256, only when you tick the box and set a password |
| Network traffic | **Unencrypted** | Plain HTTP, including with `--lan` |

By default the case database is ordinary SQLite: no password, not
obfuscated. A suspect's name, address and date of birth are readable in
a text editor, and a photograph can be carved straight out of the file.

**You can encrypt it.** See the next section. Once encrypted, the table
above changes: case data and attachments become unreadable without the
passphrase.

**Either way:**

- Always tick **Encrypt with password** when exporting. An export
  downloads to the browser's usual downloads folder — move it somewhere
  your unit controls.
- Delete `db/*.bak-*` and `db/*-backup-*` files once a case is verified;
  they are copies of the case.
- Treat the whole `db/` directory as evidence, and wipe the machine's
  disk to policy when the case closes.
- Full-disk encryption — BitLocker, FileVault — is still worth having.
  Database encryption protects the database; it does not protect the
  exports, the temporary files, or anything else on the machine.

---

## Encrypting the case database

Optional, and off until you turn it on. An existing install keeps
working untouched.

```
.venv/bin/pip install -r requirements-encryption.txt
```

```
.venv/bin/python tools/encrypt_database.py
```

> ### There is no recovery
>
> No reset, no backdoor, no key escrow. **If the passphrase is lost, the
> case is lost** — not delayed, lost. Record it somewhere your unit
> already trusts with credentials *before* you encrypt anything.

The tool takes the passphrase twice, backs up each database to a
timestamped `.plaintext-backup`, writes an encrypted copy, verifies it
opens with the same row counts, and only then replaces the original. If
anything fails, nothing is replaced.

Start VECTOR, confirm the case looks right, then delete the
`.plaintext-backup` files — they are unencrypted copies.

### Supplying the passphrase

VECTOR needs it at every start, and takes the first of these it finds:

| Source | Use when |
|--------|----------|
| `VECTOR_DB_KEY` | Convenient, but the passphrase ends up in whatever script or shortcut sets it |
| `VECTOR_DB_KEY_FILE` | A file holding it — ideally on removable media that travels separately from the laptop |
| A prompt at startup | Nothing is stored, but it needs someone at a console when VECTOR starts |

Set `VECTOR_NO_PROMPT=1` for a launcher with no console — a desktop
shortcut or scheduled task. Without it, `getpass` on Windows reads the
console directly and would hang with nothing on screen to explain why.

Set `VECTOR_REQUIRE_ENCRYPTION=1` to refuse to start on a plaintext
database, so a machine cannot quietly run unencrypted after a restore.

### What it does and does not protect

**Protects:** a laptop lost, stolen or handed in for repair, and a
backup copied somewhere it should not have gone. The file is unreadable
without the passphrase.

**Does not protect:** anything while VECTOR is running and unlocked. The
passphrase is in memory, reports render in the browser, and exports are
written in the clear unless you encrypt those too. It is not a
substitute for full-disk encryption, and it does nothing about a machine
someone is sitting in front of.

### Going back

```
.venv/bin/python tools/decrypt_database.py
```

Converts back to plaintext, keeping the encrypted original as a backup.
Worth knowing it exists: a case that can only be opened by one build of
one tool is a liability. Use it to hand a case to an examiner without
the driver, or to step back if encryption does not suit how the unit
works.

---

## Known limitations

Read these before relying on VECTOR for a case that will be charged.

- **One case at a time.** The database holds a single case. **Start New
  Case** on the home page deletes the current one after a warning —
  export first. While a case is open, the Cases page will not open a
  second one.
- **No soft delete.** A deleted record is gone from its table; it is
  recoverable from the audit trail, but by hand.
- **Case start and end times are typed by the agent** as
  `MM-DD-YYYY HH:MM`, with no time zone recorded. Everything the
  application generates itself is UTC and marked.
- **Network traffic is plain HTTP.** See
  [Access from another device](#access-from-another-device).

---

## Troubleshooting

**The launcher says "Python 3.10 or newer is needed"** — install Python
from [python.org](https://www.python.org/downloads/). On Windows, tick
**"Add python.exe to PATH"** on the installer's first screen. Then
double-click the launcher again.

**Windows shows a security warning before `Start VECTOR.bat` runs** —
this happens when the project came as a downloaded ZIP rather than a
`git clone`. Choose **Run**, or **More info** then **Run anyway**.

**macOS will not open `Start VECTOR.command`** — right-click it and
choose **Open**; on recent macOS versions, allow it under **System
Settings → Privacy & Security** instead. If Terminal says permission is
denied, run `chmod +x "Start VECTOR.command"` in the project folder once.

**Setup stopped part-way** — usually a dropped connection. Double-click
the launcher again; it installs whatever is still missing.

**A message says something could not be saved, imported or exported** —
it gives the reason in plain words. The full technical detail is printed
in the VECTOR window, for whoever looks after the installation.

**"No module named nicegui"** — the virtual environment is not being
used. Run the full `.venv/bin/python` or `.venv\Scripts\python` path
rather than a bare `python`.

**Port 8080 already in use** — something else has the port. Start on
another: `VECTOR_PORT=8099 .venv/bin/python main.py`.

**Another device cannot connect** — check you started with `--lan`,
that both devices are on the same network, and that the host firewall
is allowing Python.

**A page refuses to save with "No active case!"** — open a case first
with **Start New Case** on the home page.

**"Open New Case" is greyed out** — a case is already open, and VECTOR
holds one at a time. Export it if you need it, then use **Start New
Case** on the home page to clear it and begin another.

**A password change did not stick** — if `db/users.json` exists it
seeds that account at startup only; it no longer overwrites a changed
password. Delete `db/users.json` once every account is set up.

**Everyone needs to be signed out** — use *Sign Everyone Out* in the
Admin Panel. If no admin can sign in, delete `.secret` and restart,
which regenerates the session key and invalidates every session.

**Never delete `db/*.db-wal` or `db/*.db-shm`.** SQLite runs in
write-ahead-logging mode, so recent changes may live in the `-wal` file
until they are checkpointed. If the application was closed uncleanly,
deleting it discards those changes silently. SQLite recovers from the
`-wal` on its own the next time the database is opened — leave both
files alone.

---

## Tests

```
.venv/bin/pip install -r requirements-dev.txt
```

```
.venv/bin/python -m pytest
```

275 tests, about twelve seconds. They run against a temporary database
and never touch `db/`. The encryption tests skip themselves when the
SQLCipher driver is not installed.

The suite exists because of a specific failure: a variable rename
reached the models and the CRUD pages but not the report or export
code, and every report returned HTTP 500 for an unknown period with
nothing to catch it. Coverage is aimed at that class of bug — each
report is rendered and asserted to contain the case number, and the
export is round-tripped and compared row for row and byte for byte.

| File | Tests | Covers |
|------|------:|--------|
| `test_page_specs.py` | 53 | Every page field names a real column; required columns are reachable; validators accept what the builder passes; the Cases page holds one case and has no delete button; notes list in the order written |
| `test_reports.py` | 25 | All seven reports render, carry the case header, and escape their values |
| `test_crypto.py` | 22 | Encryption is detected without a passphrase; awkward passphrases round-trip; case data is unreadable in the raw file |
| `test_json_export.py` | 22 | JSON round trip, embedded attachments, attachments sharing a name, format detection, tampering detected; older and upstream layouts import |
| `test_auth.py` | 20 | One-time passwords are unique; throttling escalates and locks; session invalidation is per-account |
| `test_failures_and_live.py` | 20 | Failures are explained without the SQL; a failed import leaves the case unchanged, and an import clears attachments the new case lacks; exports stop rather than leave attachments out; edit dialogs open for values no longer on a list; saves, wipes and imports move the change signal, while reads and sign-ins do not |
| `test_numbering.py` | 17 | Evidence numbering past item 9; room labels past Z |
| `test_validators.py` | 16 | Every validator reports rather than crashing, and the domain rules hold, including one case at a time |
| `test_export_import.py` | 15 | CSV round trip preserves rows, bytes and provenance, including attachments sharing a name; encrypted archives; tampering detected; older and upstream archives import; download staging is cleared |
| `test_active_case.py` | 13 | Pages refuse to record without an open case; the Cases page still works; async handlers stay async |
| `test_dates.py` | 12 | Old-format case times, birth dates and note times are rewritten once and audited; nothing else is touched |
| `test_logo_and_help.py` | 12 | A missing logo is left out rather than shown broken; every button the Help page names exists |
| `test_migration.py` | 11 | Old-schema databases — old names, old constraints — upgrade without losing a row; backups include the write-ahead log |
| `test_audit.py` | 9 | Creates, edits, deletions, bulk wipes; blobs stay out of the log |
| `test_constraints.py` | 8 | The constraints that were removed, and the four that must stay |

---

## Demo data

A checkout ships with no case and no accounts; both are created on first
run. To load a worked example instead — a fictional twelve-item search
with agents, rooms, people and notes:

```
.venv/bin/python tools/make_demo_case.py
```

Add `--users` to reset the accounts at the same time and print fresh
one-time passwords.

Everything it loads is invented: placeholder names, `example.invalid`
addresses, and telephone numbers in the 555-01xx range reserved for
fiction. It replaces the case entirely, so do not run it against real
case data.

---

## How the code is laid out

```
Start VECTOR.bat     double-click launcher for Windows
Start VECTOR.command double-click launcher for macOS
main.py              startup, route table, first-run bootstrap
auth.py              session state, sign-in throttling, route guards
models.py            tables, the audit listener, schema upgrades
crypto.py            SQLCipher detection and key handling
failures.py          plain-language reasons for failures, and the log
live.py              refreshes open pages when another device saves
utils.py             validators, the active-case guard, shared helpers
import_export.py     CSV and JSON export and import
navbar.py            top navigation and the case badge
home_page.py         login, main menu, data management
parts/crud.py        the table-driven builder every entity page uses
parts/*_page.py      one file per screen
program/config.py    paths, network and upload settings
program/inc/         Virginia jurisdictions, agencies, agent roles
tools/               demo case, database encryption and decryption
tests/               the test suite
```

### Adding a field to an entity

Entity pages are declarations, not code. To add a column, add it to the
model in `models.py` and add one `Field` to that page's `SPEC` — the
form input, the table column, the edit dialog and the delete
confirmation all follow from it.

```python
Field("EVIDCONDITION", "Condition", kind="select",
      options=lambda: ["", "Sealed", "Damaged"])
```

`tests/test_page_specs.py` then checks the field names a real column, so
a typo fails a test rather than a search warrant.

### Adding a page

Write the builder, then add one line to `PAGES` in `main.py`:

```python
("/exhibits", build_exhibits_page, False),   # True = admin only
```

The guard comes from that table. Writing it by hand per route is how
`/admin` ended up reachable by any signed-in user and `/shutdown` by
anyone at all.

---

## Development

```
.venv/bin/python main.py --dev
```

Reloads on save. Note that a reload re-runs startup each time.

---

## Credits

VECTOR was created by **SSA M. Sponheimer**, Virginia State Police
NOVA/DC ICAC. The scene workflow — the lettered rooms, the separate
witness, the return copy as its own report — comes from that original
design.

The changes in this fork are by
[Hitman90210](https://github.com/Hitman90210).

No license file has been published for the project. Ask the original
author before reusing the code elsewhere.
