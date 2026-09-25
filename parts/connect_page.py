#!/usr/bin/env python3

"""
connect_page.py

What to type on the other device.

Getting a tablet onto the case means knowing this machine's address,
which is not something anyone should have to find with ipconfig at a
scene. This page says whether VECTOR is reachable at all, and if it is,
the exact address to type.
"""

from nicegui import ui

from auth import get_current_user_name, get_is_admin, is_authenticated
from navbar import build_navbar
from program.config import Config
import settings


def build_connect_page() -> None:
    """Shows the address another device should open."""

    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(is_admin=get_is_admin(), username=get_current_user_name())

    with ui.column().classes("w-full items-center"):

        ui.label("Connect a Device").classes("text-2xl font-bold m-4")

        reachable = settings.reachable_now()
        addresses = settings.addresses_for_other_devices()

        with ui.card().classes("w-full max-w-2xl p-6"):

            if not reachable:
                ui.label(
                    "VECTOR is not on the network"
                ).classes("text-lg font-bold text-[#F5B027] mb-2")

                ui.label(
                    "It is answering on this machine only, so nothing "
                    "else can reach it. An administrator can turn "
                    "network access on in the Admin Panel; it takes "
                    "effect the next time VECTOR starts."
                ).classes("text-sm text-[var(--vsp-gray)] mb-2")

                if not get_is_admin():
                    ui.label(
                        "Ask whoever administers this machine."
                    ).classes("text-sm text-[var(--vsp-gray)]")

            elif not addresses:
                ui.label(
                    "VECTOR is on the network, but this machine has no "
                    "network address"
                ).classes("text-lg font-bold text-[#F5B027] mb-2")

                ui.label(
                    "Check that it is connected to Wi-Fi or plugged in, "
                    "then open this page again."
                ).classes("text-sm text-[var(--vsp-gray)]")

            else:
                ui.label(
                    "On the other device, open a browser and type:"
                ).classes("text-sm text-[var(--vsp-gray)] mb-2")

                for address in addresses:
                    ui.label(address).classes(
                        "text-xl font-mono text-[var(--vsp-blue)] mb-1"
                    )

                if len(addresses) > 1:
                    ui.label(
                        "This machine has more than one network "
                        "address. Try them in order; the first is "
                        "usually the one."
                    ).classes("text-xs text-gray-400 mb-2")

                ui.separator().classes("my-3")

                ui.label("Three things that catch people out:").classes(
                    "text-sm font-semibold mb-1"
                )
                for line in (
                    "Type the whole address, including http:// and "
                    f":{Config.PORT}. A browser treats "
                    "the number on its own as something to search for.",
                    "Both devices have to be on the same network. A "
                    "guest network usually cannot reach this one.",
                    "It is http, not https. There is no certificate, "
                    "and the traffic is not encrypted -- use this only "
                    "on a network you control.",
                ):
                    ui.label(f"- {line}").classes(
                        "text-sm text-[var(--vsp-gray)] mb-1"
                    )

                ui.label(
                    "Sign in on the other device as usual. It is the "
                    "same case: an entry made there appears here within "
                    "a couple of seconds."
                ).classes("text-sm text-[var(--vsp-gray)] mt-3")
