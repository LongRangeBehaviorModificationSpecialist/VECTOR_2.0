#!/usr/bin/env python3

"""
links_page.py

Displays categorized useful links in collapsible sections.
No form needed — this is a read-only resource page.
"""

from nicegui import ui

from navbar import build_navbar
from home_page import confirm_new_case_handler
from main import get_current_user_name, get_is_admin

# ----- Link Data -----
starter_links = {
    "Mike's Useful Links": "https://start.me/p/w9JeoX/useful-links",
    "ICACCOPS": "https://www.icaccops.com/users/Login",
    "Search.org": "https://www.search.org/",
    "MaxMind": "https://www.maxmind.com/en/home",
    "Central Ops": "https://centralops.net/co/",
    "Code of Virginia - Online": "https://law.lis.virginia.gov/vacode",
    "Virginia Judiciary Search": "http://www.courts.state.va.us/caseinfo/home.html",
    "Cyber Chef": "https://gchq.github.io/CyberChef/",
    "EPOCH Time Converter": "https://www.epochconverter.com/",
    "Default Router Passwords": "https://192-168-1-1ip.mobi/default-router-passwords-list/",
    "MAC Address Lookup": "https://www.coffer.com/mac_find/",
    "Virus Total": "https://www.virustotal.com/gui/",
    "Joe's Sandbox (Malware Analysis)": "https://www.joesecurity.org",
    "The Wayback Machine": "https://archive.org/",
    "URL Scan": "https://urlscan.io/",
    "Visual Site Mapper": "http://www.visualsitemapper.com/",
    "File Extension Database": "https://www.file-extensions.org/",
    "List of USB IDs": "http://www.linux-usb.org/usb.ids",
    "FCC ID Search": "https://www.fcc.gov/oet/ea/fccid",
    "The iPhone Wiki": "https://www.theiphonewiki.com/",
    "TCP and UDP Port Numbers": "https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers",
}

software_links = {
    "Download AXIOM - Magnet Forensics": "https://www.magnetforensics.com/downloadAXIOM/",
    "MyCellebrite": "https://community.cellebrite.com/s/login/?language=en_US",
    "ADF Solutions Software": "https://www.adfsolutions.com/downloads",
    "Eric Zimmerman's Tools": "https://ericzimmerman.github.io/",
    "mac4n6 - APOLLO": "https://github.com/mac4n6/APOLLO",
    "Mobile Evidence Acquisition Toolkit (MEAT)": "https://github.com/jfarley248/MEAT",
    "Binary PList Carver": "https://github.com/pug4N6/plist_carver",
    "LibiMobileDevice": "https://libimobiledevice.org/",
    "iOS Sysdiagnose Forensic Scripts": "https://github.com/cheeky4n6monkey/iOS_sysdiagnose_forensic_scripts",
    "Android ADB/Fastboot platform tools": "https://developer.android.com/studio/releases/platform-tools",
    "LEAPP Tools": "https://leapps.org/",
    }

DFIR_links = {
    "Comprehensive DFIR Cheatsheet": "https://www.jaiminton.com/cheatsheet/DFIR/",
    "List of Windows Jump List IDs": "https://forensicswiki.xyz/wiki/index.php?title=List_of_Jump_List_IDs",
    "Windows 10 Registry Hacks": "https://www.maketecheasier.com/windows-10-registry-hacks/",
    "Volatility Command Reference": "https://github.com/volatilityfoundation/volatility/wiki/Command-Reference",
    "File Signature List (1)": "https://www.garykessler.net/library/file_sigs.html",
    "File Signature List (2)": "https://en.wikipedia.org/wiki/List_of_file_signatures",
    "File Signature List (3)": "https://filesignatures.net/index.php?page=all",
}

osint_links = {
    "OSINT Framework": "https://osintframework.com/",
    "OSINT Foundation Start.me": "https://start.me/p/OwabPb/osint-foundations-2026",
    "Online Password Hash Cracking": "https://www.onlinehashcrack.com/",
    "Mobile Country Codes": "https://en.wikipedia.org/wiki/Mobile_country_code",
    "Exploit Database": "https://www.exploit-db.com/",
}


# ----- Link Section Builder -----
def build_link_section(title: str, icon: str, links: dict[str, str]) -> None:
    """Builds a collapsible section of links using an expansion panel.

    Each link opens in a new tab.
    """
    with ui.expansion(
        title,
        icon=icon,
    ).classes("w-full").props("default-opened"):

        with ui.row().classes("w-full flex-wrap gap-2"):

            for name, url in links.items():

                ui.button(
                    name,
                    on_click=lambda u=url: ui.navigate.to(
                        u,
                        new_tab=True,
                    ),
                    color="blue-6",
                ).props("outline no-caps").classes("text-left text-sm")


# ----- Main Page Builder -----
def build_links_page() -> None:
    """Builds the full Useful Links page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):

        ui.label(
            "Useful Links"
        ).classes("text-2xl font-bold mb-4")

        ui.label(
            "Quick access to frequently used resources. "
            "Click any link to open it in a new tab."
        ).classes("text-sm text-gray-400 mb-4")

        # ----- Starter Links -----
        build_link_section(
            title=f"Starter Links ({len(starter_links)})",
            icon="rocket_launch",
            links=starter_links,
        )

        # ----- Forensic Software Downloads -----
        build_link_section(
            title=f"Forensic Software ({len(software_links)})",
            icon="download",
            links=software_links,
        )

        # ----- DFIR Resources -----
        build_link_section(
            title=f"DFIR Resources ({len(DFIR_links)})",
            icon="search",
            links=DFIR_links,
        )

        # ----- OSINT Resources -----
        build_link_section(
            title=f"OSINT Resources ({len(osint_links)})",
            icon="travel_explore",
            links=osint_links,
        )
