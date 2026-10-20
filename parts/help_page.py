#!/usr/bin/env python3

"""
help_page.py — the Help page.

Short topics, one per part of a search, each opened on its own, with a
search box that narrows them. Written for the agent using VECTOR at a
scene, not for whoever installed it: the install guide and the README
cover that.

Names in bold are buttons, switches and menus as they appear on screen.
tests/test_logo_and_help.py checks each one still exists, so renaming a
button fails a test instead of leaving the help out of date.
"""

from nicegui import ui

from auth import LOCK_AFTER_FAILURES, LOCKOUT_MINUTES
from program.config import Config


# (icon, title, text). The first topic opens with the page.
HELP_SECTIONS = [
    ("flag", "Start here", """
VECTOR keeps the paperwork for one search warrant: who was there, the
rooms, what was seized, and the reports you print at the end. It holds
*one case at a time*.

Work through it in this order:

1. **Start New Case** on the Home page: the case details.
2. **Add Agent**: everyone on site.
3. **Add Room**: each part of the premises gets a letter.
4. **Add Evidence**: each item seized.
5. **Add Person**: suspects and anyone else present.
6. **Add Note**: anything else worth writing down.
7. **Files**: photographs and documents.
8. **Reports**: print the lists when you finish.

Until a case is open, the top bar says **No Active Case** and nothing
can be saved. On a phone or small tablet, the page buttons are under the
menu button (three lines) at the top left.
"""),

    ("folder_open", "The case", """
1. Press **Start New Case** on the Home page.
2. Fill in the case number, the address, the jurisdiction, and when the
   search started, as `MM-DD-YYYY HH:MM`. **Fill with current date/time**
   puts in the time now.
3. Press **Open New Case**. The case number now shows at the top of
   every page.

When you finish, add the end time: open **Case**, press the pencil next
to the case, and fill in Date/Time Ended. The Reports page also offers to
fill it in for you.

*Starting a different case* deletes this one, after a warning.
Export it first: see *Saving the case*.
"""),

    ("badge", "Agents", """
- One entry for each person on site. Write names as `Last, First`.
- Pick the agency and role from the lists, or type one that is not there.
- *Phone:* type it any way you like. A US number is saved as
  `(703) 555-1234`; add an extension at the end, like `x12`. Numbers from
  other countries are kept as typed.
- Everyone you add is remembered. At the next search their name is in
  the list: pick it instead of typing it again.
"""),

    ("meeting_room", "Rooms", """
- Each area of the premises gets a letter: A, B, C, and after Z, AA, AB.
  The next letter is filled in for you.
- Describe it (`Kitchen`, `Detached garage`) and pick the two agents who
  searched it. You can add the agents later.
- Renaming a room moves its evidence with it.
"""),

    ("inventory_2", "Evidence", """
- The item number is filled in for you.
- Pick the room it was found in, and say where in the room.
- Pick who found it and who witnessed it. The witness must be a
  different person.
- Mark whether it was photographed, triaged, and contains contraband.

*Deleting an item renumbers the items after it*, so the list never
skips a number. Once bags are labelled, change an item with the pencil
instead of deleting it, or the labels will no longer match.
"""),

    ("person", "People", """
- Suspects and anyone else present at the search.
- Date of birth as `MM-DD-YYYY`.
"""),

    ("edit_note", "Notes", """
- Anything worth writing down that is not an item or a person.
- Your name and the time are added for you, and notes stay in the order
  they were written.
"""),

    ("photo_camera", "Files and photos", """
- On **Files**, drag files onto the box, or click it to choose them.
- On a phone or tablet, **Take a photograph** opens the camera.
- Accepted: photographs (including iPhone HEIC), videos, PDFs, Word,
  Excel and PowerPoint files, text files, and ZIP, 7z and RAR archives.
- VECTOR checks what a file really is. A program renamed `photo.jpg` is
  refused, and the message says what the file actually is.
- Each file gets a fingerprint (SHA-256) when it is added, so any later
  change to it can be detected. Every download is recorded in the
  **Audit Trail**.
"""),

    ("print", "Reports and printing", """
1. Open **Reports** and press the report you want.
2. Press **Print Report**. The report opens in its own window.
3. In that window, press **Print Report** to print, or **Close**. The
   bar at the top of the window is not printed.

*Nothing opened?* The browser blocked the window. Allow pop-ups for
VECTOR, or press Ctrl+P (⌘+P on a Mac) on the report page.

*Room List:* if a room is missing an agent, **Print Room List** says
which. Add the names on **Rooms**, or press
**Print Report Without Names**; the blanks print as [NOT RECORDED].

Two switches on the Reports page, both off unless you turn them on:

- **Show the date and time each report is printed**
- **Redact agent phone numbers and emails on the Agent List**

The *Evidence List (Basic)* is the inventory left at the premises. If
the case has no end time yet, the Reports page offers to fill it in.
"""),

    ("tablet_mac", "Tablets and other laptops", """
VECTOR runs on one laptop. Tablets and other laptops can use it over the
same Wi-Fi:

1. An administrator opens **Admin Panel** (account menu, top right) and
   turns on **Let other devices on this network reach VECTOR**.
2. Restart VECTOR: close its window and start it again.
3. On that laptop, open **Help**, then **Connect a Device**. It shows the
   address to type on the tablet, such as `http://192.168.1.23:8080`.
4. Each person signs in with their own account.

Pages update by themselves when someone else saves. The connection is
not encrypted, so use a network you control, such as your own hotspot,
not a hotel's or the venue's Wi-Fi.
"""),

    ("save", "Saving the case: export and import", """
- **Export Case Data** (Home page) downloads the whole case to the device
  you are using: CSV opens in Excel, JSON is one file for other systems,
  or both. Tick **Encrypt with password (AES-256)** and set a password.
  A forgotten password cannot be recovered.
- **Import Case Data** loads a file you exported. It replaces the case
  on this computer. If the file was exported with a password,
  VECTOR asks for it.
- **Delete All Data** empties the case. Accounts and the audit trail are
  kept. It cannot be undone, so export first.
"""),

    ("lock", "Accounts and passwords", f"""
- An administrator adds accounts in **Admin Panel** (account menu, top
  right). A new password is shown once: write it down. The first time
  the person signs in, VECTOR shows **Change Password** and nothing
  else until they choose a password of their own.
- Forgotten password: an administrator presses **Reset** next to the
  account and gives them the new one. It works the same way.
- Choosing a new password signs out any other device that was signed
  in to the account.
- After {LOCK_AFTER_FAILURES} wrong passwords an account is locked for
  {LOCKOUT_MINUTES} minutes. An administrator can clear the lock sooner.
- A device nobody touches for {Config.SESSION_IDLE_MINUTES} minutes signs
  itself out. A warning comes first, with **Stay signed in** on it.
  Anything already saved is kept; a form you were still filling in is
  lost, so save before you walk away.
- A device has gone missing? **Sign Everyone Out** in the Admin Panel
  ends every session at once. A page left open on any device goes back
  to the sign-in page within seconds, and saves nothing more.
- Sign out with **Logout** in the account menu.
"""),

    ("history", "Audit Trail", """
- Administrators: account menu, then **Audit Trail**.
- It records every change, sign-in, sign-out, export and download, and
  every account an administrator adds, resets, unlocks or deletes: who,
  when, and what changed. Nothing in VECTOR can edit or delete an entry,
  not even an administrator.
- Choose an action to filter by, or search for a name or an item.
- **Check the trail** confirms no entry has been altered outside VECTOR
  since it was written.
"""),

    ("help_outline", "If something goes wrong", f"""
- *"No active case"*: open a case first, with **Start New Case**.
- *"A case is already open"*: VECTOR holds one case. Export it, then
  use **Start New Case**.
- *"... is not an allowed file type"*: the file is not a photograph,
  video, document or archive. The message says what it found.
- *The print window does not open*: see *Reports and printing*.
- *A tablet cannot connect*: is it on the same Wi-Fi? Was network
  access turned on, and VECTOR restarted? Type the address from
  **Connect a Device** exactly, including the `:8080`.
- *A message that stays on screen* means something did not happen,
  and says why. Read it and press OK. The technical detail is in the
  VECTOR window, for whoever looks after the laptop.
- *Locked out*: wait {LOCKOUT_MINUTES} minutes, or ask an administrator.
- *"This device was signed out"*: an administrator ended the session, or
  the account's password was changed on another device. Sign in again;
  anything saved before then is kept.
"""),

    ("info", "About VECTOR", """
- **About App** under **Help** shows the version and who wrote VECTOR.
- **Tools** has links to forensic software, DFIR and OSINT resources.
- Times are this computer's local time. Times VECTOR records itself show
  their offset from UTC, such as `UTC-04:00`.
"""),
]

