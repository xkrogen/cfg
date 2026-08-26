#!/usr/bin/env bash

# Idempotent installer for tools that the rdev-setup skill used to cover
# manually. Split into two entry points:
#
#   one_time   — installs that live under $HOME (survives pod restart).
#                Run at initial rdev provisioning from rdev_finish_setup.sh.
#
#   every_boot — installs into overlay-fs paths (/usr/local, /export/content,
#                /home/linuxbrew baseline) that get wiped when the rdev pod
#                restarts at the end of an idle day. Driven by the sentinel
#                at $SENTINEL_FILE: if missing, we re-run; if present, the
#                container has already been reprovisioned this lifetime.
#
# Both are idempotent. "all" (default) runs every_boot, then one_time if the
# $HOME-side tools aren't detected yet.
#
# Usage:
#   bash ~/.cfg/scripts/init_rdev_tools.sh            # all (default)
#   bash ~/.cfg/scripts/init_rdev_tools.sh every_boot
#   bash ~/.cfg/scripts/init_rdev_tools.sh one_time
#   FORCE=1 bash ... every_boot                       # ignore sentinel

set -u

LOG="$HOME/.rdev_init_tools.log"
SENTINEL_FILE="/var/tmp/.rdev_ephemeral_setup_done"

log() { printf '[init_rdev_tools] %s\n' "$*" | tee -a "$LOG" >&2; }

configure_github_https() {
    if ! command -v gh >/dev/null 2>&1; then
        log "SKIP: GitHub HTTPS configuration needs gh."
        return
    fi

    # RDEVs cannot rely on a local machine's forwarded SSH agent after detach.
    # gh persists its OAuth credential under $HOME, which survives pod restarts.
    gh config set git_protocol https --host github.com >>"$LOG" 2>&1 \
        || log "WARN: failed to set GitHub's git protocol to HTTPS."
    for ssh_url in \
        "git@github.com:" \
        "ssh://git@github.com/" \
        "org-127256988@github.com:" \
        "ssh://org-127256988@github.com/" \
        "org-132020694@github.com:" \
        "ssh://org-132020694@github.com/"; do
        if ! git config --global --get-all url."https://github.com/".insteadOf 2>/dev/null \
            | grep -Fqx -- "$ssh_url"; then
            git config --global --add url."https://github.com/".insteadOf "$ssh_url" \
                || log "WARN: failed to rewrite $ssh_url to HTTPS."
        fi
    done
    if gh auth status --hostname github.com >/dev/null 2>&1; then
        gh auth setup-git --hostname github.com >>"$LOG" 2>&1 \
            || log "WARN: failed to configure gh as Git's HTTPS credential helper."
    else
        log "SKIP: gh is not authenticated; run 'gh auth login' once, then re-run init_rdev_tools.sh."
    fi
}

# ----------------------------------------------------------------------------
# every_boot — re-run on every pod restart (overlayfs wipes)
# ----------------------------------------------------------------------------
every_boot() {
    if [ -z "${RDEV_ID:-}" ]; then
        log "not on an rdev (RDEV_ID unset); skipping every_boot."
        return 0
    fi
    if [ -f "$SENTINEL_FILE" ] && [ -z "${FORCE:-}" ]; then
        log "sentinel $SENTINEL_FILE present; every_boot already ran this pod lifetime."
        return 0
    fi

    log "every_boot starting at $(date -Is)"

    # 1. GULL packages — LinkedIn's CLI baseline (mint, captain, curli, darwin,
    #    authn-cli, and ~50 others). The update script needs sudo and re-runs
    #    yum install against the full LinkedIn RPM list. Takes a few minutes.
    if [ -x /usr/local/bin/update_gull_packages.sh ]; then
        log "refreshing GULL packages (sudo update_gull_packages.sh)..."
        if sudo -n /usr/local/bin/update_gull_packages.sh >>"$LOG" 2>&1; then
            log "GULL refresh ok."
        else
            log "WARN: GULL refresh failed (sudo unavailable or yum error). Continuing."
        fi
    else
        log "WARN: /usr/local/bin/update_gull_packages.sh not found; skipping GULL refresh."
    fi

    # 2. Captain core — the inner python package is cached under $HOME
    #    (~/.cache/python-cli-runner), but the shell wrapper at
    #    /export/content/linkedin/bin/captain comes from GULL above and is
    #    wiped on restart. `captain upgrade` re-pulls captain_core to latest
    #    (fast no-op if already current).
    if command -v captain >/dev/null 2>&1; then
        log "captain upgrade..."
        captain upgrade >>"$LOG" 2>&1 || log "WARN: captain upgrade failed."
    else
        log "WARN: captain not on PATH after GULL refresh; skipping captain upgrade."
    fi

    # 3. Trino CLI — not in the GULL update list. `yum -y install LNKD-trino-cli`
    #    drops it at /export/content/linkedin/bin/trino.
    if ! command -v trino >/dev/null 2>&1; then
        log "installing LNKD-trino-cli..."
        if sudo -n yum -y install LNKD-trino-cli >>"$LOG" 2>&1; then
            log "trino CLI installed."
        else
            log "WARN: failed to install LNKD-trino-cli."
        fi
    else
        log "trino CLI already present."
    fi

    # 4. kubectl-in + dependencies — not in the GULL update list.
    if ! command -v kubectl-in >/dev/null 2>&1; then
        log "installing LNKD-kubectl-in LNKD-kubectl-login LNKD-lipy-kubectl..."
        if sudo -n dnf install -y LNKD-kubectl-in LNKD-kubectl-login LNKD-lipy-kubectl >>"$LOG" 2>&1; then
            log "kubectl-in installed."
        else
            log "WARN: failed to install kubectl-in packages."
        fi
    else
        log "kubectl-in already present."
    fi

    # Touch the sentinel only if we got this far without bailing out. Any
    # individual step failure above is logged but non-fatal — partial success
    # still beats needing to rerun the whole thing on every attach.
    mkdir -p "$(dirname "$SENTINEL_FILE")"
    date -Is > "$SENTINEL_FILE"
    log "every_boot finished at $(date -Is); sentinel = $SENTINEL_FILE"
}

