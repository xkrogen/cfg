#!/usr/bin/env bash

# Restores Homebrew and the standard Brew formulae and casks on an RDev after pod
# recreation wipes /home/linuxbrew. It runs only the Brew phase from
# brew_standard_tools.sh, not rdev_finish_setup.sh or the full setup.sh, which
# also refresh Copilot, plugins, auth, and cfg checkouts.
#
# The /var/tmp sentinel is written only after every formula and cask succeeds,
# so it records a complete restore for this pod lifetime. A failed attempt
# leaves a cooldown stamp, so each new shell does not restart a long install.
# A non-blocking flock coalesces overlapping callers. Brew children run with
# fd 9 closed, so the lock ends when this process exits.
#
# FORCE=1 ignores the sentinel and cooldown. Progress is appended to
# ~/.rdev_brew_restore.log.

set -u

if [ -z "${RDEV_ID:-}" ]; then
    echo "restore_rdev_brew: not on an RDev (RDEV_ID unset); skipping." >&2
    exit 0
fi

LOG="$HOME/.rdev_brew_restore.log"
LOCK="$HOME/.rdev_brew_restore.lock"
SENTINEL="${RDEV_BREW_RESTORE_SENTINEL:-/var/tmp/.rdev_brew_restore_done}"
ATTEMPT_STAMP="${RDEV_BREW_RESTORE_ATTEMPT_STAMP:-/var/tmp/.rdev_brew_restore_attempt}"
BREW_PREFIX=/home/linuxbrew/.linuxbrew
COOLDOWN_MINUTES=30

if [ -f "$SENTINEL" ] && [ -z "${FORCE:-}" ]; then
    exit 0
fi

exec 9>"$LOCK"
if ! flock -n 9; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) another restore holds $LOCK; coalescing" >>"$LOG"
    exit 0
fi

exec >>"$LOG" 2>&1
log() { echo "[restore_rdev_brew] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }

if [ -z "${FORCE:-}" ] && [ -n "$(find "$ATTEMPT_STAMP" -mmin "-$COOLDOWN_MINUTES" 2>/dev/null)" ]; then
    log "previous attempt is within ${COOLDOWN_MINUTES} minutes; skipping (FORCE=1 overrides)"
    exit 0
fi
log "restore starting"
date -u +%Y-%m-%dT%H:%M:%SZ >"$ATTEMPT_STAMP"

export USER="$(id -un)" LOGNAME="$(id -un)" NONINTERACTIVE=1
if [ -x "$BREW_PREFIX/bin/brew" ]; then
    eval "$("$BREW_PREFIX/bin/brew" shellenv)"
fi

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/brew_standard_tools.sh"
if brew_install_standard_formulas 9>&- && brew_install_standard_casks 9>&-; then
    date -u +%Y-%m-%dT%H:%M:%SZ >"$SENTINEL"
    log "restore finished; sentinel $SENTINEL written"
else
    log "ERROR: standard Brew restore failed; the next attempt waits ${COOLDOWN_MINUTES} minutes unless FORCE=1"
    exit 1
fi
