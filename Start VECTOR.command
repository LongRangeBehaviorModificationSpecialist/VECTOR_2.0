#!/bin/bash
# Start VECTOR -- double-click this file in Finder.
#
# The first time, it creates the .venv folder and installs what VECTOR
# needs, which takes a few minutes and an internet connection. After
# that it starts straight away, and installs again only when
# requirements.txt changes -- after an update, say.
#
# VECTOR runs while this Terminal window is open. Close the window, or
# press Ctrl+C, to stop it. Arguments are passed through, so from a
# terminal
#     ./Start\ VECTOR.command --lan
# opens it to the local network.

cd "$(dirname "$0")" || exit 1

fail() {
    echo
    echo "$1"
    echo "See \"Troubleshooting\" in README.md."
    read -r -p "Press Return to close this window. " _
    exit 1
}

if [ ! -x .venv/bin/python ]; then
    echo "Setting up VECTOR for the first time. This takes a few minutes..."
    PYTHON=""
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    done
    [ -n "$PYTHON" ] || fail "Python 3.10 or newer is needed and was not found.
Install it from https://www.python.org/downloads/macos/ or with: brew install python"
    "$PYTHON" -m venv .venv || fail "Could not create the .venv folder."
fi

# A copy of requirements.txt is kept once it has installed, so an update
# that changes the requirements installs them before VECTOR starts.
if ! cmp -s requirements.txt .venv/requirements.installed; then
    echo "Installing the packages VECTOR needs..."
    .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt ||
        fail "Installing the packages failed. Check the internet connection and try again."
    cp requirements.txt .venv/requirements.installed
fi

.venv/bin/python main.py "$@" ||
    fail "VECTOR stopped with an error. The message above says why."
