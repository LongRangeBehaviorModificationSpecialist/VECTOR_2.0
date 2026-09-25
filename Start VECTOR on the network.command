#!/bin/bash
# Start VECTOR so other devices can reach it -- double-click in Finder.
#
# The same launcher as "Start VECTOR.command", started with --lan. VECTOR
# then listens on the network rather than on this machine alone, so a
# tablet or a second laptop on the same network can open it: the address
# is printed in this Terminal window when it starts.
#
# Traffic is unencrypted HTTP. Use this only on a network you control,
# and use "Start VECTOR.command" the rest of the time -- with that one,
# the port is not on the network at all.

cd "$(dirname "$0")" || exit 1
exec bash "./Start VECTOR.sh" --lan "$@"
