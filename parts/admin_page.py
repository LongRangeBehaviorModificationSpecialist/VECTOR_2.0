#!/usr/bin/env python3

"""
admin_page.py

Admin panel for user management.

Only accessible to admin accounts. Manages users stored in
the separate users.db database file.
"""

from nicegui import ui

from models import get_users_session, Users, DEFAULT_USER_PASSWORD
from navbar import build_navbar
from main import get_current_user_name, get_is_admin


# ----- PAGE BUILDER -----
def build_admin_page() -> None:
    """Builds the Admin user management page."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=None,
    )

    with ui.column().classes("w-full items-center"):

        ui.label("User Administration").classes("text-2xl font-bold m-4")

        # ----- Add New User Card -----
        with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

            ui.label("Add New User").classes("text-lg font-semibold mb-4")

            ui.label(
                "New users are created with the default password and must "
                "change it on first login. (New users are never admins.)"
            ).classes("text-sm text-gray-400 mb-4")

            new_username = ui.input(label="Username").classes("w-full")

            def create_user() -> None:
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

                    new_user.set_password(DEFAULT_USER_PASSWORD)
                    session.add(new_user)

                ui.notify(
                    f"User '{uname}' created.\n"
                    f"Default password: {DEFAULT_USER_PASSWORD}\n"
                    f"They will be prompted to change it on first login.",
                    timeout=0,
                    position="bottom",
                    close_button="OK",
                )

                new_username.value = ""
                refresh_users_table()

            new_username.on("keydown.enter", create_user)

            ui.button(
                "Create User",
                on_click=create_user,
                color="var(--vsp-blue)",
            ).props("unelevated").classes("text-[var(--vsp-white)]")

        # ----- Existing Users Table -----
        ui.separator().classes("my-6")

        with ui.column().classes("w-full items-center"):

            ui.label("Registered Users").classes("text-xl font-bold mb-3")

            with ui.row().classes("w-fill max-w-6xl items-center"):

                table_container = ui.column().classes("w-full max-w-4xl")

                def refresh_users_table() -> None:
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

                        table.add_slot(
                            "body-cell-actions",
                            """
                            <q-td :props="props">
                                <div class="row no-wrap gap-1">
                                    <q-btn dense flat
                                    icon="refresh" size="sm"
                                    style="color: #2984D1;"
                                    title="Reset Password"
                                        @click="$parent.$emit('reset', \
                                        props.row)" />
                                    <q-btn dense flat color="negative"
                                    icon="delete" size="sm"
                                    style="color: #EF4444" \
                                    title="Delete User"
                                    :disable="props.row.ISADMIN === 'True'"
                                        @click="$parent.$emit('delete', \
                                        props.row)" />
                                </div>
                            </q-td>
                            """,
                        )

                        # ----- Reset password handler -----
                        def reset_password(e) -> None:

                            row = e.args

                            with ui.dialog() as reset_dialog, ui.card(
                                ).classes("max-w-sm p-6"
                            ):

                                ui.label("Reset Password").classes(
                                    "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                                )

                                ui.label(
                                    f"Reset the password for "
                                    f"{row['USERNAME']} back "
                                    f"to the default?  They will be prompted "
                                    f"to change it on next login."
                                ).classes("mb-4 text-sm text-[var(--vsp-gray)]")

                                with ui.row().classes(
                                    "w-full justify-end gap-2"
                                ):

                                    ui.button(
                                        "Cancel",
                                        on_click=reset_dialog.close,
                                        color="transparent").props("flat"
                                    ).classes("text-[var(--vsp-blue)]")

                                    def on_confirm_reset() -> None:

                                        with get_users_session() as session:

                                            user = (
                                                session.query(Users)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )

                                            if user:
                                                user.set_password(
                                                    DEFAULT_USER_PASSWORD
                                                )
                                                user.MUSTCHANGEPASSWORD = True

                                        ui.notify(
                                            f"Password for "
                                            f"\"{row['USERNAME']}\" reset to "
                                            "default.\n"
                                            f"Default password: "
                                            f"{DEFAULT_USER_PASSWORD}",
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
                                        color="var(--vsp-blue)"
                                    ).props(
                                        "unelevated"
                                    ).classes("text-[var(--vsp-white)]")

                            reset_dialog.open()

                        # ----- Delete user handler -----
                        def delete_user(e) -> None:

                            row = e.args

                            if row["ISADMIN"] == "Yes":

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
                                    "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                                )

                                ui.label(
                                    f"Are you sure you want to delete user "
                                    f"\"{row['USERNAME']}\"? This cannot be "
                                    "undone."
                                ).classes("mb-4")

                                with ui.row().classes(
                                    "w-full justify-end gap-2"
                                ):

                                    ui.button(
                                        "Cancel",
                                        on_click=delete_dialog.close,
                                        color="transparent").props("flat"
                                    ).classes("text-[var(--vsp-blue)]")

                                    def on_confirm_delete() -> None:

                                        with get_users_session() as session:

                                            user = (
                                                session.query(Users)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )

                                            if user:
                                                session.delete(user)

                                        ui.notify(
                                            f"User \"{row['USERNAME']}\" "
                                            "deleted.",
                                            timeout=4000,
                                            position="bottom",
                                            close_button="OK",
                                        )

                                        delete_dialog.close()
                                        refresh_users_table()

                                    ui.button(
                                        "Delete",
                                        on_click=on_confirm_delete,
                                        color="#EF4444",
                                    ).props("unelevated").classes(
                                        "text-[var(--vsp-white)]"
                                    )

                            delete_dialog.open()

                        table.on("reset", reset_password)
                        table.on("delete", delete_user)

    # Initial render
    refresh_users_table()
