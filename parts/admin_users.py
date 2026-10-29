#!/usr/bin/env python3

"""
admin_users.py

The three parts of the Admin Panel: the card that creates an account,
the table of accounts with its reset, unlock and delete dialogs, and the
control that ends every session at once.

They were one 545-line function, in which the card called a refresh
function defined two hundred lines further down and the delete dialog
sat four levels of indentation deep. Each part is its own function here,
and the card is handed the refresh rather than reaching for it.

parts/admin_page.py draws the page from these; nothing else uses them.
"""

from typing import Callable

from nicegui import ui

from auth import (
    clear_login_failures,
    get_current_user_name,
    get_is_admin,
    invalidate_all_sessions,
    invalidate_user_sessions,
    lockout_seconds_remaining,
)
from models import (
    generate_one_time_password,
    get_session,
    get_users_session,
    record_account_event,
    record_audit,
    Users,
)
import settings
from failures import explain, log
from utils import (
    CONFIRM_TIMEOUT,
    WARN_TIMEOUT,
    ZERO_TIMEOUT,
    delete_all_data,
    get_case_info,
    set_network_access,
)


# ----- Add an account -----
def add_user_card(refresh_users: Callable[[], None]) -> None:
    """The card that creates an account and shows its one-time password.

    refresh_users redraws the table below, which does not exist yet when
    this is drawn.
    """
    with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

        ui.label("Add New User").classes("text-lg font-semibold mb-4")

        ui.label(
            "A one-time password is generated and shown once. Write it "
            "down before closing the message -- it cannot be recovered. "
            "New users are never admins."
        ).classes("text-sm text-gray-400 mb-4")

        new_username = ui.input(label="Username").classes("w-full")

        def create_user():

            if not get_is_admin():
                ui.navigate.to("/")
                return

            uname = new_username.value.strip()

            # ----- Validation -----
            if not uname:
                ui.notify(
                    "A username is required.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return

            with get_users_session() as session:
                if session.query(Users).filter_by(USERNAME=uname).first():
                    ui.notify(
                        "That username already exists.",
                        type="warning",
                        timeout=WARN_TIMEOUT,
                        position="center",
                        close_button="OK",
                    )
                    return

                new_user = Users(
                    USERNAME=uname,
                    ISADMIN=False,
                    ISACTIVE=True,
                    MUSTCHANGEPASSWORD=True,
                )

                one_time = generate_one_time_password()
                new_user.set_password(one_time)
                session.add(new_user)
                session.flush()
                new_pk = new_user.Z_PK

            record_account_event(
                action="USER_CREATED",
                row_pk=new_pk,
                summary=f"{uname} (not an admin; must change password)",
                actor=get_current_user_name(),
            )

            with ui.dialog() as confirm_user_dialog, ui.card(
                ).classes("max-w-md p-6"
            ):
                ui.label("New User Created").classes(
                    "mb-2 text-xl font-bold text-[var(--vsp-blue)]")

                with ui.row().classes("w-full mb-2"):
                    ui.label(
                        "User created successfully :"
                    ).classes("text-base")
                    ui.label(f"{uname}").classes(
                        "text-base font-semibold text-[#F5B027]")

                with ui.row().classes("w-full mb-2"):
                    ui.label(
                        f"New user's one-time password :"
                    ).classes("text-base")
                    ui.label(f"{one_time}").classes(
                            "text-base font-semibold text-[#F5B027]"
                        )

                ui.label(
                    "This password is only shown once and cannot be recovered. "
                    "They will be asked to change it at first sign-in."
                ).classes("mb-6 text-base text-[var(--vsp-gray)]")

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button(
                        "Okay",
                        on_click=confirm_user_dialog.close,
                        color="var(--vsp-blue)",
                    ).props("push").classes("w-25 p-3 hover-border-white")

            confirm_user_dialog.open()

            new_username.value = ""
            refresh_users()

        new_username.on("keydown.enter", create_user)

        ui.button(
            "Create User",
            on_click=create_user,
            color="var(--vsp-blue)",
        ).props("push").classes("p-3 hover-border-white")


# ----- The accounts -----
def users_table() -> Callable[[], None]:
    """Draws the table of accounts, and returns the function that redraws it.

    Resetting a password, clearing a lock and deleting an account each
    ask first; those dialogs live here, with the table they act on.
    """
    ui.separator().classes("my-6")

    with ui.column().classes("w-full items-center"):

        ui.label("Registered Users").classes("text-xl font-bold mb-3")

        with ui.row().classes("w-fill max-w-6xl items-center"):

            table_container = ui.column().classes("w-full max-w-4xl")

            def refresh_users_table():
                """Re-renders the users table from users.db."""
                table_container.clear()

                with get_users_session() as session:
                    users = (
                        session.query(Users)
                        .order_by(Users.USERNAME)
                        .all()
                    )
                    rows = [
                        {
                            "Z_PK": u.Z_PK,
                            "USERNAME": u.USERNAME,
                            "ISADMIN": "True" if u.ISADMIN else "False",
                            "ISACTIVE": "True" if u.ISACTIVE else "False",
                            "MUSTCHANGEPASSWORD": (
                                "True" if u.MUSTCHANGEPASSWORD else "False"
                            ),
                            "locked": (
                                "LOCKED"
                                if lockout_seconds_remaining(u.USERNAME)
                                else ""
                            ),
                        }
                        for u in users
                    ]

                with table_container:
                    columns = [
                        {
                            "name": "Z_PK",
                            "label": "User ID",
                            "field": "Z_PK",
                            "sortable": True,
                            "align": "left",
                        },
                        {
                            "name": "USERNAME",
                            "label": "Username",
                            "field": "USERNAME",
                            "sortable": True,
                            "align": "left",
                        },
                        {
                            "name": "ISADMIN",
                            "label": "Admin",
                            "field": "ISADMIN",
                            "align": "left",
                        },
                        {
                            "name": "ISACTIVE",
                            "label": "Active",
                            "field": "ISACTIVE",
                            "align": "left",
                        },
                        {
                            "name": "MUSTCHANGEPASSWORD",
                            "label": "Must Change PW",
                            "field": "MUSTCHANGEPASSWORD",
                            "align": "left",
                        },
                        {
                            "name": "locked",
                            "label": "Sign-in",
                            "field": "locked",
                            "align": "left",
                        },
                        {
                            "name": "actions",
                            "label": "Actions",
                            "field": "actions",
                            "align": "center",
                        },
                    ]

                    table = ui.table(
                        columns=columns,
                        rows=rows,
                        row_key="Z_PK",
                    )

                    table.props("dense flat")

                    # A locked account has to be obvious: an agent
                    # who cannot sign in mid-search will ask an
                    # admin, and this is what the admin looks at.
                    table.add_slot(
                        "body-cell-locked",
                        """
                        <q-td :props="props">
                            <span v-if="props.row.locked"
                                class="text-red-500"
                                style="font-weight:600">
                                {{ props.row.locked }}
                            </span>
                            <span v-else class="text-green-500">OK</span>
                        </q-td>
                        """,
                    )

                    table.add_slot(
                        "body-cell-actions",
                        """
                        <q-td :props="props">
                            <div class="row no-wrap gap-1">
                                <q-btn dense flat
                                color="warning" \
                                icon="refresh"
                                size="sm"
                                style="color: #2984D1;"
                                title="Reset Password"
                                    @click="$parent.$emit('reset', \
                                    props.row)" />
                                <q-btn dense flat
                                    icon="lock_open"
                                    size="sm"
                                    style="color: #F59E0B;"
                                    title="Clear sign-in lock"
                                    :disable="!props.row.locked"
                                    @click="$parent.$emit('unlock', \
                                    props.row)" />
                                <q-btn dense flat color="negative" \
                                icon="delete"
                                    size="sm"
                                    title="Delete User"
                                    :disable="props.row.ISADMIN === 'True'"
                                    @click="$parent.$emit('delete', \
                                    props.row)" />
                            </div>
                        </q-td>
                        """,
                    )

                    # ----- Reset password handler -----
                    def reset_password(e):

                        row = e.args

                        with ui.dialog() as reset_dialog, ui.card(
                            ).classes("max-w-sm p-6"
                        ):

                            ui.label("Reset Password").classes(
                                "mb-3 text-lg font-semibold "
                                "text-[var(--vsp-blue)]"
                            )
                            ui.label(
                                f"Generate a new one-time password for "
                                f"{row['USERNAME']}?"
                            ).classes("mb-2")
                            ui.label(
                                "Their current password stops working "
                                "immediately and any session they have "
                                "open is ended. The new password is "
                                "shown once."
                            ).classes("mb-4 text-xs text-gray-400")

                            with ui.row().classes(
                                "w-full justify-end gap-2"
                            ):
                                ui.button(
                                    "Cancel",
                                    on_click=reset_dialog.close,
                                    color="transparent",
                                    ).props("flat").classes(
                                    "p-3 hover-border-blue"
                                )

                                def on_confirm_reset():

                                    if not get_is_admin():
                                        reset_dialog.close()
                                        ui.navigate.to("/")
                                        return

                                    with get_users_session() as session:
                                        user = (
                                            session.query(Users)
                                            .filter_by(Z_PK=row["Z_PK"])
                                            .first()
                                        )
                                        one_time = None
                                        if user:
                                            one_time = (
                                                generate_one_time_password()
                                            )
                                            user.set_password(one_time)
                                            user.MUSTCHANGEPASSWORD = True

                                    if one_time is None:
                                        # Deleted on another device while
                                        # this dialog was open.
                                        ui.notify(
                                            f"'{row['USERNAME']}' no longer "
                                            "exists, so nothing was reset.",
                                            type="warning",
                                            timeout=WARN_TIMEOUT,
                                            position="center",
                                            close_button="OK",
                                        )
                                        reset_dialog.close()
                                        refresh_users_table()
                                        return

                                    # A reset that leaves the old
                                    # session working is not a reset.
                                    ended = invalidate_user_sessions(
                                        row["USERNAME"]
                                    )
                                    clear_login_failures(row["USERNAME"])
                                    record_account_event(
                                        action="PASSWORD_RESET",
                                        row_pk=row["Z_PK"],
                                        summary=(
                                            f"{row['USERNAME']}: a new "
                                            "one-time password, sessions "
                                            + (
                                                "ended" if ended else
                                                "NOT ended"
                                            )
                                        ),
                                        actor=get_current_user_name(),
                                    )

                                    ui.notify(
                                        f"Password for "
                                        f"'{row['USERNAME']}' reset.\n\n"
                                        f"One-time password:  "
                                        f"{one_time}\n\n"
                                        "Shown once, and cannot be recovered."
                                        + (
                                            "Any session they had open "
                                            "has been ended."
                                            if ended else
                                            "Their open sessions could "
                                            "NOT be ended; use Sign "
                                            "Everyone Out below."
                                        ),
                                        multi_line=True,
                                        type="warning",
                                        timeout=WARN_TIMEOUT,
                                        position="center",
                                        close_button="OK",
                                    )

                                    reset_dialog.close()
                                    refresh_users_table()

                                ui.button(
                                    "Reset",
                                    on_click=on_confirm_reset,
                                    color="var(--vsp-blue)",
                                    ).props("push").classes(
                                    "p-3 hover-border-white"
                                )

                        reset_dialog.open()

                    # ----- Delete user handler -----
                    def delete_user(e):

                        row = e.args

                        if row["ISADMIN"] == "True":

                            ui.notify(
                                "Cannot delete the admin account.",
                                type="warning",
                                timeout=WARN_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return

                        with ui.dialog() as delete_dialog, ui.card(
                            ).classes("max-w-sm p-6"
                        ):

                            ui.label("Confirm Deletion").classes(
                                "mb-3 text-lg font-semibold "
                                "text-[var(--vsp-blue)]"
                            )
                            ui.label(
                                f"Are you sure you want to delete user "
                                f"'{row['USERNAME']}'? This cannot be "
                                "undone."
                            ).classes("mb-4")

                            with ui.row().classes(
                                "w-full justify-end gap-2"
                            ):
                                ui.button(
                                    "Cancel",
                                    on_click=delete_dialog.close,
                                    color="transparent",
                                    ).props("flat"
                                ).classes("p-3 hover-border-blue")

                                def on_confirm_delete():

                                    if not get_is_admin():
                                        delete_dialog.close()
                                        ui.navigate.to("/")
                                        return

                                    with get_users_session() as session:
                                        user = (
                                            session.query(Users)
                                            .filter_by(Z_PK=row["Z_PK"])
                                            .first()
                                        )

                                        # Admin status comes from the
                                        # database, never from the row
                                        # payload the browser sent.
                                        if user and user.ISADMIN:
                                            ui.notify(
                                                "Cannot delete an admin "
                                                "account.",
                                                type="warning",
                                                timeout=WARN_TIMEOUT,
                                                position="center",
                                                close_button="OK",
                                            )
                                            delete_dialog.close()
                                            return

                                        deleted = user is not None
                                        if user:
                                            session.delete(user)

                                    # Otherwise the deleted account
                                    # keeps working until its browser
                                    # is closed.
                                    ended = invalidate_user_sessions(
                                        row["USERNAME"]
                                    )

                                    clear_login_failures(row["USERNAME"])

                                    if deleted:
                                        record_account_event(
                                            action="USER_DELETED",
                                            row_pk=row["Z_PK"],
                                            summary=(
                                                f"{row['USERNAME']}, "
                                                "sessions "
                                                + (
                                                    "ended" if ended else
                                                    "NOT ended"
                                                )
                                            ),
                                            actor=get_current_user_name(),
                                        )

                                    ui.notify(
                                        f"User \"{row['USERNAME']}\" "
                                        "deleted."
                                        + (
                                            "" if ended else
                                            " Their open sessions could "
                                            "NOT be ended; use Sign "
                                            "Everyone Out below."
                                        ),
                                        timeout=(
                                            CONFIRM_TIMEOUT
                                            if ended else 0
                                        ),
                                        position="bottom",
                                        close_button="OK",
                                    )

                                    delete_dialog.close()
                                    refresh_users_table()

                                ui.button(
                                    "Delete",
                                    on_click=on_confirm_delete,
                                    color="#ef4444",
                                    ).props("push").classes(
                                    "p-3 hover-border-white"
                                )

                        delete_dialog.open()

                    def unlock_user(e) -> None:
                        """Clears a sign-in lock immediately."""
                        row = e.args
                        if not get_is_admin():
                            ui.navigate.to("/")
                            return

                        clear_login_failures(row["USERNAME"])
                        record_account_event(
                            action="LOCK_CLEARED",
                            row_pk=row["Z_PK"],
                            summary=row["USERNAME"],
                            actor=get_current_user_name(),
                        )
                        ui.notify(
                            f"Sign-in lock cleared for "
                            f"'{row['USERNAME']}'.",
                            timeout=CONFIRM_TIMEOUT,
                            position="bottom",
                            close_button="OK",
                        )
                        refresh_users_table()

                    table.on("reset", reset_password)
                    table.on("delete", delete_user)
                    table.on("unlock", unlock_user)

    return refresh_users_table


# ----- Sessions -----
def session_controls() -> None:
    """Sign Everyone Out, with the warning it warrants."""
    ui.separator().classes("my-6")

    with ui.column().classes("w-full items-center mb-8"):

        ui.label("Sessions").classes("text-xl font-bold mb-2")

        ui.label(
            "Ends every signed-in session, on every device, at once.  "
            "Everyone signs in again. Nothing else is affected."
        ).classes("text-sm text-gray-400 mb-3 text-center max-w-lg")

        def open_sign_out_all_dialog() -> None:
            with ui.dialog() as dialog, ui.card().classes("max-w-sm p-6"):
                ui.label("Sign everyone out?").classes(
                    "text-lg font-bold mb-2 text-[var(--vsp-blue)]"
                )
                ui.label(
                    "Every open session ends immediately, including "
                    "yours. Unsaved form entries on other devices will "
                    "be lost."
                ).classes("mb-4 text-[var(--vsp-gray)]")

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button(
                        "Cancel",
                        on_click=dialog.close,
                        color="transparent",
                    ).props("flat").classes("p-3 hover-border-blue")

                    def confirm_sign_out_all() -> None:
                        if not get_is_admin():
                            ui.navigate.to("/")
                            return
                        # Named before the sessions end: this admin's own
                        # ends with them.
                        admin_name = get_current_user_name()
                        if not invalidate_all_sessions():
                            ui.notify(
                                "The sessions could NOT be ended. The "
                                "details are in the VECTOR console "
                                "window.",
                                type="warning",
                                timeout=ZERO_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            dialog.close()
                            return

                        record_account_event(
                            action="SIGN_OUT_ALL",
                            table_name="(session)",
                            summary="every session on every device ended",
                            actor=admin_name,
                        )
                        dialog.close()
                        ui.navigate.to("/")

                    ui.button(
                        "Sign Everyone Out",
                        on_click=confirm_sign_out_all,
                        color="#ef4444",
                    ).props("push").classes(
                        "p-3 hover-border-white"
                    )

            dialog.open()

        ui.button(
            "Sign Everyone Out",
            on_click=open_sign_out_all_dialog,
            color="#ef4444",
        ).props("push").classes("p-3 hover-border-white")


# ----- Network access -----
def network_access_card() -> None:
    """The switch that decides whether other devices can reach this
    machine, with a plain statement of what is true right now.

    It cannot take effect until VECTOR restarts, so it says so rather
    than implying the switch did something immediately.
    """
    with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

        ui.label("Network Access").classes(
            "text-lg font-semibold mb-2 text-[var(--vsp-blue)]")

        if settings.reachable_now():
            addresses = settings.addresses_for_other_devices()
            where = (
                f"The address to give them is {addresses[0]} -- "
                "Help -> Connect a Device has more."
                if addresses else
                "The address to give them is on the Connect a Device page."
            )
            ui.label(
                "Right now, other devices on this network can reach "
                f"VECTOR. {where}"
            ).classes("text-sm text-[#F5B027] mb-3")
        else:
            ui.label(
                "Right now, VECTOR is answering on this machine only."
            ).classes("text-sm text-[var(--vsp-gray)] mb-3")

        switch = ui.switch(
            "Let other devices on this network reach VECTOR",
            value=settings.network_access(),
        ).classes("text-sm")

        ui.label(
            "Takes effect the next time VECTOR starts. Nothing changes "
            "until then -- a listening port cannot be moved."
        ).classes("text-xs text-gray-400 mt-2")

        ui.label(
            "Traffic is unencrypted HTTP, so turn this on only for a "
            "network you control. With it off the port is not on the "
            "network at all: the connection is refused before VECTOR "
            "sees it."
        ).classes("text-xs text-gray-400 mt-1")

        def on_change(event) -> None:
            if not get_is_admin():
                ui.navigate.to("/")
                return

            allowed = bool(event.value)
            set_network_access(allowed, get_current_user_name())

            ui.notify(
                ("Other devices will be able to reach VECTOR "
                if allowed else
                "VECTOR will answer on this machine only ")
                + "the next time it starts.",
                type="info",
                timeout=ZERO_TIMEOUT,
                position="center",
                close_button="OK",
            )

        switch.on_value_change(on_change)


# ----- Training -----
def load_demo_case(actor: str = "") -> str:
    """Replaces the case with the made-up demo one, for practice. Returns
    the demo's case number.

    The case is cleared the usual way first, so the wipe is in the audit
    trail like any other, and then the loading is. Accounts and the agent
    list (parts/agents.json) are not touched.
    """
    from tools import make_demo_case as demo

    delete_all_data()
    demo.rebuild_case()
    with get_session() as session:
        record_audit(
            session,
            action="DEMO_SEED",
            table_name="(all case tables)",
            summary="fictional demo case loaded for training",
            actor=actor or None,
            after={"case": demo.DEMO_CASE["CASENUMBER"]},
        )
    return demo.DEMO_CASE["CASENUMBER"]


def training_card() -> None:
    """A made-up search to practise on, a button away."""
    with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

        ui.label("Training").classes("text-lg font-semibold mb-2")

        ui.label(
            "Loads a made-up search to practise on: a case with items, "
            "rooms, agents, people and notes, every name and number "
            "invented. It replaces the case on this computer. Accounts and "
            "the agent list are not touched."
        ).classes("text-sm text-gray-400 mb-3")

        def open_dialog() -> None:
            case = get_case_info()

            with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):
                ui.label("Load the demo case?").classes(
                    "text-lg font-bold mb-2 text-[var(--vsp-blue)]"
                )

                confirm = None
                if case:
                    ui.label(
                        f"Case {case['CASENUMBER']} is open on this "
                        "computer. Loading the demo DELETES it and "
                        "everything recorded against it. Export it first "
                        "if you need it."
                    ).classes("text-sm text-[#F5B027] mb-3")
                    confirm = ui.input(
                        label="TYPE DEMO TO CONFIRM",
                    ).classes("w-full yellow-label mb-3")
                else:
                    ui.label(
                        "No case is open, so nothing is lost."
                    ).classes("text-sm mb-3")

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button(
                        "Cancel",
                        on_click=dialog.close,
                        color="transparent",
                    ).props("flat").classes("p-3 hover-border-blue")

                    def load() -> None:
                        if not get_is_admin():
                            dialog.close()
                            ui.navigate.to("/")
                            return
                        if confirm is not None and (
                            (confirm.value or "").strip() != "DEMO"
                        ):
                            ui.notify(
                                "Type DEMO, in capital letters, to confirm.",
                                type="warning",
                                timeout=WARN_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return
                        dialog.close()
                        try:
                            number = load_demo_case(get_current_user_name())
                        except Exception as err:
                            log.exception("Could not load the demo case")
                            ui.notify(
                                "The demo case could not be loaded."
                                f"\n\n{explain(err)}",
                                multi_line=True,
                                classes="multi-line-notification",
                                type="warning",
                                timeout=ZERO_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return
                        ui.notify(
                            f"Demo case {number} loaded. Everything in it "
                            "is made up.",
                            timeout=CONFIRM_TIMEOUT,
                            position="bottom",
                            close_button="OK",
                        )
                        ui.navigate.to("/")

                    ui.button(
                        "Load demo case",
                        on_click=load,
                        color="#ef4444" if case else "var(--vsp-blue)",
                    ).props("push").classes("p-3 hover-border-white")

            dialog.open()

        ui.button(
            "Load the demo case",
            icon="school",
            on_click=open_dialog,
            color="var(--vsp-blue)",
        ).props("push").classes("p-3 hover-border-white")
