# Fixing what a merge leaves behind

A step-by-step guide to the fixes made after pull request #3 was merged
(13 to 15 October 2026): what each problem was, how it was found, how it
was fixed, and how to catch the same kind of thing yourself next time.

Every step here can be done on your own machine in a few minutes. The
commands are the ones actually used.

**Contents**

- [Set up once](#set-up-once)
- [The two-minute check before every push](#the-two-minute-check-before-every-push)
- [Reading a red X on GitHub](#reading-a-red-x-on-github)
- The fixes, one by one
  1. [The Audit Trail filter lost UPDATE](#1-the-audit-trail-filter-lost-update)
  2. [Imports left over from the merge](#2-imports-left-over-from-the-merge)
  3. [A test that checked the wrong thing](#3-a-test-that-checked-the-wrong-thing)
  4. [RAR archives were refused](#4-rar-archives-were-refused)
  5. [db/settings.json was committed](#5-dbsettingsjson-was-committed)
  6. [The print window's buttons](#6-the-print-windows-buttons)
  7. [The triple border on an iPad](#7-the-triple-border-on-an-ipad)
- [Resolving a conflict on your own machine](#resolving-a-conflict-on-your-own-machine)
- [Checklist](#checklist)
- [Where each fix is](#where-each-fix-is)

---

## Set up once

From the project folder, make the virtual environment and install both
the app's packages and the tools that check it:

**macOS / Linux**

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

**Windows**

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

`requirements-dev.txt` adds two tools:

- **pytest** runs the test suite: 495 small programs that each use a
  part of VECTOR and check the result.
- **ruff** reads the code without running it and reports real errors:
  a name used but never defined, an import nothing uses, a variable
  assigned and then ignored.

In a new terminal, run the `activate` line again before the commands
below.

---

## The two-minute check before every push

```
ruff check .
pytest
```

- `ruff check .` should end with **All checks passed!**
- `pytest` should end with **495 passed** (or however many there are
  by then), and no **failed**.

If either one complains, fix that before pushing. GitHub runs exactly
these two on every push, so anything they report locally will show up
as a red X there too.

Since 13 October every push to `main` had a red X. Those checks were
reporting problems 2 and 3 below the whole time.

---

## Reading a red X on GitHub

1. Open the repository on GitHub and click the **Actions** tab, or the
   red X next to a commit.
2. Click the failing run, then the failing job: **ruff**, or one of the
   **ubuntu-latest / windows-latest** test jobs.
3. Expand the step with the red X: **Look for errors, not style** for
   ruff, **Run the tests** for pytest.
4. The lines that matter are near the bottom: `F401 ... imported but
   unused` from ruff, or `FAILED tests/...` with an `AssertionError`
   from pytest. They name the file and line.

A test job fails if one test fails, even if 494 passed. The summary line
says which one.

---

## The fixes, one by one

### 1. The Audit Trail filter lost UPDATE

**What you would have seen.** The **Action** filter on the Audit Trail
page had no **UPDATE**. Edits are the commonest entry after new
records, and there was no way to list just those.

**Why it happened.** Both sides of the merge had changed the same list.
Your side sorted it A to Z and added `DOWNLOAD`, which moved `UPDATE` to
the end. The branch side had added `LOGOUT_IDLE` and `SETTING_CHANGED`
at the end. Git could not tell which end-of-list was right, so it asked:

```
    "LOGIN",
    "LOGIN_FAILED",
<<<<<<< HEAD
    "LOGOUT_IDLE",
    "SETTING_CHANGED",
=======
    "UPDATE",
>>>>>>> b773f4e
]
```

The top half (`HEAD`) is one side, the bottom half is the other, and
the markers have to go. The resolution kept the top half, but the right
answer here was **both halves**:

```
    "LOGIN",
    "LOGIN_FAILED",
    "LOGOUT_IDLE",
    "SETTING_CHANGED",
    "UPDATE",
]
```

**How to spot it.** A conflict is never "pick a side" by default. For
each one, ask what each side was trying to do. Here one side was adding
`UPDATE` back in its new place, the other was adding two new entries,
and both were right.

**The fix.** Add `"UPDATE",` back at the end of `ACTION_CHOICES` in
[`parts/audit_page.py`](../parts/audit_page.py).

**So it cannot happen again.** A new test reads every `action="..."`
the application writes, adds the CREATE/UPDATE/DELETE written
automatically, and fails if the filter cannot offer one of them:

```python
def test_every_action_vector_records_can_be_filtered_for():
    root = Path(audit_page.__file__).resolve().parent.parent
    recorded = {"CREATE", "UPDATE", "DELETE"}  # written by the flush listener
    for source in root.glob("*.py"):
        recorded |= set(re.findall(r'action="([A-Z_]+)"', source.read_text("utf-8")))
    for source in (root / "parts").glob("*.py"):
        recorded |= set(re.findall(r'action="([A-Z_]+)"', source.read_text("utf-8")))
    missing = recorded - set(audit_page.ACTION_CHOICES)
    assert not missing, f"Not in the Audit Trail filter: {sorted(missing)}"
```

It is in `tests/test_session_and_search.py`. To check that a new test
really catches the problem, do this before committing the fix: set the
fix aside, run the test and watch it fail, then put the fix back:

```
git stash push parts/audit_page.py
pytest tests/test_session_and_search.py -k every_action
git stash pop
```

It printed `Not in the Audit Trail filter: ['UPDATE']`, so the test
works.

---

### 2. Imports left over from the merge

**What ruff said.** Sixteen errors, all of two kinds:

```
parts\files_page.py:15:5: F401 `models.audit_timestamp` imported but unused
...
parts\file_upload.py:34:5: F401 `utils.get_mime_type` imported but unused
parts\reports_page.py:482:9: F841 Local variable `evidence` is assigned to but never used
parts\reports_page.py:483:9: F841 Local variable `rooms` is assigned to but never used
```

- **F401** is an import nothing uses.
- **F841** is a variable that is set and never read.

**Why it happened.** On the branch, the Files page had been split into
three files: `files_page.py` (the page and the download route),
`parts/file_upload.py` (the upload card) and `parts/file_table.py` (the
list). Your side still had the single long file. Resolving the conflict
in `files_page.py` kept your side's import block, which carried the
imports for code that had since moved to the other two files. It also
dropped the two imports for the new files. That is why the Files page
stopped opening, which you fixed in 44379de by adding them back.

You also spotted that your upload change had to go into
`parts/file_upload.py` now, and carried it there in fdcf24d. That is the
step most people miss when code moves between files in a merge.

**How to find where code went.** When a merge shows code you remember
in one file, search the whole project for it before resolving:

```
git grep -n "def upload_card"
git grep -n "get_mime_type"
```

`git grep` searches only files git tracks, so it skips `.venv`.

**The fix.**

1. Let ruff remove the unused imports, then read what it changed:

   ```
   ruff check . --fix
   git diff
   ```

2. Remove the two unused queries by hand. ruff will not delete a line
   that runs code. In `validate_case_for_report()` in
   [`parts/reports_page.py`](../parts/reports_page.py):

   ```python
   case = session.query(Cases).first()
   evidence = session.query(Evidence).all()   # removed: never used
   rooms = session.query(Rooms).all()         # removed: never used
   ```

   These were more than tidiness: each one read every evidence item and
   every room from the database every time a report page opened, and
   threw the result away. The rooms check now lives with the Room List,
   where you put it.

3. Run `ruff check .` again: **All checks passed!**

---

### 3. A test that checked the wrong thing

**What the test said.**

```
FAILED tests/test_validators.py::test_unknown_content_is_not_trusted
AssertionError: assert 'application/x-msdownload' == 'application/octet-stream'
```

**Why it happened.** The test gave `derive_mime_type()` the first bytes
of a Windows program (`MZ`) named `evil.pdf`, and expected
"unknown" (`application/octet-stream`). But `filetype` *recognises* a
Windows program, so it answered `application/x-msdownload`. The code
did the right thing, since the file was still refused; only the test's
expectation was off.

**How to find out what a library really returns.** Ask it, in one line:

```
python -c "import filetype; print(filetype.guess(b'MZ' + bytes(64)).mime)"
```

**The fix.** Test what matters, which is that the file is refused, not
the label it gets on the way. And add a second test for content that
really is unrecognised:

```python
def test_a_program_named_pdf_is_not_trusted():
    mime = utils.derive_mime_type("evil.pdf", b"MZ\x90\x00 not a pdf")
    assert mime != "application/pdf"
    assert not utils.is_allowed_file(mime)


def test_unrecognised_content_is_not_trusted():
    mime = utils.derive_mime_type("evil.pdf", b"\x00\x01 nothing known")
    assert mime == "application/octet-stream"
    assert not utils.is_allowed_file(mime)
```

**The habit.** Run a new test before pushing it, and see it pass. Then
break the code on purpose and see it fail.

---

### 4. RAR archives were refused

**What an agent would have seen.**

> 'photos.rar' is not an allowed file type (application/x-rar-compressed).

**Why it happened.** The same file type can have two names. The allowed
list in [`utils.py`](../utils.py) had the official name for RAR,
`application/vnd.rar`, which is what Python's `mimetypes` (going by the
file name) returned before. `filetype` (going by the content) calls it
`application/x-rar-compressed`. Once uploads were typed by content,
every RAR file was refused.

**How to find this kind of thing.** Put one real file of each kind
agents attach in a folder called `samples`: a phone photo, an iPhone
photo (HEIC), a video, a PDF, a Word file, an Excel file, a ZIP, a RAR.
Then run:

```python
from pathlib import Path
import utils

for f in sorted(Path("samples").iterdir()):
    mime = utils.derive_mime_type(f.name, f.read_bytes())
    verdict = "ok" if utils.is_allowed_file(mime) else "REFUSED"
    print(f"{f.name:30} {mime:45} {verdict}")
```

Anything marked REFUSED that agents need is a name to add to the list.

**The fix.** One line in `ALLOWED_MIME_TYPES`:

```python
    "application/vnd.rar",
    # What derive_mime_type() calls a RAR file, from its content.
    "application/x-rar-compressed",
```

and a test that a RAR archive is accepted.

---

### 5. db/settings.json was committed

**Why it matters.** `db/settings.json` holds this machine's choices,
and one of them is **network access**. If a copy with network access on
were ever committed, every machine that updated would start opening
VECTOR to its network. And on any machine where someone has flipped a
switch, git refuses to update over the local copy.

**How it got in.** A new file that `.gitignore` does not mention gets
picked up by `git add .` or by "commit all" in GitHub Desktop. The
databases were in `.gitignore`, but `settings.json` was not. That one is
on our side: it should have gone into `.gitignore` when the settings
file was added.

**The fix.**

1. Add it to [`.gitignore`](../.gitignore), next to the databases:

   ```
   /db/settings.json
   ```

2. Take it out of the repository, but not off your disk:

   ```
   git rm --cached db/settings.json
   git commit -m "db/settings.json is each machine's own"
   ```

   `--cached` is the important part. Without it, git deletes your copy
   as well.

**After you pull this.** Git takes away the copy it had put there, so
your three switches (network access, printed date, Agent List
redaction) go back to off, once. If git refuses to update because the
file has changed on your machine, move it out of `db/`, update, and move
it back.

**The habit.** Look at the list of files before every commit, with
`git status` or GitHub Desktop's file list. Nothing under `db/` should
ever be in it.

---

### 6. The print window's buttons

**What was wrong.** The window **Print Report** opens had **Print
Report** and **Close** buttons with the classes `print-btn` and
`close-btn`, but no style was ever written for them, so the browser drew
its own default buttons: small, grey and hard to hit on an iPad. On a
laptop in **dark mode**, Chrome also painted the new window near-black
while the report's text stayed black, so the report was close to
unreadable until it printed.

**How to see it.** Open any report and press **Print Report**. For the
dark window, switch the computer to dark mode first.

**The fix**, in [`parts/reports_page.py`](../parts/reports_page.py):

- `PRINT_WINDOW_STYLES`: styles for the window only. A dark bar across
  the top that stays put while you scroll, two 44-pixel buttons (the
  smallest target Apple recommends for a finger), and a white page set
  under `@media screen`, so printing is unchanged.
- `print_toolbar_html()` builds the bar, which names the report and the
  case.
- `render_report_page()` now takes the report's name, and each of the
  eight report pages passes its own.

Two details worth copying:

- **Where a style goes matters.** The white page could not go into
  `COMMON_STYLES`, because those same styles are drawn inside VECTOR's
  own dark report page, which would have turned white. The window's
  styles are added only where the window is written.
- **Anything a person typed is escaped before it goes into HTML.** The
  case number goes through `h()`, so a case number containing `<` shows
  as text instead of becoming markup. Tests check both.

---

### 7. The triple border on an iPad

**What was wrong.** On an iPad, raised buttons such as **Delete All
Files** looked as if they had two or three borders. Two causes stacked
up:

- `.hover-border-white` gave every button a `2px solid transparent`
  border, to keep room for the dashed hover line. On a raised (`push`)
  button, the button's colour showed through that transparent border as
  a ring outside the raised face.
- An iPad has no mouse, so after a tap it keeps the button in its
  `:hover` state until something else is tapped. The dashed white line
  went on top of the ring and the raised edge.

**How to see it without an iPad.** In Chrome, open DevTools (F12) and:

- Press **Ctrl+Shift+M** (Cmd+Shift+M on a Mac) for the device toolbar
  and pick an iPad. The page now behaves as a touch screen.
- In the **Elements** panel, select the button and click **:hov**, then
  tick **:hover** to hold the button in its hover state.

**The fix**, in the CSS in [`main.py`](../main.py):

```css
.hover-border-white {
    color: var(--vsp-white);          /* no transparent border any more */
}

@media (hover: hover) {               /* only where there is a mouse */
    .hover-border-white:hover::after,
    .hover-border-blue:hover::after {
        content: "";
        position: absolute;
        inset: 3px;                   /* just inside the button */
        border: 2px dashed white;
        border-radius: inherit;
        pointer-events: none;
    }

    .hover-border-blue:hover::after {
        border-color: var(--vsp-blue);
    }
}
```

With a mouse it looks as it did. On a touch screen the dashed line
never appears.

**Why not just use `outline`?** That was tried first, and nothing
showed. DevTools → **Computed** said `outline: none`. Quasar gives its
buttons the class `no-outline`, which is `outline: 0 !important`, and
NiceGUI loads Quasar's `!important` rules in a cascade layer that
outranks any `!important` in our own CSS. The `::after` element is
something Quasar does not touch. When a style you wrote does not apply,
**Computed** shows what the browser ended up using, and **Styles** shows
which rule won.

---

## Resolving a conflict on your own machine

GitHub's web editor is fine for a line of text. For Python code,
resolve on your own machine, where you can run the app and the tests
before anything is committed.

To bring `main` into a pull request's branch (what the web editor
does), fetch the pull request's branch with the
[GitHub CLI](https://cli.github.com/), which works even when the branch
lives on someone else's fork:

```
gh pr checkout <number>
git fetch origin
git merge origin/main
```

Git lists the files with conflicts. In each one:

1. Find every `<<<<<<<` … `=======` … `>>>>>>>` block.
2. Work out what each side was trying to do, and write the result that
   does both. Delete the three marker lines.
3. If the other side moved code to a different file, carry your change
   to where the code is now (`git grep` finds it).

Then check before committing:

```
ruff check .
pytest
python main.py          # open the pages the conflict touched
git add <the files>
git commit
git push                # back to the pull request
```

`git push` updates the pull request, as long as it allows edits by
maintainers (the default).

---

## Checklist

Before every push:

- [ ] `git pull` first, so you are working on the latest code
- [ ] After any merge conflict: read the whole function or list as it
      now stands, not just the lines between the markers
- [ ] `ruff check .` → **All checks passed!**
- [ ] `pytest` → no **failed**
- [ ] `git status` → nothing under `db/`
- [ ] For a change people will see: look at it on an iPad (or DevTools'
      device toolbar) and in dark mode
- [ ] After pushing: the commit has a green tick on GitHub

---

## Where each fix is

On branch `fix/after-pr3-merge` of
[Hitman90210/VECTOR_2.0](https://github.com/Hitman90210/VECTOR_2.0):

| Commit | What it does | Files |
|--------|--------------|-------|
| `706bdd9` | The Audit Trail filter offers UPDATE again, with a test for every action | `parts/audit_page.py`, `tests/test_session_and_search.py` |
| `908b728` | RAR accepted again; the file-type tests check the outcome | `utils.py`, `tests/test_validators.py` |
| `217a677` | The 16 lint errors left by the merge | `parts/files_page.py`, `parts/file_upload.py`, `parts/reports_page.py` |
| `a833151` | `db/settings.json` out of version control | `.gitignore`, `db/settings.json` |
| `97c1f49` | README test counts | `README.md` |
| `d713095` | The print window's bar, buttons and white page | `parts/reports_page.py`, `tests/test_reports.py` |
| `61525bd` | No triple border on an iPad | `main.py`, `tests/test_logo_and_help.py` |

To see any one of them in full:

```
git show 706bdd9
```

Each commit's message explains the why as well as the what.
