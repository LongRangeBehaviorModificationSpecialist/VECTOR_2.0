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
    get_is_admin,
    invalidate_all_sessions,
    invalidate_user_sessions,
    lockout_seconds_remaining,
)
from models import get_users_session, Users, generate_one_time_password


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
                    timeout=0,
                    position="center",
                    close_button="OK",
                )
                return

            with get_users_session() as session:

                if session.query(Users).filter_by(USERNAME=uname).first():

                    ui.notify(
                        "That username already exists.",
                        type="negative",
                        timeout=0,
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

            ui.notify(
                f"User '{uname}' created.\n\n"
                f"One-time password:  {one_time}\n\n"
                "This is shown once and cannot be recovered. They "
                "will be asked to change it at first sign-in.",
                multi_line=True,
                classes="multi-line-notification",
                timeout=0,
                position="center",
                close_button="OK",
            )

            new_username.value = ""
            refresh_users()

        new_username.on("keydown.enter", create_user)

        ui.button(
            "Create User",
            on_click=create_user,
            color="var(--vsp-blue)",
        ).props("push").classes("text-[var(--vsp-white)]")


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
                                <q-btn dense flat color="warning" \
                                icon="refresh" size="sm"
                                style="color: #2984D1;"
                                title="Reset Password"
                                    @click="$parent.$emit('reset', \
                                    props.row)" />
                                <q-btn dense flat icon="lock_open"
                                    size="sm"
                                    style="color: #F59E0B;"
                                    title="Clear sign-in lock"
                                    :disable="!props.row.locked"
                                    @click="$parent.$emit('unlock', \
                                    props.row)" />
                                <q-btn dense flat color="negative" \
                                icon="delete"
                                    size="sm" title="Delete User"
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
                                    "text-[var(--vsp-blue)]"
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

                                        if user:
                                            one_time = (
                                                generate_one_time_password()
                                            )
                                            user.set_password(one_time)
                                            user.MUSTCHANGEPASSWORD = True

                                    # A reset that leaves the old
                                    # session working is not a reset.
                                    ended = invalidate_user_sessions(
                                        row["USERNAME"]
                                    )
                                    clear_login_failures(row["USERNAME"])

                                    ui.notify(
                                        f"Password for "
                                        f"'{row['USERNAME']}' reset.\n\n"
                                        f"One-time password:  "
                                        f"{one_time}\n\n"
                                        "Shown once, and cannot be "
                                        "recovered. "
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
                                        timeout=0,
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
                                    "text-[var(--vsp-white)]"
                                )

                        reset_dialog.open()

                    # ----- Delete user handler -----
                    def delete_user(e):

                        row = e.args

                        if row["ISADMIN"] == "True":

                            ui.notify(
                                "Cannot delete the admin account.",
                                type="negative",
                                timeout=0,
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
                                ).classes("text-[var(--vsp-blue)]")

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
                                                type="negative",
                                                timeout=0,
                                                position="center",
                                                close_button="OK",
                                            )
                                            delete_dialog.close()
                                            return

                                        if user:
                                            session.delete(user)

                                    # Otherwise the deleted account
                                    # keeps working until its browser
                                    # is closed.
                                    ended = invalidate_user_sessions(
                                        row["USERNAME"]
                                    )
                                    clear_login_failures(row["USERNAME"])

                                    ui.notify(
                                        f"User \"{row['USERNAME']}\" "
                                        "deleted."
                                        + (
                                            "" if ended else
                                            " Their open sessions could "
                                            "NOT be ended; use Sign "
                                            "Everyone Out below."
                                        ),
                                        timeout=4000 if ended else 0,
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
                                    "text-[var(--vsp-white)]"
                                )

                        delete_dialog.open()

                    def unlock_user(e) -> None:
                        """Clears a sign-in lock immediately."""
                        row = e.args
                        if not get_is_admin():
                            ui.navigate.to("/")
                            return

                        clear_login_failures(row["USERNAME"])
                        ui.notify(
                            f"Sign-in lock cleared for "
                            f"'{row['USERNAME']}'.",
                            timeout=4000,
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
            "Ends every signed-in session, on every device, at once. "
            "Everyone signs in again; nothing else is affected."
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
                    ).props("flat").classes("text-[var(--vsp-blue)]")

                    def confirm_sign_out_all() -> None:
                        if not get_is_admin():
                            ui.navigate.to("/")
                            return
                        if not invalidate_all_sessions():
                            ui.notify(
                                "The sessions could NOT be ended. The "
                                "details are in the VECTOR console "
                                "window.",
                                type="negative",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            dialog.close()
                            return
                        dialog.close()
                        ui.navigate.to("/")

                    ui.button(
                        "Sign Everyone Out",
                        on_click=confirm_sign_out_all,
                        color="#ef4444",
                    ).props("push").classes(
                        "text-[var(--vsp-white)]"
                    )

            dialog.open()

        ui.button(
            "Sign Everyone Out",
            on_click=open_sign_out_all_dialog,
            color="#ef4444",
        ).props("push")
