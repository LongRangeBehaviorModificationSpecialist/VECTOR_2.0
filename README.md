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

**Export** seals every table, every attachment and a SHA-256 manifest
into a single AES-256 encrypted ZIP on your Desktop. **Import** restores
one, replacing everything currently loaded.

---

## Known limitations

Read these before relying on VECTOR for a case that will be charged.

- **No audit trail.** Records can be edited or deleted by any signed-in
  user with no history of what changed, when, or by whom.
- **One case at a time.** The database holds a single case. "Make New
  Case File" deletes the current one — export first.
- **Note authorship is self-declared**, chosen from a dropdown rather
  than taken from the signed-in user.
- **Evidence file hashes are computed at export**, not at collection.
- **New accounts share a default password** defined in `models.py`.
  Change it after creating a user.

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

---

## Development

```
.venv/bin/python main.py --dev
```

Reloads on save. Note that a reload re-runs startup each time.