# Every topic as one text: what the tests check the bold names in.
HELP_TEXT = "\n\n".join(text for _icon, _title, text in HELP_SECTIONS)


def build_help_page() -> None:
    """The topics, and a search box that narrows them."""
    with ui.column().classes("w-full items-center"):
        with ui.column().classes("w-full max-w-3xl mt-8 mb-12 px-4 gap-3"):
            ui.label("Help").classes("text-2xl font-bold")
            ui.label(
                "Short answers to how VECTOR works. Open a topic, or search."
            ).classes("text-sm text-[var(--vsp-gray)]")

            search = ui.input(
                placeholder="Search the help: try print, tablet or password",
            ).props("clearable outlined dense").classes("w-full mb-2")

            nothing = ui.label(
                "Nothing in the help matches that. Try a shorter word."
            ).classes("text-sm text-[#F5B027]")
            nothing.set_visibility(False)

            topics = []
            for index, (icon, title, text) in enumerate(HELP_SECTIONS):
                with ui.expansion(
                    title, icon=icon, value=index == 0,
                ).props(
                    'header-class="text-base font-semibold"'
                ).classes(
                    "w-full rounded-lg border border-[#3a3a3a]"
                ) as topic:
                    ui.markdown(text).classes("text-sm px-4 pb-2")
                topics.append((topic, f"{title} {text}".lower()))

            def narrow(_event=None) -> None:
                words = (search.value or "").lower().split()
                shown = 0
                for topic, words_in_it in topics:
                    match = all(word in words_in_it for word in words)
                    topic.set_visibility(match)
                    if words:
                        # A match is opened, so the answer is in view.
                        topic.value = match
                    shown += match
                nothing.set_visibility(shown == 0)

            search.on_value_change(narrow)
