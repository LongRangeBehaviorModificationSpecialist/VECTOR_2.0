#!/bin/bash
# Starts VECTOR -- the same as "Start VECTOR.command" in the main VECTOR
# folder, one level up. It is here too so that everything a first-time
# user needs is in this folder.
exec bash "$(dirname "$0")/../Start VECTOR.sh" "$@"
