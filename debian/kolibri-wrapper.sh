#!/bin/sh
# Wrapper for the kolibri command that uses the correct Python interpreter.
# Sources /etc/default/kolibri to resolve KOLIBRI_PYTHON, then execs kolibri.

set -e

# Source the kolibri environment if available (sets KOLIBRI_PYTHON, PYTHONPATH, etc.)
if [ -f /etc/default/kolibri ]; then
    set -o allexport
    . /etc/default/kolibri
    set +o allexport
fi

# Default to system python3 if not resolved
KOLIBRI_PYTHON="${KOLIBRI_PYTHON:-python3}"

exec "$KOLIBRI_PYTHON" -m kolibri "$@"
