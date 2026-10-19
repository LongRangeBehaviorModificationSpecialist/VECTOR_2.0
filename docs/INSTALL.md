# Installing VECTOR

Step by step, for Windows and Mac. It takes about fifteen minutes, and
you only do it once per laptop.

**Contents**

- [What you need](#what-you-need)
- [1. Install Python](#1-install-python)
- [2. Get VECTOR](#2-get-vector)
- [3. Start VECTOR](#3-start-vector)
- [4. Sign in the first time](#4-sign-in-the-first-time)
- [5. Add your team](#5-add-your-team)
- [6. Put a shortcut on the desktop](#6-put-a-shortcut-on-the-desktop)
- [Every day](#every-day)
- [Using tablets](#using-tablets)
- [Updating to a new version](#updating-to-a-new-version)
- [Where your data is](#where-your-data-is)
- [If VECTOR does not start](#if-vector-does-not-start)
- [Removing VECTOR](#removing-vector)

---

## What you need

- A laptop running **Windows 10 or 11**, or a **Mac with macOS 11
  (Big Sur) or newer**. Linux works too; see
  [REFERENCE.md](REFERENCE.md#requirements).
- About **200 MB** of free space.
- An **internet connection the first time** VECTOR starts. After that it
  runs without one.
- Permission to install programs on the laptop. On an agency laptop you
  may need IT to do step 1.

---

## 1. Install Python

VECTOR is written in Python, so the laptop needs Python 3.10 or newer.

### Windows

1. Go to <https://www.python.org/downloads/> and press the yellow
   **Download Python** button.
2. Open the file you downloaded.
3. **On the first screen, tick "Add python.exe to PATH"** at the bottom.
   This is the step people miss. Without it VECTOR cannot find Python.
4. Press **Install Now**, and **Close** when it finishes.

### Mac

1. Go to <https://www.python.org/downloads/> and press **Download Python**.
2. Open the `.pkg` file you downloaded and press **Continue** through each
   screen, then **Install**.

### Check it worked (optional)

Open **Command Prompt** (Windows) or **Terminal** (Mac) and type:

```
python --version
```

On a Mac, type `python3 --version` instead. It should say
`Python 3.10` or a higher number.

---

## 2. Get VECTOR

1. On the VECTOR GitHub page, press the green **Code** button, then
   **Download ZIP**.
2. Unzip it into a folder you will keep, such as `Documents\VECTOR` on
   Windows or `Documents/VECTOR` on a Mac.
   - On Windows: right-click the ZIP, **Extract All**, choose the folder.
   - On a Mac: double-click the ZIP, then move the folder it makes.

Do not run VECTOR from inside the ZIP, or from the Downloads folder:
the case is saved inside the VECTOR folder, so put it somewhere it will
stay.

If you use `git`, `git clone` the repository instead.

---

## 3. Start VECTOR

### Windows

Double-click **`Start VECTOR.bat`** in the VECTOR folder.

If Windows says **"Windows protected your PC"**, press **More info**,
then **Run anyway**. It says this about any file downloaded from the
internet.

### Mac

Double-click **`Start VECTOR.command`** in the VECTOR folder.

If the Mac says it **cannot be opened because it is from an unidentified
developer**: right-click it, choose **Open**, then **Open** again. On
newer Macs you may need **System Settings → Privacy & Security → Open
Anyway** instead.

### The first start

A window opens and says **"Setting up VECTOR for the first time"**. It
downloads what VECTOR needs, which takes a few minutes. Leave it alone
until your web browser opens on the VECTOR sign-in page, at
<http://localhost:8080>.

**Keep that window open** while you use VECTOR. Closing it stops VECTOR.

---

## 4. Sign in the first time

1. The VECTOR window shows an administrator account:

   ```
   FIRST RUN - an administrator account has been created.
     Username:  admin
     Password:  (a one-time password)
   ```

   The same is saved in the file `db\FIRST_RUN_PASSWORD.txt` inside the
   VECTOR folder, in case the window scrolls.
2. Sign in with that username and password.
3. VECTOR asks you to choose your own password. Do that now.
4. **Delete `FIRST_RUN_PASSWORD.txt`** once you have.

---

## 5. Add your team

Give each agent their own account, so the audit trail shows who did what.

1. Open the account menu at the top right (**Welcome, admin**), then
   **Admin Panel**.
2. Type a username and press **Create User**.
3. VECTOR shows a one-time password **once**. Write it down and give it
   to the agent. They choose their own the first time they sign in.

New accounts are never administrators.

---

## 6. Put a shortcut on the desktop

### Windows

Right-click **`Start VECTOR.bat`**, then **Show more options**, then
**Send to → Desktop (create shortcut)**. Rename the shortcut to
**VECTOR** if you like.

### Mac

Right-click **`Start VECTOR.command`**, then **Make Alias**, and drag
the alias to the Desktop.

---

## Every day

- **Start:** double-click the shortcut, or the file in the VECTOR folder.
  Your browser opens on the sign-in page.
- **Stop:** close the VECTOR window. An administrator can also choose
  **Shutdown** from the account menu.
- **Help:** the **Help** page in VECTOR's top bar explains each page in
  short steps.

---

## Using tablets

Tablets and other laptops can use VECTOR over the same Wi-Fi:

1. An administrator turns on **Let other devices on this network reach
   VECTOR** in the **Admin Panel**.
2. Close the VECTOR window and start it again.
3. The first time, Windows asks whether to allow Python on the network.
   Allow it on **private networks** only. A Mac asks whether to accept
   incoming connections: allow it.
4. On the VECTOR laptop, open **Help → Connect a Device**. Type the
   address it shows, such as `http://192.168.1.23:8080`, into the
   tablet's browser.

The connection is not encrypted. Use a network you control, such as
your own hotspot, not a hotel's or the venue's Wi-Fi.

---

## Updating to a new version

1. Download and unzip the new version into a **new** folder.
2. From the old VECTOR folder, copy across:
   - the **`db`** folder: your cases, accounts and settings;
   - **`parts\agents.json`**: the agents remembered between searches.
3. Start VECTOR from the new folder. The first start installs anything
   new, so it needs the internet once.
4. When everything looks right, delete the old folder.

If you use `git`: close VECTOR, run `git pull`, and start it again.

---

## Where your data is

Everything about your cases is in the **`db`** folder inside the VECTOR
folder: the case, the attachments, the accounts and the audit trail.

- **Treat it as evidence.** Anyone who copies it can read the case,
  unless you have turned on database encryption (see
  [REFERENCE.md](REFERENCE.md#encrypting-the-case-database)).
- **To back it up**, close VECTOR and copy the whole `db` folder.
- **Never delete** the files ending in `-wal` or `-shm`. They hold the
  most recent changes.

---

## If VECTOR does not start

**"Python 3.10 or newer is needed"**: Python is not installed, or on
Windows the **"Add python.exe to PATH"** box was not ticked. Run the
Python installer again, tick it, and start VECTOR again.

**"Installing the packages failed"**: the internet connection dropped,
or a work network blocked the download. Start VECTOR again; it carries on
where it stopped.

**The window opens and closes at once**: open **Command Prompt** (or
**Terminal** on a Mac) in the VECTOR folder and start it from there, so
the message stays on screen:

```
"Start VECTOR.bat"
```

On a Mac: `./"Start VECTOR.command"`

**The browser did not open**: open it yourself and go to
<http://localhost:8080>.

**An error about port 8080, or "address already in use"**: VECTOR is
already running in another window, or another program is using the
port. Close the other VECTOR window first.

**Windows or the Mac will not run the file**: see the warnings in
[step 3](#3-start-vector).

**Mac: "permission denied"**: in Terminal, in the VECTOR folder, run
`chmod +x "Start VECTOR.command" "Start VECTOR.sh"` once.

**Forgot the admin password**: if another administrator can sign in,
they can press **Reset** next to the account in the **Admin Panel**. If
nobody can: close VECTOR, move the three files `users.db`,
`users.db-wal` and `users.db-shm` out of the `db` folder, and start
VECTOR again. With no accounts it creates a new `admin` with a one-time
password, as on the first start. The case is untouched; other accounts
need adding again.

Anything else: [REFERENCE.md](REFERENCE.md#troubleshooting) has the full
list.

---

## Removing VECTOR

1. Export any case you need (**Export Case Data** on the Home page), and
   keep a copy of the `db` folder if your policy says to.
2. Delete the VECTOR folder.
3. Python can stay, or be removed from **Settings → Apps** (Windows) or
   by deleting it from **Applications** (Mac).
