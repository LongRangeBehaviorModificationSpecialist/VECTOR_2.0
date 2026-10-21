# VECTOR Reference File

Everything about installing, running and looking after VECTOR, in detail. Most people need less than this:

- [README.md](../README.md) — what VECTOR is, and the short version of everything here.

- [/00 START HERE/](<../00%20START%20HERE/>) — installing the application, step by step, with pictures.

- The **Help** page inside VECTOR — using it at a scene.

`Python 3.10+` · `NiceGUI 3.16` · `SQLite` · `Windows · macOS · Linux` · `652 tests`

---

## 1.0 Contents

- [2.0 What It Does](#20-what-it-does)
- [3.0 What Has Been Added](#30-what-has-been-added)
- [4.0 Quick Start](#40-quick-start)
- [5.0 Requirements](#50-requirements)
- [6.0 Install](#60-install)
    - [6.1 Unit Branding](#61-unit-branding)
- [7.0 Running The Application](#70-running-the-application)
    - [7.1 First Run](#71-first-run)
    - [7.2 Upgrading An Existing Database](#72-upgrading-an-existing-database)
- [8.0 Access From Another Device](#80-access-from-another-device)
    - [8.1 Settings](#81-settings)
- [9.0 Using The Application](#90-using-the-application)
    - [9.1 Importing And Exporting Case Data](#91-importing-and-exporting-case-data)
- [10.0 Accounts & Sessions](#100-accounts--sessions)
- [11.0 The Audit Trail](#110-the-audit-trail)
- [12.0 How Data Is Protected](#120-how-data-is-protected)
- [13.0 Encrypting The Case Database](#130-encrypting-the-case-database)
    - [13.1 There Is No Recovery](#131-there-is-no-recovery)
    - [13.2 Supplying The Passphrase](#132-supplying-the-passphrase)
    - [13.3 What It Does And Does Not Protect](#133-what-it-does-and-does-not-protect)
    - [13.4 Going Back](#134-going-back)
- [14.0 Known Limitations](#140-known-limitations)
- [15.0 Troubleshooting](#150-troubleshooting)
- [16.0 Tests](#160-tests)
- [17.0 Demo Data](#170-demo-data)
- [18.0 How The Code Is Laid Out](#180-how-the-code-is-laid-out)
    - [18.1 Adding A Field To An Entity](#181-adding-a-field-to-an-entity)
    - [18.2 Adding A Page](#182-adding-a-page)
- [19.0 Development](#190-development)
- [20.0 Credits](#200-credits)

---

## 2.0 What It Does

***On scene***

- **Case** — number, address, jurisdiction, and when the search began and ended.
- **Agents** — everyone on site, kept in a roster that pre-fills the next warrant.
- **Rooms** — the premises lettered A, B, C… and on to AA, AB, with two agents assigned to each.
- **Evidence** — numbered automatically, with where it was found, who found it, and a witness who must be someone else.
- **People** — suspects and others present, with phone numbers typed any way.
- **Notes** — timestamped narrative, attributed to whoever is signed in.
- **Files** — photographs and documents, hashed the moment they arrive.

***Afterwards***

- **Eight printable reports**, including the basic inventory left as the return copy and a list of every attached file with its SHA-256, and **Print All**, which prints the ones a search ends with in one go.
- **Export** as a ZIP of CSVs, a single JSON file, or both — optionally AES-256 encrypted.
- **Import** either format back, with every attachment checked against the hash taken when it was collected.

***Throughout***

- **An append-only audit trail** of every change, sign-in and wipe.
- **Accounts** with one-time passwords, sign-in throttling and sessions an admin can end.
- **Several devices at once** over a local network, when you choose to allow it.
- **Optional encryption** of the case database itself

---

## 3.0 What Has Been Added

Everything the first version did, plus:

| Area                         | Change                                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Access control**     | The admin panel and shutdown require an admin account. Network access is off by default; `--lan` opts in; a device nobody is using signs itself out                                                                                                                                                                                                                  |
| **Passwords**          | A one-time password per account instead of a shared default; throttling and lockout on failed sign-ins; sessions an admin can end                                                                                                                                                                                                                                      |
| **Audit trail**        | Every create, edit, delete, wipe, import and sign-in, with field-level before and after; each entry fingerprinted onto the one before it, so a later edit or deletion shows up                                                                                                                                                                                         |
| **Evidence integrity** | A SHA-256 taken when each file is uploaded, verified again at export and at import                                                                                                                                                                                                                                                                                     |
| **Encryption**         | Optional SQLCipher encryption of both databases, with tools to convert either way                                                                                                                                                                                                                                                                                      |
| **Reliability**        | Reports and export working; evidence numbering past item 9; room letters past Z; uploads over 1 MB; no more "database is locked"; imports that are all or nothing; failures explained in plain words, and kept on screen until acknowledged; reports in item-number order; dates checked before they are saved; evidence numbers that close up when an item is removed |
| **Times**              | Stamped in the machine's own time zone, with the offset from UTC; case times fill in from the clock, and Reports asks about a missing end time                                                                                                                                                                                                                         |
| **Several devices**    | Open pages refresh on their own when another device saves, and the case badge follows; on a phone or a small tablet the page buttons fold into one menu                                                                                                                                                                                                                |
| **Data handling**      | Case databases, and each machine's settings, kept out of version control; a fictional demo case for evaluation; automatic schema upgrades with backups; attachments downloaded straight from the database, with no copy left on disk                                                                                                                                   |
| **Maintainability**    | Six hand-written entity pages replaced by declarations and one table-driven builder; one route table with one guard                                                                                                                                                                                                                                                    |
| **Touch screens**      | Raised buttons drawn cleanly on an iPad, with no hover border left behind by a tap; the print window's Print and Close buttons sized for a finger, in a bar that names the report and stays readable on a laptop in dark mode                                                                                                                                          |
| **Install**            | A double-click launcher that sets itself up, pinned dependencies, step-by-step Windows and macOS instructions, and a start that works from any folder                                                                                                                                                                                                                  |
| **Tests**              | 652 tests covering reports, export round trips, the audit trail, migrations, sign-in and encryption                                                                                                                                                                                                                                                                    |

It also carries the original project's most recent work — JSON export, the active-case badge and guard, the capitalised column names, the refreshed interface, (28-Sep-2026) the larger buttons with hover borders, the Files report, `Page X of Y` on printed reports, exports recorded in the audit trail and a hash for every table in the CSV manifest, and (13 and 14-Oct-2026) uploads typed by their content rather than their name, downloads recorded in the audit trail and sent with safety headers, a switch that hides agents' phone numbers and emails on the Agent List, a Room List that waits for both agents in every room, and a Cases page that shows the open case instead of a second form — with fixes made while bringing it across.

Every change, with the reasoning behind it, is listed in pull requests [#2](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0/pull/2) and [#3](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0/pull/3) to the original project.

The fixes made after the second merge are explained step by step, with the commands to find and make each one, in [fixing-after-a-merge.md](fixing-after-a-merge.md), and at more length, with screenshots, in [VECTOR-fixing-after-a-merge.pdf](VECTOR-fixing-after-a-merge.pdf).

---

## 4.0 Quick Start

With [Python 3.10 or newer](#requirements) installed, double-click the launcher in the project folder:

- **Windows** — `Start VECTOR.bat`
- **macOS** — `Start VECTOR.command`, which runs `Start VECTOR.sh`

The first start sets up a `.venv` folder and installs what VECTOR needs, which takes a few minutes and an internet connection; after that it starts straight away. The same by hand:

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

Your browser opens at [http://localhost:8080](http://localhost:8080), and the console prints a one-time administrator password — see [7.1 First Run](#71-first-run). To look around with a worked example first, load the [17.0 Demo Data](#170-demo-data).

The sections below cover each step in full.

---

## 5.0 Requirements

- **Python 3.10 or newer**
- About 200 MB of disk for the virtual environment

Check what you have:

```
python --version
```

If that reports Python 2, or "command not found", use `python3` in place of `python` throughout.

**Windows** — install from [python.org](https://www.python.org/downloads/windows/). Tick **"Add python.exe to PATH"** on the first screen of the installer.

**macOS** — the bundled `python3` is a stub. Install a real one from [python.org](https://www.python.org/downloads/macos/) or with Homebrew:

```
brew install python
```

---

## 6.0 Install

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

No compiler is needed. Every dependency ships as a prebuilt wheel for Windows, Intel Mac and Apple Silicon.

---

### 6.1 Unit Branding

The logos and the browser tab icon are not distributed with the source. See [`static/README.md`](../static/README.md) for the filenames. VECTOR runs without them — each page shows just its title.

---

## 7.0 Running The Application

Double-click `Start VECTOR.bat` (on Windows) or `Start VECTOR.command` (on macOS). It sets up Python virtual environment (`.venv`) if it is missing, installs again if `requirements.txt` has changed since the last start — after an update, say — and then starts VECTOR. That install needs an internet connection; the 13-Oct-2026 update added one package, `filetype`, which reads what an uploaded file really is. From a terminal instead:

**macOS / Linux**

```
.venv/bin/python main.py
```

**Windows**

```
.venv\Scripts\python main.py
```

Your browser opens at [http://localhost:8080](http://localhost:8080).

VECTOR runs only while that window is open. Closing it, or pressing `Ctrl + C`, stops the application; nothing is left running in the background.

The first start also asks once whether to put a VECTOR shortcut on the desktop, with VECTOR's icon (no answer in 30 seconds counts as yes). `tools/make_shortcut.py` makes it the way each system does: a `.lnk` through Windows' own shortcut maker, a small `VECTOR.app` on a Mac that opens the launcher in Terminal, and a `.desktop` entry on Linux. A shortcut holds the folder it was made in, which is why one is not shipped; run the script again after moving the folder. The icons are in `static/icons/`.

---

### 7.1 First Run

VECTOR creates its databases and prints a one-time administrator password:

```
  ==============================================================
  FIRST RUN - an administrator account has been created.
  ==============================================================
    Username:  admin
    Password:  64xhZN0pDYhwPG73
```

The same credentials are written to `db/FIRST_RUN_PASSWORD.txt` in case the console scrolls. You will be asked to change the password immediately; delete that file once you have.

Every password VECTOR issues — at first run, when an admin creates an account, and when an admin resets one — is generated for that account and shown **once**. There is no shared default. Write it down before closing the message; it cannot be recovered, only reset again.

---

### 7.2 Upgrading An Existing Database

If you already have databases from an earlier version, the first start after upgrading brings them up to date. Each database is copied to a timestamped `.bak` beside it before anything changes, and every step runs once:

- **Names.** PERSONS, FILES and users take the upstream project's capitalised column names — `SUSPECTNAME` => `PERSONNAME`, `file_name` => `FILENAME`, `user_name` => `USERNAME`, and so on, and since 28-Sep-2026 `SUSPECTNOTE` => `PERSONNOTE` and `FILEHASHEDAT` => `FILEHASHEDDATETIME`. Columns are renamed in place, so no row is copied and every password keeps working. A database opened by a version that added `FILEHASHEDDATETIME` empty beside the old column has its hashing times copied across.

- **Constraints.** A table still carrying a unique constraint that blocked ordinary scenes — a second agent with no email address, a house with two bedrooms, the same photograph attached twice — is rebuilt without it.

- **Dates.** Case times and dates of birth stored as `YYYY-MM-DD` are rewritten as `MM-DD-YYYY`, the format the input masks now use. Each change is recorded in the audit trail.

- **Times.** Note and entry times that earlier versions stamped in UTC are rewritten in this machine's time zone, with the offset. Each change is recorded in the audit trail.

- **Audit fingerprints.** The trail gains a `chain` column, and entries written before it existed are fingerprinted once, in order. They are chained retrospectively, so the chain says nothing about what happened to them before the upgrade — only that nothing has changed since. This happens before the date and time rewrites above, which write audit entries of their own and have to be chained onto the old ones. (A database upgraded on 24-Sep-2026 had them the other way round, and its trail fails the check at the first rewritten entry. That is a record of the order, not of tampering; a new database is unaffected.)

A database from before the renames prints:

```
Schema migration: backed up app_data.db to app_data.db.bak-20260915-000534
Schema migration: PERSONS -> PERSONS, 4 column(s) renamed
Schema migration: files -> FILES, 9 column(s) renamed
Schema migration: backed up users.db to users.db.bak-20260915-000534
Schema migration: users -> users, 7 column(s) renamed
Schema migration: added FILES.FILENOTE
```

The write-ahead log is folded in before the copy, so the backup holds the most recent entries too. Keep it until you have confirmed the case looks right, then delete it — it is a full copy of the case.

Exports made by earlier versions, and by the upstream project, still import: old table and column names are read as the names they became.

**This machine's settings.** `/db/settings.json` was briefly kept in version control (13 and 14-Oct-2026) and no longer is. Updating past that takes away the copy git put there, so network access, the printed date and Agent List redaction go back to off once; turn back on the ones you use. If git refuses to update because `/db/settings.json` has local changes, move the file out of `/db/`, update, and move it back.

---

## 8.0 Access From Another Device

By default VECTOR listens on **loopback only** — it is not reachable from the network, and nothing on your Wi-Fi can see it.

To open it to other devices on the same network, add `--lan`:

**macOS / Linux**

```
.venv/bin/python main.py --lan
```

**Windows**

```
.venv\Scripts\python main.py --lan
```

**The simplest way is the setting.** An administrator turns network access on in the **Admin Panel**, and from then on this machine starts that way — there is no flag to remember and no special launcher to find. It takes effect the next time VECTOR starts, because the address a server listens on is fixed when the socket opens; the page says so rather than pretending otherwise.

**`Help => Connect a Device`** then shows the exact address to type on the other device, with a QR code of it that a tablet's camera opens (drawn on this computer by the `segno` package, so no internet is needed), and says plainly when VECTOR is not on the network at all. The console window says the same when VECTOR starts:

```
  VECTOR is running.
    On this computer:  http://localhost:8080
    On a tablet:       http://192.168.1.23:8080
```

A computer has an address for every network adapter it has, and a laptop running VMware, Hyper-V, WSL, Docker or a VPN has a virtual adapter for each — networks that exist only inside that machine, which no tablet can reach. VECTOR offers the one on the network the computer is connected to; the page lists any other real adapter (a cable as well as Wi-Fi, or the laptop's own Mobile Hotspot) as a fallback, and every address, labelled with its adapter, under **Every address on this computer** for troubleshooting.

For a single run, without changing what the machine does from then on, `--lan` still works and takes precedence over the setting.

The launchers pass arguments on, so `"Start VECTOR.bat" --lan` or `"./Start VECTOR.command" --lan` from a terminal does the same.

Then browse from the other device to the address Connect a Device gives, whole — `http://` and `:8080` included.

Any device that reaches the port gets the login page, so several agents can work the same case from tablets or laptops at once. The database is in WAL mode, so simultaneous entries do not collide, and open pages refresh on their own within a couple of seconds when another device saves -- the Audit Trail page included, which follows the trail itself so a sign-in on another device shows up. A page waits while you have a dialog open, so an edit in progress is never swept away. On a phone or a small tablet the page buttons fold into one menu button at the top left, so the bar stays on a single line.

> **Before you use `--lan`, understand what it means.**
>
> - **Traffic is unencrypted HTTP.** Passwords, suspect names, addresses and dates of birth cross the network in the clear. Anyone who can capture packets on that network can read them. Use it only on a network you control, and prefer a dedicated hotspot over a venue's Wi-Fi.
>
> - **Your firewall will ask.** Windows shows a Defender prompt the first time — allow Python on **private** networks only. macOS prompts to allow incoming connections.
>
> - **Shut it down when you are finished**, and do not leave `--lan` in a shortcut you use by default.

---

### 8.1 Settings

All optional, read from the environment:

| Variable                      | Default     | Effect                                                        |
| ----------------------------- | ----------- | ------------------------------------------------------------- |
| `VECTOR_HOST`                 | `127.0.0.1` | Interface to bind. `--lan` sets `0.0.0.0`                     |
| `VECTOR_PORT`                 | `8080`      | Port to listen on                                             |
| `VECTOR_MAX_UPLOAD_MB`        | `512`       | Largest accepted attachment                                   |
| `VECTOR_MAX_IMPORT_MB`        | `2048`      | Largest export accepted back by Import                        |
| `VECTOR_NO_BROWSER`           | unset       | Set to `1` to not open a browser on start                     |
| `VECTOR_DB_DIR`               | `db/`       | Where the databases live                                      |
| `VECTOR_DB_KEY`               | unset       | Passphrase for an encrypted database                          |
| `VECTOR_DB_KEY_FILE`          | unset       | File holding the passphrase                                   |
| `VECTOR_NO_PROMPT`            | unset       | Set to `1` to never prompt for it                             |
| `VECTOR_REQUIRE_ENCRYPTION`   | unset       | Set to `1` to refuse a plaintext database                     |
| `VECTOR_SESSION_IDLE_MINUTES` | `60`        | Minutes untouched before a device signs out; `0` turns it off |

Four things are settings rather than environment variables, because they describe this machine rather than travel with a copy of the case: network access, in the Admin Panel, and on the Reports page the printed date, Agent List redaction and what Print All prints. They are kept in `db/settings.json`, which is not in version control, and every change to one is recorded in the audit trail.

---

## 9.0 Using The Application

Work top to bottom; each step feeds the next.

1. **Case.** Press **Start New Case** on the home page, then enter the number, address, jurisdiction and start time (`MM-DD-YYYY HH:MM`), or press **Fill with current date/time**. While a case is open, the Cases page shows it in place of the form; **Start New Case** warns before clearing it.

2. **Agents.** Everyone on site. Saved to a roster that auto-populates at the next scene. A phone number can be typed any way; a US one is saved as `(703) 555-1234`, with any extension kept as `x12`, and anything else as typed.

3. **Rooms.** Letter the premises A, B, C..., and assign two agents to each, now or later.

4. **Evidence.** Item numbers are assigned automatically. Room and agent fields are drawn from steps 2 and 3, and Room Located, Found By and Witnessed By stay filled in from one item to the next; **Clear** empties them. On a phone the form is one column. Delete an item that was not seized after all, and the later items move down one number, so the list never skips.

5. **People.** Suspects and others present. A phone number is typed any way, as for agents.

6. **Notes.** Timestamped narrative entries.

7. **Files.** Photographs and documents, stored in the case database. On a phone or tablet a **Take a photograph** button opens the camera straight into the case. VECTOR goes by what a file is, read from its contents, not by its name: images, videos, documents and archives are accepted, and a program renamed `photo.jpg` is refused. Every download of a file is recorded in the audit trail.

8. **Reports.** Eight printable layouts, including the basic inventory used as the return copy and the list of attached files. **Print Report** opens the report in a window of its own, under a bar naming the report and case with **Print Report** and **Close**; the bar is not printed. Two switches on the Reports page, both off unless turned on: one adds the date and time each report was printed, the other hides agents' phone numbers and emails on the Agent List. If a room is missing an agent, **Print Room List** says which, and offers **Print Report Without Names**, with the blanks printed as `[NOT RECORDED]`. If the case has no end time yet, the page offers to fill it in from this machine's clock.

   **Print All** prints the reports a search ends with in one print window, each starting on a new page: by default the Agent List, Room List, Evidence List (Full), two copies of the Inventory and Return and the Persons List. **Choose what Print All prints**, under it, sets which reports and how many copies, for this machine, and each change is audited. Its pages are not numbered.

The open case's number is shown in the top bar on every page. Until a case is open, the other pages refuse new entries and say why.

Prompts and confirmations fade after a few seconds. A message saying that something did **not** happen — a record that was not saved, an import or export that failed, an attachment that no longer matches its hash — stays until you press **OK**.

Every table has a search box above it, which narrows the rows as you type — an item number, part of a description, a room, an agent's name. It filters the rows already on screen, so the order you sorted them into is kept. The magnifying glass in the top bar searches the whole case at once, and a result opens its page with that page's search filled in.

The Home page counts what the case holds, and **Before you leave the scene** lists what is easy to miss at the end: a room with fewer than two agents, items not marked as photographed or with no answer for triage, a blank end time, and changes made since the last export.

Anything typed into an add form and not saved yet is kept, for that account on that browser, and put back the next time the form opens, marked *Filled in from before*, with **Discard**.

**Light or dark page**, in the account menu, shows every page light for a tablet in daylight, or dark again. Each browser keeps its own choice.

The **Help** page inside VECTOR (top bar) explains all of this in short topics, with a search box, for the agents using it at a scene.

---

### 9.1 Importing And Exporting Case Data

**Export** offers two formats — or **Both** at once — downloaded through your browser and optionally sealed with an AES-256 password. The file arrives on whichever device you exported from, a tablet on `--lan` included, and lands wherever that browser saves downloads:

| Format   | What it is                                                                  | Use it for                                           |
| -------- | --------------------------------------------------------------------------- | ---------------------------------------------------- |
| **CSV**  | A ZIP with one CSV per table, attachments as files, plus a SHA-256 manifest | Opening in Excel, or reading the case without VECTOR |
| **JSON** | One self-contained file, attachments embedded as base64                     | Handing the case to another tool or system           |

Both carry the audit trail, and both record the SHA-256 taken when each attachment was collected — so a file that has changed since is flagged on the way out, and again on the way back in. The CSV manifest also records a SHA-256 of each table's CSV, and every export is itself recorded in the audit trail; an export whose record cannot be written is not handed over.

Digests are shown in capitals. One recorded in lower case, as every attachment was before 28-Sep-2026, is the same digest, and is compared as one.

**Import** takes either format: choose the file, and VECTOR works out which format it is from the file itself — and whether it was exported with a password, asking for one only when it was. It replaces everything currently loaded. The one thing it will not replace is this machine's audit trail: the import is appended to it instead, so the receiving machine keeps its own history of what happened here.

An import is all or nothing. If any part of the file cannot be read, nothing is imported, the case is left exactly as it was, and the message says which table the problem was in.

---

## 10.0 Accounts & Sessions

**Creating an account.** An admin enters a username in the Admin Panel and gets a one-time password back, shown once. The new account must change it at first sign-in and is never an admin.

**A one-time password opens one page.** Until it is replaced, it opens *Change Password* and nothing else: every other page, and every attachment download, sends it back there. It used to be a full sign-in once that page was skipped — Home, or any address typed in, carried on without the change. The one-time password typed again is refused, and choosing a new one ends every other session the account has open, so a second device signed in with the same one-time password cannot set a password over it. Change Password is for that and nothing else; a signed-in user is sent away from it.

**Resetting one.** The reset button issues a fresh one-time password, ends every session that account has open, and clears any sign-in lock. A reset that left the old session working would not be a reset.

**Failed sign-ins.** After three failures VECTOR starts pausing before each attempt, and after ten it locks the account for fifteen minutes. Failures older than thirty minutes are forgotten, so attempts spread across a shift never accumulate into a lock, and a name that was never an account is dropped from the list once its failures have aged out. Every attempt — successful or not — is in the audit trail.

The pause holds up that sign-in and nothing else, and so does the password check itself, which bcrypt makes take a quarter of a second on purpose. Both used to run on the loop that serves every device, so each wrong password stopped every tablet at the scene for up to two seconds.

The numbers are deliberately forgiving. An agent mistyping a password at 3am on a scene must not be shut out of evidence logging.

A locked account shows **LOCKED** in the Admin Panel's Sign-in column, and an admin clears it with the padlock button without changing the password.

**A device left alone signs itself out.** After an hour with no typing, tapping or scrolling, VECTOR warns and then ends the session, so a tablet on a kitchen counter is not a case file anyone passing can read. Only real use counts — the pages refresh themselves every couple of seconds, and that deliberately does not keep a session alive — and every tab of the same browser counts as one device. Records already saved are kept — a sign-out changes no case data — but a form filled in and not yet saved goes with the page, which is what the warning is for. The sign-out itself is recorded in the audit trail.

Change the wait with `VECTOR_SESSION_IDLE_MINUTES`, or set it to `0` to turn it off.

**Signing everyone out.** Admin Panel => Sessions => *Sign Everyone Out* ends every session on every device at once. Use it when a device goes missing, or when someone leaves the team. Deleting or resetting a single account signs out only that account.

**A page already open notices.** Ending a session used to stop only the next page load: a page already open kept saving, deleting and uploading until somebody moved off it, under the name of an account that might no longer exist. Now each page checks every five seconds and goes to the sign-in page, which says the device was signed out. Every save, delete, upload, import and export checks as well before it acts, so nothing gets in during those five seconds either.

Session state is persisted, so an invalidation survives a restart of the server.

---

## 11.0 The Audit Trail

Every change to case data is recorded — creations, edits, deletions, bulk wipes, imports, exports, attachment downloads, setting changes, sign-outs, and both successful and failed logins — and so is every change to the accounts: one created, reset, unlocked or deleted, a password changed, Sign Everyone Out, and a shutdown. Those used to be missing, so who had reset a colleague's password was nowhere to be found. Admins read it at **Welcome => Audit Trail**, where the filter offers every kind of entry (a test checks that it does).

Each entry records when (kept in UTC, shown in this machine's time zone), who, what action, which record, and the field-level before and after. Deletions keep the complete row, so a mis-click is recoverable from the trail even though the record is gone.

Four properties worth knowing:

- **It is append-only.** Nothing in the application can edit or remove an entry, including an administrator.

- **Each entry is fingerprinted.** An entry carries a SHA-256 of itself and of the entry before it, so the entries form a chain: change one in a database browser, or take one out, and every entry after it stops matching. **Check the trail** on the Audit Trail page walks the chain and says what it found. This is evidence of tampering rather than protection from it — anyone who can write to the database could recompute the whole chain — so keep exports, which carry the trail as it stood when they were made.

- **It survives "Delete All Data".** A wipe is exactly the event the trail exists to record, so it is never cleared.

- **It travels with the case.** Exports include `AUDIT.csv`. An import does *not* overwrite the local trail — it appends a record of the import instead, so the receiving machine's own history stays intact.

The trail is captured at the database layer rather than in each page, so a new screen cannot accidentally skip it.

---

## 12.0 How Data Is Protected

Be clear about this before deciding where VECTOR runs.

| Data                                  | At rest                   | Notes                                                                                |
| ------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------ |
| Case data — suspects, evidence, notes | **Plaintext by default**  | Encryptable — see below. Otherwise anyone who opens `db/app_data.db` reads all of it |
| Attachments — photographs, documents  | **Plaintext by default**  | Same file, same choice                                                               |
| Login passwords                       | **Hashed**                | bcrypt; not recoverable, not reversible                                              |
| Exported archive                      | **Encrypted, if you ask** | AES-256, only when you tick the box and set a password                               |
| Network traffic                       | **Unencrypted**           | Plain HTTP, including with `--lan`                                                   |

By default the case database is ordinary SQLite: no password, not obfuscated. A suspect's name, address and date of birth are readable in a text editor, and a photograph can be carved straight out of the file.

**You can encrypt it.** See the next section. Once encrypted, the table above changes: case data and attachments become unreadable without the passphrase.

**Either way:**

- Always tick **Encrypt with password** when exporting. An export downloads to the browser's usual downloads folder — move it somewhere your unit controls.

- Delete `db/*.bak-*` and `db/*-backup-*` files once a case is verified; they are copies of the case.

- Treat the whole `db/` directory as evidence, and wipe the machine's disk to policy when the case closes.

- Full-disk encryption — BitLocker, FileVault — is still worth having. Database encryption protects the database; it does not protect the exports, the temporary files, or anything else on the machine.

---

## 13.0 Encrypting The Case Database

Optional, and off until you turn it on. An existing install keeps working untouched.

```
.venv/bin/pip install -r requirements-encryption.txt
```

```
.venv/bin/python tools/encrypt_database.py
```

---

### 13.1 There Is No Recovery

No reset, no backdoor, no key escrow. **If the passphrase is lost, the case is lost** — not delayed, lost. Record it somewhere your unit already trusts with credentials *before* you encrypt anything.

The tool takes the passphrase twice, backs up each database to a timestamped `.plaintext-backup`, writes an encrypted copy, verifies it opens with the same row counts, and only then replaces the original. If anything fails, nothing is replaced.

Start VECTOR, confirm the case looks right, then delete the `.plaintext-backup` files — they are unencrypted copies.

---

### 13.2 Supplying The Passphrase

VECTOR needs it at every start, and takes the first of these it finds:

| Source               | Use when                                                                               |
| -------------------- | -------------------------------------------------------------------------------------- |
| `VECTOR_DB_KEY`      | Convenient, but the passphrase ends up in whatever script or shortcut sets it          |
| `VECTOR_DB_KEY_FILE` | A file holding it — ideally on removable media that travels separately from the laptop |
| A prompt at startup  | Nothing is stored, but it needs someone at a console when VECTOR starts                |

Set `VECTOR_NO_PROMPT=1` for a launcher with no console — a desktop shortcut or scheduled task. Without it, `getpass` on Windows reads the console directly and would hang with nothing on screen to explain why.

Set `VECTOR_REQUIRE_ENCRYPTION=1` to refuse to start on a plaintext database, so a machine cannot quietly run unencrypted after a restore.

---

### 13.3 What It Does And Does Not Protect

**Protects.** A laptop lost, stolen or handed in for repair, and a backup copied somewhere it should not have gone. The file is unreadable without the passphrase.

**Does not protect.** Anything while VECTOR is running and unlocked. The passphrase is in memory, reports render in the browser, and exports are written in the clear unless you encrypt those too. It is not a substitute for full-disk encryption, and it does nothing about a machine someone is sitting in front of.

---

### 13.4 Going Back

```
.venv/bin/python tools/decrypt_database.py
```

Converts back to plaintext, keeping the encrypted original as a backup. Worth knowing it exists: a case that can only be opened by one build of one tool is a liability. Use it to hand a case to an examiner without the driver, or to step back if encryption does not suit how the unit works.

---

## 14.0 Known Limitations

Read these before relying on VECTOR for a case that will be charged.

- **One case at a time.** The database holds a single case. **Start New Case** on the home page deletes the current one after a warning — export first. While a case is open, the Cases page will not open a second one.

- **No soft delete.** A deleted record is gone from its table; it is recoverable from the audit trail, but by hand.

- **Case start and end times carry no time zone.** They are typed as `MM-DD-YYYY HH:MM`, or filled in from the clock, in this machine's local time. Everything VECTOR stamps itself carries its offset from UTC.

- **Network traffic is plain HTTP.** See [8.0 Access From Another Device](#80-access-from-another-device).

---

## 15.0 Troubleshooting

**The launcher says "Python 3.10 or newer is needed".**  Install Python from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add python.exe to PATH"** on the installer's first screen. Then double-click the launcher again.

**Windows shows a security warning before `Start VECTOR.bat` runs.**  This happens when the project came as a downloaded ZIP rather than a `git clone`. Choose **Run**, or **More info** then **Run anyway**.

**macOS opens `Start VECTOR.sh` in an editor, or not at all.**  Double-click `Start VECTOR.command` instead. Finder only opens a `.command` file in Terminal; the `.command` file runs `Start VECTOR.sh`, so both stay in step.

**macOS will not open `Start VECTOR.command`.**  Right-click it and choose **Open**; on recent macOS versions, allow it under **System Settings → Privacy & Security** instead. If Terminal says permission is denied, run `chmod +x "Start VECTOR.command"` in the project folder once.

**Setup stopped part-way.**  Usually a dropped connection. Double-click the launcher again; it installs whatever is still missing.

**A message says something could not be saved, imported or exported.**  It gives the reason in plain words. The full technical detail is printed in the VECTOR window, for whoever looks after the installation.

**"No module named nicegui"**  The virtual environment is not being used. Run the full `.venv/bin/python` or `.venv\Scripts\python` path rather than a bare `python`.

**Port 8080 already in use.**  Something else has the port. Start on another: `VECTOR_PORT=8099 .venv/bin/python main.py`.

**Another device cannot connect.**  Check you started with `--lan`, that both devices are on the same network, and that the host firewall is allowing Python.

**A page refuses to save with "No active case!"**  Open a case first with **Start New Case** on the home page.

**The Cases page says "A case is already open" instead of showing the form.**  VECTOR holds one case at a time. Export it if you need it, then use **Start New Case** on the home page to clear it and begin another.

**An upload is refused as "not an allowed file type".**  VECTOR goes by what the file is, not its name. Images, videos, PDFs, Office documents, text and archives (ZIP, 7z, RAR, tar, and gzip) are accepted. A file that is really something else — a program renamed `.jpg` — is refused on purpose. The message names the type it found.

**The Room List says rooms are missing agents.**  Enter the names on the Rooms page, or press **Print Report Without Names** to print it with the blanks marked `[NOT RECORDED]`.

**"No module named filetype".**  VECTOR was started without the packages the latest update added. Start it with the launcher, which installs them, or run `pip install -r requirements.txt` in the virtual environment.

**git refuses to update because of `db/settings.json`.**  That file was in version control for two days in October 2026. Move it out of `db/`, update, and move it back.

**A password change did not stick.**  If `db/users.json` exists it seeds that account at startup only; it no longer overwrites a changed password. Delete `db/users.json` once every account is set up.

**Everyone needs to be signed out.**  Use *Sign Everyone Out* in the Admin Panel. If no admin can sign in, delete `.secret` and restart, which regenerates the session key and invalidates every session.

**Never delete `db/*.db-wal` or `db/*.db-shm`.**  SQLite runs in write-ahead-logging mode, so recent changes may live in the `-wal` file until they are checkpointed. If the application was closed uncleanly, deleting it discards those changes silently. SQLite recovers from the `-wal` on its own the next time the database is opened — leave both files alone.

---

## 16.0 Tests

The tests and the developer tools are in a `git clone`. GitHub's **Download ZIP** leaves them out, along with the CI setup -- see `export-ignore` in `.gitattributes` -- because the download is what an agent installs from.

```
.venv/bin/pip install -r requirements-dev.txt
```

```
.venv/bin/python -m pytest
```

Every push and every pull request runs the same suite on GitHub Actions — Ubuntu on the oldest and the newest Python VECTOR supports, and Windows — from [`.github/workflows/tests.yml`](../.github/workflows/tests.yml).

That workflow also runs `ruff check`, configured in [`ruff.toml`](../ruff.toml) to look for errors rather than style: a name that does not exist, an import left behind by code that moved, a value assigned and never read. Style is left alone deliberately — this codebase has its own conventions and a linter arguing about them would be noise.

652 tests, about twenty-five seconds. They run against a temporary database, which they remove when they finish, and never touch `db/`. The encryption tests skip themselves when the SQLCipher driver is not installed.

The suite exists because of a specific failure: a variable rename reached the models and the CRUD pages but not the report or export code, and every report returned HTTP 500 for an unknown period with nothing to catch it. Coverage is aimed at that class of bug — each report is rendered and asserted to contain the case number, and the export is round-tripped and compared row for row and byte for byte.

| File | Tests | Covers |
| ---- | ----- | ------ |
| `test_modules_import.py` | 41 | Every module imports: a page builder moved into a new file cannot break the application without failing here |
| `test_page_specs.py` | 53 | Every page field names a real column; required columns are reachable; validators accept what the builder passes; the Cases page holds one case and has no delete button; notes list in the order written |
| `test_order_dates_and_files.py` | 29 | Reports and tables list items and rooms in order; renaming a room moves its evidence; impossible or half-typed dates are refused; attachment contents load only when read, and downloads keep their names |
| `test_times_and_numbers.py` | 25 | Stamps carry this machine's time zone and offset, and UTC stamps already saved are rewritten once; both case times offer the fill button, and the end-time reminder never fills in a time before the start; typed text in a dropdown is kept; removing an item moves the later numbers down, audited |
| `test_reports.py` | 37 | All eight reports render, carry the case header, and escape their values exactly once; the Files report prints upload times in local time; the printed date appears only when switched on, and the change is audited; the print window copies the report, not the page, names its report and case without letting a typed case number into its markup, and keeps a white page of its own |
| `test_crypto.py` | 22 | Encryption is detected without a passphrase; awkward passphrases round-trip; case data is unreadable in the raw file |
| `test_json_export.py` | 23 | JSON round trip, embedded attachments, attachments sharing a name, format detection, tampering detected, a lower-case collection hash not mistaken for tampering; older and upstream layouts import |
| `test_scene_usability.py` | 54 | Print All, case search, the Home checklist, drafts, light mode, the QR code, the evidence form's kept fields, the demo case |
| `test_auth.py` | 20 | One-time passwords are unique; throttling escalates and locks; session invalidation is per-account |
| `test_accounts_and_sessions.py` | 44 | A one-time password opens Change Password and nothing else, and replacing it signs the account's other devices out; a page whose session was ended cannot save, delete, upload or export, notices within seconds, and the sign-in page says why; the sign-in never pauses VECTOR's shared loop; made-up names drop off the failure list; every account change reaches the audit trail |
| `test_left_behind.py` | 11 | An import that fails — a damaged manifest or archive, or something nobody foresaw — leaves no unpacked copy of the case in the temp folder, and says what happened; the start-up clean-up recognises one left by an older VECTOR; a run of the tests removes its own database folder |
| `test_failures_and_live.py` | 24 | Failures are explained without the SQL; a failed import leaves the case unchanged, and an import clears attachments the new case lacks; exports stop rather than leave attachments out, and one the audit trail cannot record is not handed over; edit dialogs open for values no longer on a list; saves, wipes and imports move the change signal, while reads do not, and a sign-in moves the trail's signal alone |
| `test_numbering.py` | 17 | Evidence numbering past item 9; room labels past Z |
| `test_validators.py` | 20 | Every validator reports rather than crashing, and the domain rules hold, including one case at a time; an upload's type comes from its content, so a program named .pdf is refused and a RAR archive is not |
| `test_export_import.py` | 26 | CSV round trip preserves rows, bytes and provenance, including attachments sharing a name; encrypted archives; tampering detected, and a lower-case hash is the same hash; older and upstream archives import, including those with `SUSPECTNOTE` and `FILEHASHEDAT`, and one named `.ZIP`; any case number makes a file name Windows accepts; download staging is cleared |
| `test_active_case.py` | 13 | Pages refuse to record without an open case; the Cases page still works; async handlers stay async |
| `test_menu_rooms_and_passwords.py` | 13 | The page buttons and the menu share one list, and only administrators are offered Shutdown; a room without agents can be edited and survives a CSV round trip; a dropdown saved blank opens blank; an import knows when a file needs a password |
| `test_dates.py` | 12 | Old-format case times, birth dates and note times are rewritten once and audited; nothing else is touched |
| `test_logo_and_help.py` | 21 | A missing logo is left out rather than shown broken, whether it is named by file name or by its /static address; every button the Help page names exists, every topic has a title and text, and the Room List's print-anyway option replaced the old rule; the dashed hover line on buttons is for a mouse only |
| `test_session_and_search.py` | 19 | A session idle past the limit ends and one short of it warns, a timeout of zero never signs anyone out, an idle sign-out reaches the audit trail and can be filtered for, as can every other action VECTOR records; every table that grows offers a search box and the one-case page does not |
| `test_network_setting.py` | 28 | Network access is off until somebody turns it on and a damaged settings file reads as off; the flag opens it for one run and the setting from then on; the address given out is one another device could use, chosen from the adapter on the network this computer is on rather than VMware, Hyper-V, WSL or VPN adapters; and the change is recorded with who made it |
| `test_launchers.py` | 12 | Both macOS launchers are present, the double-clickable one hands over to the script, arguments pass through, and the line endings each system needs are pinned; both offer the desktop shortcut once and cannot be held up by it; the Start files in 00 START HERE hand over to them, and the guide there finds every picture; the Download ZIP leaves out the tests and the developer tools and nothing else |
| `test_shortcut.py` | 14 | The icon files hold every size each system asks for, PNG only where Windows reads it; the Mac app is a complete bundle that opens the launcher in Terminal; the Linux entry starts VECTOR in a terminal; on Windows a real .lnk points at the launcher with the icon, and a blocked one says how to make it by hand; an unrelated VECTOR.app is never deleted, and a Linux entry survives any folder name |
| `test_migration.py` | 13 | Old-schema databases — old names, old constraints — upgrade without losing a row, including the September renames of the person notes and hashing time; backups include the write-ahead log |
| `test_audit_chain.py` | 13 | Every entry is fingerprinted as it is written; an entry changed or removed afterwards is found and named; entries from before the chain are fingerprinted once by the upgrade, before anything else writes to the trail, and the check says which could not be checked |
| `test_audit.py` | 9 | Creates, edits, deletions, bulk wipes; blobs stay out of the log |
| `test_entry_edges.py` | 26 | Typed values are saved without surrounding spaces, so a trailing space cannot make a second agent; iPhone photographs (HEIC) are accepted; an agent roster that cannot be written is not a failed save; a phone number can be typed any way, a US one is saved as (703) 555-1234 with any extension, and anything else as typed |
| `test_messages.py` | 5 | A failed save or import stays on screen until acknowledged, a confirmation fades, the wipe itself shows nothing, and no debugging note reaches a message |
| `test_constraints.py` | 8 | The constraints that were removed, and the four that must stay |

---

## 17.0 Demo Data

A checkout ships with no case and no accounts; both are created on first run. To load a worked example instead — a fictional twelve-item search with agents, rooms, people and notes:

```
.venv/bin/python tools/make_demo_case.py
```

Add `--users` to reset the accounts at the same time and print fresh one-time passwords.

Everything it loads is invented: placeholder names, `example.invalid` addresses, and telephone numbers in the 555-01xx range reserved for fiction. It replaces the case entirely, so do not run it against real case data. The same case is a button away for training: **Load the demo case** in the Admin Panel, which asks for DEMO to be typed when a case is open and leaves accounts and the agent roster alone.

---

## 18.0 How The Code Is Laid Out

```
00 START HERE/          the install guide (and its PDF), and both Start files
Start VECTOR.bat        double-click launcher for Windows
Start VECTOR.command    double-click launcher for macOS, runs the .sh
Start VECTOR.sh         the macOS launcher itself
main.py                 startup, route table, first-run bootstrap
auth.py                 session state, sign-in throttling, route guards
models.py               tables, the audit listener, schema upgrades
clock.py                the machine's clock and time zone, for every stamp
crypto.py               SQLCipher detection and key handling
failures.py             plain-language reasons for failures, and the log
idle.py                 signs out a device nobody has touched
live.py                 refreshes open pages when another device saves
utils.py                validators, the active-case guard, shared helpers
import_export.py        CSV and JSON export and import
navbar.py               top navigation, the case badge, light or dark
settings.py             this machine's settings: network, printed date, redaction, Print All
home_page.py            login, main menu, the buttons on it
parts/case_transfer.py  export, import and Delete All Data
parts/admin_users.py    the Admin Panel's card, table and sessions
parts/file_upload.py    the upload card, the checks, the SHA-256
parts/file_table.py     the attachments list, downloads, deletes
parts/connect_page.py   the address another device should open, and its QR code
parts/case_search.py    the search over the whole case, in the top bar
parts/case_summary.py   Home's counts and its before-you-leave checklist
parts/drafts.py         keeps what was typed into a form and not saved
parts/crud.py           the table-driven builder every entity page uses
parts/crud_widgets.py   the Field description and the widgets
parts/crud_dialogs.py   edit, delete and delete-all
parts/*_page.py         one file per screen
program/config.py       paths, network and upload settings
program/inc/            Virginia jurisdictions, agencies, agent roles
tools/                  demo case, encryption, and make_shortcut.py (the desktop shortcut)
tests/                  the test suite
docs/                   field-test notes, and the guide to the October fixes (Markdown and PDF)
```

---

### 18.1 Adding A Field To An Entity

Entity pages are declarations, not code. To add a column, add it to the model in `models.py` and add one `Field` to that page's `SPEC` — the form input, the table column, the edit dialog and the delete confirmation all follow from it.

```python
Field("EVIDCONDITION", "Condition", kind="select",
      options=lambda: ["", "Sealed", "Damaged"])
```

`tests/test_page_specs.py` then checks the field names a real column, so a typo fails a test rather than a search warrant.

---

### 18.2 Adding A Page

Write the builder, then add one line to `PAGES` in `main.py`:

```python
("/exhibits", build_exhibits_page, False),   # True = admin only
```

The guard comes from that table. Writing it by hand per route is how `/admin` ended up reachable by any signed-in user and `/shutdown` by anyone at all.

---

## 19.0 Development

```
.venv/bin/python main.py --dev
```

Reloads on save. Note that a reload re-runs startup each time.

---

## 20.0 Credits

VECTOR was created by **SSA M. Sponheimer**, Virginia State Police [NOVA/DC ICAC](https://novadcicac.vsp.virginia.gov/). The scene workflow — the lettered rooms, the separate witness, the return copy as its own report — comes from that original design.

The security, audit, encryption, testing and install work contributed through pull requests #2 and #3 is by [Hitman90210](https://github.com/Hitman90210).

No license file has been published for the project. Ask the original author before reusing the code elsewhere.
