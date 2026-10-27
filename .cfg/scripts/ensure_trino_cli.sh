#!/usr/bin/env bash

# Ensures the Trino CLI from the LNKD-trino-cli RPM is present at one of its
# canonical install paths and responds to --help.
#
# The RPM lands under /export/content (overlay-fs), so it disappears when the
# rdev pod is recreated while $HOME survives. Each run checks the binary
# directly instead of trusting the sentinel or `command -v`, which can resolve a
# stale or unrelated shim. Installation runs only when the canonical binary is
# missing or fails --help. A successful run leaves the binary untouched.
#
# Usage:
#   bash ~/.cfg/scripts/ensure_trino_cli.sh
#
# TRINO_CLI_BIN_DIRS overrides the colon-separated search list (tests use this).

set -u

LOG="$HOME/.rdev_init_tools.log"
BIN_DIRS="${TRINO_CLI_BIN_DIRS:-/export/content/granular/bin:/export/content/linkedin/bin}"

log() { printf '[ensure_trino_cli] %s\n' "$*" | tee -a "$LOG" >&2; }

# Prints the first canonical trino executable, or nothing.
find_canonical_trino() {
    local dir IFS=':'
    for dir in $BIN_DIRS; do
        if [ -x "$dir/trino" ]; then
            printf '%s\n' "$dir/trino"
            return 0
        fi
    done
    return 1
}

# A binary counts as usable only if it starts; a present but broken file is
# treated like a missing one so the install path can repair it.
trino_usable() {
    "$1" --help >/dev/null 2>&1
}

bin="$(find_canonical_trino)" && trino_usable "$bin" && {
    log "trino CLI present and usable at $bin."
    exit 0
}

if [ -n "$bin" ]; then
    log "WARN: $bin exists but --help failed; reinstalling LNKD-trino-cli."
else
    log "trino CLI missing from [$BIN_DIRS]; installing LNKD-trino-cli."
fi

if ! sudo -n dnf install -y LNKD-trino-cli >>"$LOG" 2>&1; then
    log "ERROR: sudo -n dnf install LNKD-trino-cli failed."
    exit 1
fi

bin="$(find_canonical_trino)" && trino_usable "$bin" || {
    log "ERROR: trino CLI still missing or unusable after install."
    exit 1
}
log "trino CLI installed and usable at $bin."
