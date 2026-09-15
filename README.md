# V·E·C·T·O·R

**Virginia Evidence Collection, Tracking, Organization & Reporting**

A local web application for documenting the execution of a search
warrant: who was on site, how the premises were divided, what was
seized from where, who found it and who witnessed it. It prints the
scene paperwork and exports the case as an encrypted archive.

VECTOR runs on your own machine. Nothing is sent anywhere.

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

The header logo and favicon are not distributed with the source. See
[`static/README.md`](static/README.md) for the two filenames. VECTOR
runs without them — the images just render as broken.

---

## Run

**macOS / Linux**

```
.venv/bin/python main.py
```

**Windows**

```
.venv\Scripts\python main.py
```

Your browser opens at <http://localhost:8080>.

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

Then browse from the other device to `http://<host-ip>:8080`. Find the
host's address with `ipconfig` on Windows or `ipconfig getifaddr en0`
on macOS.

Any device that reaches the port gets the login page, so several agents
can work the same case from tablets or laptops at once. The database is
in WAL mode, so simultaneous entries do not collide.

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
> - **Pages do not live-update.** An entry made on one device appears
>   on another when that page is reloaded, not automatically.
> - **Shut it down when you are finished**, and do not leave `--lan`
>   in a shortcut you use by default.

### Settings

All optional, read from the environment:

| Variable                | Default     | Effect                                   |
|-------------------------|-------------|------------------------------------------|
| `VECTOR_HOST`           | `127.0.0.1` | Interface to bind. `--lan` sets `0.0.0.0` |
| `VECTOR_PORT`           | `8080`      | Port to listen on                        |
| `VECTOR_MAX_UPLOAD_MB`  | `512`       | Largest accepted attachment              |
| `VECTOR_NO_BROWSER`     | unset       | Set to `1` to not open a browser on start |
| `VECTOR_DB_DIR`         | `db/`       | Where the databases live                 |
| `VECTOR_DB_KEY`         | unset       | Passphrase for an encrypted database     |
| `VECTOR_DB_KEY_FILE`    | unset       | File holding the passphrase              |
| `VECTOR_NO_PROMPT`      | unset       | Set to `1` to never prompt for it        |
| `VECTOR_REQUIRE_ENCRYPTION` | unset   | Set to `1` to refuse a plaintext database |

---

## Using it

Work top to bottom; each step feeds the next.

1. **Case** — number, address, jurisdiction, start time
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

### Getting a case out

**Export** offers two formats — or **Both** at once — saved to your
Desktop and optionally sealed with an AES-256 password:

| Format | What it is | Use it for |
|--------|-----------|------------|
| **CSV** | A ZIP with one CSV per table, attachments as files, plus a SHA-256 manifest | Opening in Excel, or reading the case without VECTOR |
| **JSON** | One self-contained file, attachments embedded as base64 | Handing the case to another tool or system |

Both carry the audit trail, and both record the SHA-256 taken when each
attachment was collected — so a file that has changed since is flagged
on the way out, and again on the way back in.

**Import** takes either format; it works out which from the file
itself, so you do not have to say. It replaces everything currently
loaded. The one thing it will not replace is this machine's audit
trail: the import is appended to it instead, so the receiving machine
keeps its own history of what happened here.

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

- Always tick **Encrypt with password** when exporting.
- Delete `db/*.bak-*` and `db/*-backup-*` files once a case is verified;
  they are unencrypted copies.
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
  export first. Nothing yet stops a second case being opened from the
  Cases page, and reports read only the first, so use Start New Case.
- **No soft delete.** A deleted record is gone from its table; it is
  recoverable from the audit trail, but by hand.
- **Case start and end times are typed by the agent** as
  `MM-DD-YYYY HH:MM`, with no time zone recorded. Everything the application generates itself is
  UTC and marked.
- **No live refresh.** With several devices connected, a page shows
  another agent's entry only after a reload.

---

## Troubleshooting

**"No module named nicegui"** — the virtual environment is not being
used. Run the full `.venv/bin/python` or `.venv\Scripts\python` path
rather than a bare `python`.

**Port 8080 already in use** — something else has the port. Start on
another: `VECTOR_PORT=8099 .venv/bin/python main.py`.

**Another device cannot connect** — check you started with `--lan`,
that both devices are on the same network, and that the host firewall
is allowing Python.

**A password change did not stick** — if `db/users.json` exists it
seeds that account at startup only; it no longer overwrites a changed
password. Delete `db/users.json` once every account is set up.

**Everyone needs to be signed out** — delete `.secret` and restart.
That regenerates the session key and invalidates every active session.

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

200 tests, about six seconds. They run against a temporary database and
never touch `db/`. The encryption tests skip themselves when the
SQLCipher driver is not installed.

The suite exists because of a specific failure: a variable rename
reached the models and the CRUD pages but not the report or export
code, and every report returned HTTP 500 for an unknown period with
nothing to catch it. Coverage is aimed at that class of bug — each
report is rendered and asserted to contain the case number, and the
export is round-tripped and compared row for row and byte for byte.

| File | Covers |
|------|--------|
| `test_reports.py` | All seven reports render, carry the case header, and escape their values |
| `test_export_import.py` | CSV round trip preserves rows, bytes and provenance; encrypted archives; tampering is detected |
| `test_json_export.py` | JSON round trip, embedded attachments, format detection, tampering is detected |
| `test_audit.py` | Creates, edits, deletions, bulk wipes; blobs stay out of the log |
| `test_validators.py` | Every validator reports rather than crashing, and the domain rules hold |
| `test_numbering.py` | Evidence numbering past item 9; room labels past Z |
| `test_constraints.py` | The constraints that were removed, and the four that must stay |
| `test_migration.py` | An old-schema database migrates without losing a row |
| `test_page_specs.py` | Every page field names a real column; required columns are reachable; validators accept what the builder passes |
| `test_auth.py` | One-time passwords are unique; throttling escalates and locks; session invalidation is per-account |
| `test_crypto.py` | Encryption is detected without a passphrase; awkward passphrases round-trip; case data is unreadable in the raw file |

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
main.py              startup, route table, first-run bootstrap
auth.py              session state and the require_login / require_admin guards
models.py            tables, the audit listener, schema migrations
utils.py             validators and shared helpers
import_export.py     the encrypted archive
navbar.py            top navigation
home_page.py         login, main menu, data management
parts/crud.py        the table-driven builder every entity page uses
parts/*_page.py      one file per screen
program/config.py    paths, network and upload settings
program/inc/         Virginia jurisdictions, agencies, agent roles
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
