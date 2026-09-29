#!/usr/bin/env python3

"""
make_demo_case.py

Replaces the contents of db/app_data.db with a fictional demo case.

Written because the working database carried real names and real work
email addresses of serving officers. Anything checked out, copied to a
spare laptop, or handed to someone evaluating the tool should contain
invented people only.

Everything below is fabricated. The names are obvious placeholders, the
addresses are not real addresses, and the phone numbers are in the
555-01xx range reserved for fiction.

    .venv/bin/python tools/make_demo_case.py            (macOS / Linux)
    .venv\\Scripts\\python tools\\make_demo_case.py       (Windows)

Add --users to reset the accounts as well; it prints the new one-time
passwords once.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import (  # noqa: E402
    Agents,
    Cases,
    Evidence,
    Notes,
    Persons,
    Rooms,
    UploadedFiles,
    Users,
    audit_timestamp,
    generate_one_time_password,
    get_session,
    get_users_session,
    init_db,
    record_audit,
)

def _scene_time(text: str) -> str:
    """A demo time as VECTOR stamps it: local, with the offset from UTC."""
    import clock
    from datetime import datetime

    return clock.stamp(
        datetime.strptime(text, "%m-%d-%Y %H:%M:%S").astimezone()
    )


DEMO_CASE = {
    "CASENUMBER": "26-DEMO-001",
    "LOCATION": "1 Example Way, Springfield",
    "JURISDICTION": "Fairfax County",
    "CASEDATETIMEBEGIN": "09-01-2026 07:30",
    "CASEDATETIMEEND": "09-01-2026 15:45",
}

DEMO_AGENTS = [
    (
        "Demo, Alex",
        "Virginia State Police",
        "Case Agent (Primary)",
        "", "555-0101",
        "alex.demo@example.invalid"
    ),
    (
        "Sample, Bailey",
        "Virginia State Police",
        "Search",
        "Photographer",
        "555-0102",
        "bailey.sample@example.invalid"
    ),
    (
        "Placeholder, Casey",
        "Fairfax County Police",
        "Evidence Triage",
        "",
        "555-0103",
        "casey.placeholder@example.invalid"
    ),
    (
        "Testcase, Devon",
        "Town of Herndon Police",
        "Photographer",
        "",
        "555-0104",
        ""
    ),
    (
        "Fixture, Ellis",
        "Loudon County Sheriff's Office",
        "Search",
        "",
        "555-0105",
        ""
    ),
]

DEMO_ROOMS = [
    (
        "A",
        "Living Room",
        "Demo, Alex",
        "Sample, Bailey"
    ),
    (
        "B",
        "Kitchen",
        "Placeholder, Casey",
        "Testcase, Devon"
    ),
    (
        "C",
        "Main Bedroom",
        "Demo, Alex",
        "Fixture, Ellis"
    ),
    (
        "D",
        "Second Bedroom",
        "Sample, Bailey",
        "Placeholder, Casey"
    ),
    (
        "E",
        "Detached Garage",
        "Testcase, Devon",
        "Fixture, Ellis"
    ),
]

DEMO_EVIDENCE = [
    (
        "1",
        "1",
        "Laptop computer, silver",
        "XPS-13",
        "SN-0000001",
        "Room A (Living Room)",
        "On coffee table",
        "Demo, Alex",
        "Sample, Bailey",
        "Yes",
        "Yes",
        "Placeholder, Casey",
        "Unknown",
        "Powered off at seizure"
    ),
    (
        "2",
        "1",
        "Mobile telephone, black, cracked screen",
        "Model-9",
        "SN-0000002",
        "Room C (Main Bedroom)",
        "Nightstand drawer",
        "Demo, Alex",
        "Fixture, Ellis",
        "Yes",
        "Yes",
        "Placeholder, Casey",
        "Yes",
        "Airplane mode enabled at seizure"
    ),
    (
        "3",
        "4",
        "USB flash drives, assorted",
        "",
        "",
        "Room C (Main Bedroom)",
        "Desk drawer, left",
        "Fixture, Ellis",
        "Demo, Alex",
        "Yes",
        "No",
        "", "Unknown",
        "Bagged together"
    ),
    (
        "4",
        "1",
        "External hard drive, 2TB",
        "Portable-2T",
        "SN-0000004",
        "Room E (Detached Garage)",
        "Shelf above workbench",
        "Testcase, Devon",
        "Fixture, Ellis",
        "Yes",
        "No",
        "",
        "Unknown",
        ""
    ),
    (
        "5",
        "1",
        "Tablet computer, 10 inch",
        "Tab-10",
        "SN-0000005",
        "Room D (Second Bedroom)",
        "Under mattress",
        "Sample, Bailey",
        "Placeholder, Casey",
        "Yes",
        "Yes",
        "Placeholder, Casey",
        "No",
        ""
    ),
    (
        "6",
        "1",
        "Desktop tower, black",
        "Tower-500",
        "SN-0000006",
        "Room A (Living Room)",
        "Beneath television stand",
        "Demo, Alex",
        "Sample, Bailey",
        "Yes",
        "No",
        "",
        "Unknown",
        "Left in place, imaged"
    ),
    (
        "7",
        "2",
        "Memory cards, microSD",
        "",
        "",
        "Room B (Kitchen)",
        "Kitchen drawer, second from top",
        "Placeholder, Casey",
        "Testcase, Devon",
        "Yes",
        "No",
        "",
        "Unknown",
        ""
    ),
    (
        "8",
        "1",
        "Router, consumer grade",
        "Net-AC1200",
        "SN-0000008",
        "Room A (Living Room)",
        "Hall cupboard",
        "Sample, Bailey",
        "Demo, Alex",
        "Yes",
        "No",
        "",
        "N/A",
        "Configuration photographed"
    ),
    (
        "9",
        "1",
        "Notebook, spiral bound, handwritten",
        "",
        "",
        "Room C (Main Bedroom)",
        "Bedside table",
        "Fixture, Ellis",
        "Demo, Alex",
        "Yes",
        "No",
        "",
        "Unknown",
        "Contains handwritten notes"
    ),
    (
        "10",
        "1",
        "Games console",
        "Console-X",
        "SN-0000010",
        "Room D (Second Bedroom)",
        "Beside television",
        "Testcase, Devon",
        "Sample, Bailey",
        "Yes",
        "No",
        "",
        "Unknown",
        ""
    ),
    (
        "11",
        "3",
        "Optical discs, unlabelled",
        "",
        "",
        "Room E (Detached Garage)",
        "Cardboard box on floor",
        "Fixture, Ellis",
        "Testcase, Devon",
        "Yes",
        "No",
        "",
        "Unknown",
        ""
    ),
    (
        "12",
        "1",
        "Digital camera",
        "Cam-200",
        "SN-0000012",
        "Room C (Main Bedroom)",
        "Wardrobe, top shelf",
        "Demo, Alex",
        "Placeholder, Casey",
        "Yes",
        "Yes",
        "Placeholder, Casey",
        "Unknown",
        "Memory card seized as item 7"
    ),
]

DEMO_PERSONS = [
    (
        "Fictional, Jordan",
        "04-17-1985",
        "1 Example Way, Springfield",
        "555-0110",
        "Named on the warrant. Present at entry."
    ),
    (
        "Invented, Morgan",
        "11-02-1991",
        "1 Example Way, Springfield",
        "555-0111",
        "Resident. Cooperative throughout."
    ),
]

DEMO_NOTES = [
    (
        "09-01-2026 07:32:00",
        "Demo, Alex",
        "Entry made at 0730. Premises secured. Two occupants present and "
        "identified."
    ),
    (
        "09-01-2026 08:15:00",
        "Sample, Bailey",
        "Photographs taken of all rooms prior to search commencing."
    ),
    (
        "09-01-2026 11:40:00", "Placeholder, Casey",
        "Triage completed on items 1, 2, 5 and 12. No further action on "
        "item 5."
    ),
    (
        "09-01-2026 15:40:00",
        "Demo, Alex",
        "Search concluded. Property receipt provided to occupant. "
        "Twelve items seized."
    ),
]


def rebuild_case() -> None:
    """Clears the case tables and writes the demo case."""
    with get_session() as session:
        for model in (
            Cases,
            Agents,
            Rooms,
            Evidence,
            Persons,
            Notes,
            UploadedFiles,
        ):
            session.query(model).delete()

    with get_session() as session:
        session.add(Cases(**DEMO_CASE))

        for name, agency, role, second, phone, email in DEMO_AGENTS:
            session.add(
                Agents(
                    AGENTNAME=name,
                    AGENTPARENTAGENCY=agency,
                    AGENTPRIMARYROLE=role,
                    AGENTROLESECONDARY=second,
                    AGENTPHONE=phone,
                    AGENTEMAIL=email,
                    ENTEREDDATETIME=_scene_time("09-01-2026 07:35:00"),
                )
            )

        for label, desc, first, second in DEMO_ROOMS:
            session.add(
                Rooms(
                    ROOMLABEL=label,
                    ROOMDESC=desc,
                    ROOMFIRSTAGENT=first,
                    ROOMSECONDAGENT=second,
                    ENTEREDDATETIME=_scene_time("09-01-2026 07:50:00"),
                )
            )

        for item in DEMO_EVIDENCE:
            (
                num,
                qty,
                desc,
                model_no,
                serial,
                room,
                where,
                found_by,
                witness,
                photographed,
                triaged,
                triaged_by,
                contraband,
                note
            ) = item
            session.add(
                Evidence(
                    EVIDNUM=num,
                    EVIDQTY=qty,
                    EVIDDESC=desc,
                    EVIDMODELNUMBER=model_no,
                    EVIDSERIALNUMBER=serial,
                    EVIDLOCROOM=room,
                    EVIDLOCROOMDETAIL=where,
                    EVIDFOUNDBY=found_by,
                    EVIDFOUNDBYWITNESS=witness,
                    EVIDPICTAKEN=photographed,
                    EVIDTRIAGED=triaged,
                    EVIDTRIAGEDBY=triaged_by,
                    EVIDISCONTRABAND=contraband,
                    EVIDNOTE=note,
                    ENTEREDDATETIME=_scene_time("09-01-2026 09:00:00"),
                )
            )

        for name, dob, address, phone, note in DEMO_PERSONS:
            session.add(
                Persons(
                    PERSONNAME=name,
                    PERSONDOB=dob,
                    PERSONADDRESS=address,
                    PERSONPHONE=phone,
                    PERSONNOTE=note,
                    ENTEREDDATETIME=_scene_time("09-01-2026 08:05:00"),
                )
            )

        for when, author, text in DEMO_NOTES:
            session.add(
                Notes(
                    NOTEDATETIME=_scene_time(when),
                    NOTEDATETIMEUPDATED="",
                    NOTEAUTHOR=author,
                    NOTETEXT=text,
                )
            )


def reset_users() -> list:
    """Replaces the accounts with demo ones. Returns their passwords."""
    issued = []
    with get_users_session() as session:
        for user in session.query(Users).all():
            session.delete(user)

    with get_users_session() as session:
        for name, is_admin in (("admin", True), ("agent", False)):
            password = generate_one_time_password()
            user = Users(
                USERNAME=name,
                ISADMIN=is_admin,
                ISACTIVE=True,
                MUSTCHANGEPASSWORD=True,
            )
            user.set_password(password)
            session.add(user)
            issued.append((name, password, is_admin))
    return issued


def main() -> None:
    init_db()
    rebuild_case()

    with get_session() as session:
        record_audit(
            session,
            action="DEMO_SEED",
            table_name="(all case tables)",
            summary="fictional demo case loaded",
            actor="setup",
            after={"case": DEMO_CASE["CASENUMBER"], "at": audit_timestamp()},
        )

    print("Demo case loaded.")
    print(f"  Case      : {DEMO_CASE['CASENUMBER']}")
    print(f"  Agents    : {len(DEMO_AGENTS)}")
    print(f"  Rooms     : {len(DEMO_ROOMS)}")
    print(f"  Evidence  : {len(DEMO_EVIDENCE)} items")
    print(f"  People    : {len(DEMO_PERSONS)}")
    print(f"  Notes     : {len(DEMO_NOTES)}")
    print("  All names, addresses and numbers are fictional.")

    if "--users" in sys.argv:
        issued = reset_users()
        print("\n" + "  " + "=" * 62)
        print("  Accounts reset. These passwords are shown once.")
        print("  " + "=" * 62)
        for name, password, is_admin in issued:
            role = "admin" if is_admin else "standard"
            print(f"    {name:<8} ({role:<8})  {password}")
        print("  " + "=" * 62)
        print("  Each account must change its password at first sign-in.\n")


if __name__ == "__main__":
    main()
