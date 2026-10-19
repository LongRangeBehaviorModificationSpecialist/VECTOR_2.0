# V·E·C·T·O·R

**Virginia Evidence Collection, Tracking, Organization & Reporting**

VECTOR keeps the paperwork for a search warrant: who was on site, how
the premises were divided, what was seized from where, who found it and
who witnessed it. At the end it prints the scene reports, including the
inventory left at the premises, and exports the whole case.

It runs on your own laptop. Nothing is sent anywhere.

`Windows` · `macOS` · `Linux` · `Python 3.10+`

> **About.** VECTOR was created by SSA M. Sponheimer of the Virginia
> State Police NOVA/DC ICAC
> ([original repository](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0)).
> Security hardening, an audit trail, optional database encryption, a
> test suite and a cross-platform install were contributed from
> [Hitman90210's fork](https://github.com/Hitman90210/VECTOR_2.0) and
> merged in pull requests
> [#2](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0/pull/2),
> [#3](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0/pull/3) and
> [#4](https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0/pull/4).

---

## What it does

**During the search**

- **Case**: number, address, jurisdiction, start and end time
- **Agents**: everyone on site, remembered for the next search
- **Rooms**: the premises lettered A, B, C… with the agents who searched each
- **Evidence**: numbered for you, with where it was found, who found it, and a witness
- **People** and **Notes**
- **Files**: photographs and documents, fingerprinted the moment they arrive

**At the end**

- **Eight printable reports**, including the inventory left at the premises
- **Export** the whole case to a file, protected with a password if you choose

**Throughout**

- An **audit trail** of every change, sign-in and download
- **Accounts** for each agent, and tablets on the same Wi-Fi if you allow it

---

## Install

**Open the [00 START HERE](00%20START%20HERE/) folder.** It has the install guide,
with pictures, as a PDF to read or print, and the files that start
VECTOR. In short:

1. **Install Python 3.10 or newer** from [python.org](https://www.python.org/downloads/).
   On Windows, tick **"Add python.exe to PATH"** on the installer's first screen.
2. **Download VECTOR**: the green **Code** button above, then **Download ZIP**.
   Unzip it to a folder you will keep, such as `Documents\VECTOR`.
3. **Double-click** `Start VECTOR (Windows).bat` or `Start VECTOR (Mac).command`
   in **00 START HERE**. The first start takes a few minutes and needs the
   internet, and offers a desktop shortcut with VECTOR's icon; after that
   it starts straight away.
4. **Sign in** as `admin` with the one-time password the VECTOR window shows,
   then choose your own.

The step-by-step version, with what each screen looks like and what to do
when something goes wrong, is in **[00 START HERE](00%20START%20HERE/)**.

---

## Using it

Work through the pages in order: **Case**, **Agents**, **Rooms**,
**Evidence**, **People**, **Notes**, **Files**, then **Reports**.

The **Help** page inside VECTOR (in the top bar) explains each one in a
few short steps, with a search box. It also covers printing, tablets,
passwords, and what each message means.

**Before you clear a case, export it:** **Export Case Data** on the Home
page.

---

## Keeping the case safe

- **The case lives in the `db` folder** on this laptop. Treat that folder
  as evidence. It is not encrypted unless you turn on
  [database encryption](docs/REFERENCE.md#encrypting-the-case-database).
- **Tick "Encrypt with password" when you export.** A forgotten password
  cannot be recovered.
- **Tablets connect over plain HTTP.** Use a network you control, such as
  your own hotspot.
- **Every change is in the audit trail**, which nothing in VECTOR can edit.

---

## Updating

Download the new version and unzip it to a new folder. From the old
folder, copy across the `db` folder (your cases, accounts and settings)
and `parts\agents.json` (the agents remembered between searches). The
first start after an update installs anything new, so it needs the
internet once. If you use `git`, run `git pull` instead.

---

## More

| Document | For |
|---|---|
| [00 START HERE](00%20START%20HERE/) | Installing VECTOR, step by step, with pictures (also as a PDF) |
| The **Help** page, inside VECTOR | Using it at a scene |
| [docs/REFERENCE.md](docs/REFERENCE.md) | Everything in detail: settings, tablets, upgrading, security, encryption, troubleshooting, tests and how the code is laid out |
| [docs/fixing-after-a-merge.md](docs/fixing-after-a-merge.md) ([PDF](docs/VECTOR-fixing-after-a-merge.pdf)) | Checking changes before you push them |
| [docs/field-test-2026-09-29.md](docs/field-test-2026-09-29.md) | Notes from the first search warrant VECTOR was used on |

**Developers:** `pip install -r requirements-dev.txt`, then `ruff check .`
and `pytest` before every push. See
[docs/REFERENCE.md](docs/REFERENCE.md#how-the-code-is-laid-out).

---

## Credits

VECTOR was created by **SSA M. Sponheimer**, Virginia State Police
NOVA/DC ICAC. The scene workflow, with lettered rooms, a separate witness
for every item and the return copy as its own report, comes from that
original design.

The security, audit, encryption, testing and install work contributed
through pull requests #2, #3 and #4 is by
[Hitman90210](https://github.com/Hitman90210).

No license file has been published for the project. Ask the original
author before reusing the code elsewhere.
