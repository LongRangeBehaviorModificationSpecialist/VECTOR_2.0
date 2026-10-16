#!/bin/bash
# Start VECTOR on macOS -- double-click this file in Finder.
#
# The launcher itself is "Start VECTOR.sh". Finder opens a .command file
# in Terminal when it is double-clicked, and will not open a .sh file, so
# this wrapper is what makes double-clicking work. Arguments are passed
# through, so from a terminal
#     "./Start VECTOR.command" --lan
# opens VECTOR to the local network.

cd "$(dirname "$0")" || exit 1
exec bash "./Start VECTOR.sh" "$@"
