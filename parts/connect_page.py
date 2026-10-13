#!/usr/bin/env python3

"""
connect_page.py

What to type on the other device.

Getting a tablet onto the case means knowing this machine's address,
which is not something anyone should have to find with ipconfig at a
scene. This page says whether VECTOR is reachable at all, and if it is,
the address to type -- one address, on the network this computer is on,
rather than every adapter it has. Virtual adapters (VMware, Hyper-V, WSL,
VPNs) each have an address too, and none of them is reachable from a
tablet; they are listed apart, for whoever is troubleshooting.
"""

from nicegui import ui

from auth import get_current_user_name, get_is_admin, is_authenticated
from navbar import build_navbar
from program.config import Config
import settings


_KIND_NOTES = {
    settings.MAIN: "the network this computer is connected to",
    settings.HOTSPOT: "this computer's own hotspot",
    settings.OTHER: "another network adapter on this computer",
    settings.VIRTUAL: "a virtual adapter -- other devices cannot reach it",
}


def _address_line(item, size: str = "text-base") -> None:
    """One address, with the adapter it belongs to."""
    with ui.column().classes("gap-0 mb-2"):
        ui.label(item.url).classes(
            f"{size} font-mono text-[var(--vsp-blue)]"
        )
        detail = _KIND_NOTES[item.kind]
        if item.adapter:
            detail = f"{item.adapter} -- {detail}"
        ui.label(detail).classes("text-xs text-gray-400")


def build_connect_page() -> None:
    """Shows the address another device should open."""

    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(is_admin=get_is_admin(), username=get_current_user_name())

    with ui.column().classes("w-full items-center"):

        ui.label("Connect a Device").classes("text-2xl font-bold m-4")

        reachable = settings.reachable_now()
        everything = settings.network_addresses()
        usable = [a for a in everything if a.kind != settings.VIRTUAL]

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

            elif not usable:
                ui.label(
                    "VECTOR is on the network, but this machine has no "
                    "network address"
                ).classes("text-lg font-bold text-[#F5B027] mb-2")

                ui.label(
                    "Check that it is connected to Wi-Fi or plugged in, "
                    "then open this page again."
                ).classes("text-sm text-[var(--vsp-gray)]")

            else:
                best, rest = usable[0], usable[1:]

                ui.label(
                    "On the other device, open a browser and type:"
                ).classes("text-sm text-[var(--vsp-gray)] mb-2")
                _address_line(best, size="text-xl")

                hotspots = [a for a in rest if a.kind == settings.HOTSPOT]
                if hotspots:
                    ui.label(
                        "If the tablet has joined this computer's own "
                        "hotspot instead:"
                    ).classes("text-sm text-[var(--vsp-gray)] mt-2 mb-1")
                    for item in hotspots:
                        _address_line(item)

                others = [a for a in rest if a.kind == settings.OTHER]
                if others:
                    ui.label(
                        "If that does not open, the tablet may be on a "
                        "different network from this computer -- Wi-Fi "
                        "rather than a cable, say. Try:"
                    ).classes("text-sm text-[var(--vsp-gray)] mt-2 mb-1")
                    for item in others:
                        _address_line(item)

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

            # Every address, for whoever is working out why one does not
            # open. Virtual adapters are why a computer has so many.
            if reachable and len(everything) > len(usable[:1]):
                with ui.expansion(
                    f"Every address on this computer ({len(everything)})"
                ).classes("w-full mt-3 text-sm"):
                    ui.label(
                        "Each network adapter has its own address. "
                        "VMware, Hyper-V, WSL, Docker and VPN adapters are "
                        "networks inside this computer: a tablet cannot "
                        "reach them."
                    ).classes("text-xs text-gray-400 mb-2")
                    for item in everything:
                        _address_line(item, size="text-sm")