# ----------------------------------------------------------------------------
# one_time — install tools that live under $HOME (persistent volume)
# ----------------------------------------------------------------------------
one_time() {
    log "one_time starting at $(date -Is)"

    # 1. volta Node 20 — the tool-image dir is what the ~/.zshrc.local PATH
    #    fix prepends. Without a 20.x toolchain installed, the glob in zshrc
    #    finds nothing and Node 16 keeps winning.
    if [ -x "$HOME/.volta/bin/volta" ]; then
        if ! ls -d "$HOME/.volta/tools/image/node/20."* >/dev/null 2>&1; then
            log "volta install node@20..."
            "$HOME/.volta/bin/volta" install node@20 >>"$LOG" 2>&1 \
                || log "WARN: volta install node@20 failed."
        else
            log "volta Node 20 already installed."
        fi
    else
        log "WARN: volta not installed yet; skipping node@20 (setup.sh handles volta bootstrap)."
    fi

    # 2. uv (Astral) — standalone installer, drops uv/uvx into ~/.local/bin.
    if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
        log "installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh 2>>"$LOG" | sh >>"$LOG" 2>&1 \
            || log "WARN: uv install failed."
    else
        log "uv already present."
    fi

    # 3. Teamwork Graph CLI — install the verified official binary without
    # triggering interactive login or its all-or-nothing generated skill set.
    # The maintained Jira and Confluence skills arrive through the config overlay.
    if [ ! -x "$HOME/.local/bin/twg" ]; then
        local twg_installer
        twg_installer="$(mktemp)" || {
            log "WARN: failed to create a temporary file for the TWG installer."
            return
        }
        log "installing Teamwork Graph CLI..."
        if curl -fsSL https://teamwork-graph.atlassian.com/cli/install -o "$twg_installer" \
            && bash "$twg_installer" --yes --skip-login --skip-skills --plugin copilot >>"$LOG" 2>&1; then
            log "Teamwork Graph CLI installed."
        else
            log "WARN: Teamwork Graph CLI install failed."
        fi
        rm -f "$twg_installer"
    else
        log "Teamwork Graph CLI already installed."
    fi

    # 4. Git-sprout — the Cargo build survives pod restarts and avoids the
    #    Homebrew Linux bottle's incompatible glibc requirement.
    if [ -x "$HOME/.cfg/scripts/install_git_sprout.sh" ]; then
        "$HOME/.cfg/scripts/install_git_sprout.sh" >>"$LOG" 2>&1 \
            || log "WARN: git-sprout setup failed."
    else
        log "WARN: git-sprout installer is missing."
    fi

    # 5. GitHub HTTPS auth — avoids depending on a forwarded SSH agent after
    # detaching from the RDEV. No credential is stored in dotfiles.
    configure_github_https

    # 6. Captain dynamic-discovery — enables the compact tool interface for
    #    Copilot. It writes under $HOME and persists across pod restarts.
    if command -v captain >/dev/null 2>&1; then
        if [ ! -f "$HOME/.copilot/.captain-dynamic-discovery-setup" ]; then
            log "captain setup dynamic-discovery --copilot..."
            if captain setup dynamic-discovery --copilot >>"$LOG" 2>&1; then
                mkdir -p "$HOME/.copilot"
                date -Is > "$HOME/.copilot/.captain-dynamic-discovery-setup"
                log "dynamic-discovery configured (copilot)."
            else
                log "WARN: captain setup dynamic-discovery --copilot failed."
            fi
        else
            log "captain dynamic-discovery already configured (copilot)."
        fi
    fi

    log "one_time finished at $(date -Is)"
}

# ----------------------------------------------------------------------------
# Entry
# ----------------------------------------------------------------------------
mode="${1:-all}"
case "$mode" in
    every_boot) every_boot ;;
    one_time)   one_time ;;
    all)
        every_boot
        # Only run one_time when the persistent-side tools look unprovisioned.
        # Detection is cheap; full one_time is idempotent but noisy in the log.
        if ! command -v uv >/dev/null 2>&1 \
            || ! ls -d "$HOME/.volta/tools/image/node/20."* >/dev/null 2>&1 \
            || [ ! -x "$HOME/.local/bin/twg" ] \
            || [ ! -x "$HOME/.local/bin/git-sprout" ]; then
            one_time
        else
            log "one_time tooling already present; skipping one_time."
        fi
        ;;
    *)
        echo "usage: $(basename "$0") [all|every_boot|one_time]" >&2
        exit 2
        ;;
esac
