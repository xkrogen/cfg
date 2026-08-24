#!/usr/bin/env bash

# One-shot finalizer for rdev setup. Runs the parts of init_linkedin.sh/setup.sh
# that require the user's forwarded SSH agent or a logged-in `gh`:
#   - clone ekrogen-cfg-overlay as a cfgli bare repo
#   - run xkrogen/cfg's setup.sh (only the parts that were skipped at init time)
#   - install Copilot CLI
#   - install the Copilot Glean MCP and plugins
#   - wire herdr's native Copilot integration (session-restore identity hook)
#   - wire the session archive into Copilot
#
# Triggered from ~/.zshrc.local on first interactive shell when RDEV_ID is set
# and ~/.cfg.li.git/ doesn't exist yet. Safe to re-run manually:
#   bash ~/.cfg/scripts/rdev_finish_setup.sh

set -u

LOG="$HOME/.rdev_finish_setup.log"
LOCK="$HOME/.rdev_finish_setup.lock"

# Prevent concurrent runs (multiple shells start on first SSH)
exec 9>"$LOCK"
if ! flock -n 9; then
    echo "rdev_finish_setup: another run is in progress (lock held on $LOCK); skipping." | tee -a "$LOG"
    exit 0
fi

exec > >(tee -a "$LOG") 2>&1
echo "=== rdev_finish_setup starting at $(date -Is) ==="

if [ -z "${RDEV_ID:-}" ]; then
    echo "Not running on an rdev (RDEV_ID unset); aborting."
    exit 0
fi

if ! ssh-add -l >/dev/null 2>&1; then
    cat <<'EOF'
rdev_finish_setup: no forwarded ssh-agent identities are available.

Reconnect with `rdev ssh <name>` (which enables ForwardAgent by default), or
load a github-capable key into the agent, then re-run:
    bash ~/.cfg/scripts/rdev_finish_setup.sh
EOF
    exit 1
fi

cfg_dir="$(cd "$(dirname "$(dirname "${BASH_SOURCE[0]}")")" >/dev/null 2>&1 && pwd)/scripts"

# 1. Recover xkrogen/cfg base layer if rdev's init-phase got killed before it
#    finished. init.sh is idempotent — it clones into ~/.cfg.git and checks
#    out .zshrc/.bashrc/etc. Without this, .zshrc.local is never sourced
#    because rdev's fallback .zshrc is a stub that skips it.
if [ ! -d "$HOME/.cfg.git" ]; then
    echo "xkrogen/cfg base layer missing; running its init.sh."
    GIT_CLONE_HTTPS=1 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xkrogen/cfg/master/.cfg/scripts/init.sh)" \
        || echo "WARN: xkrogen/cfg init.sh returned non-zero."
fi

# 2. Re-run xkrogen/cfg setup.sh: the initial rdev-phase run often gets killed
#    partway (tmux tpm clone needs the agent, brew install may not finish).
#    setup.sh is idempotent.
if [ -x "$HOME/.cfg/scripts/setup.sh" ]; then
    USER="$(whoami)" "$HOME/.cfg/scripts/setup.sh" || echo "WARN: setup.sh returned non-zero (may be safe to ignore)."
fi

# 3. Clone cfgli bare repo (re-entering init_linkedin.sh now that an agent is available)
"$cfg_dir/init_linkedin.sh" || {
    echo "init_linkedin.sh failed; aborting rdev_finish_setup."
    exit 1
}

# 4. Re-run setup_linkedin.sh (no-op on rdev since ssh-add reinit is gated,
#    but run it to stay uniform with laptop flow).
if [ -x "$cfg_dir/setup_linkedin.sh" ]; then
    "$cfg_dir/setup_linkedin.sh" || echo "WARN: setup_linkedin.sh returned non-zero."
fi

# 4b. Install rdev tooling — both persistent ($HOME: volta node20, uv, TWG,
#     captain dynamic-discovery) and ephemeral (GULL refresh, captain upgrade,
#     trino CLI). The ephemeral half also runs on every rdev-tmux attach via
#     the /var/tmp sentinel it drops, so daily pod restarts self-heal.
if [ -x "$cfg_dir/init_rdev_tools.sh" ]; then
    "$cfg_dir/init_rdev_tools.sh" all || echo "WARN: init_rdev_tools.sh returned non-zero (see ~/.rdev_init_tools.log)."
fi

# 5. Session history: clone the shared archive repo and tag this machine with a
#    distinct source name (rdev:<mp>/<rdev-name>) so Copilot results can be
#    filtered. The source tag lives outside tracked configuration because it is
#    machine-specific.
ARCHIVE_DIR="$HOME/.claude/session-archive"
if [ ! -d "$ARCHIVE_DIR/.git" ]; then
    echo "Cloning claude-session-archive."
    git clone --quiet ssh://git@github.com/ekrogen_LinkedIn/claude-session-archive.git "$ARCHIVE_DIR" \
        || echo "WARN: session-archive clone failed."
    if [ -d "$ARCHIVE_DIR/.git" ]; then
        bash "$ARCHIVE_DIR/sync-archive.sh" rebuild-fts 2>/dev/null \
            || echo "WARN: session-archive FTS rebuild failed."
    fi
fi

SOURCE_TAG="rdev:${PRODUCT_NAME:-unknown}/${RDEV_NAME:-${RDEV_ID}}"
COPILOT_ENV_FILE="$HOME/.copilot-local.env"
if [ ! -f "$COPILOT_ENV_FILE" ] || ! grep -qxF "export CLAUDE_SESSION_ARCHIVE_SOURCE=$SOURCE_TAG" "$COPILOT_ENV_FILE"; then
    echo "export CLAUDE_SESSION_ARCHIVE_SOURCE=$SOURCE_TAG" > "$COPILOT_ENV_FILE"
    echo "Tagged CLAUDE_SESSION_ARCHIVE_SOURCE=$SOURCE_TAG in $COPILOT_ENV_FILE"
else
    echo "Source tag already set to $SOURCE_TAG in $COPILOT_ENV_FILE"
fi

# 6. Install Copilot via its native installer. Copilot is self-contained, so
#    it avoids rdev's Node-version constraints.
curl -fsSL https://gh.io/copilot-install | bash || echo "WARN: copilot install failed."

# 7. Configure the Copilot Glean MCP and marketplaces. The declarations in
#    cfgli identify enabled plugins; this materializes their local catalogs.
COPILOT_BIN="$HOME/.local/bin/copilot"
if [ -x "$COPILOT_BIN" ]; then
    # glean uses OAuth (advertises .well-known/oauth-protected-resource, 401s to
    # token auth), so add it with no header — Copilot runs the OAuth flow on
    # first interactive use. Mirrors the cfgli-shipped mcp-config.json entry.
    if "$COPILOT_BIN" mcp list 2>/dev/null | grep -q "glean_default"; then
        echo "glean MCP already configured (copilot)."
    else
        "$COPILOT_BIN" mcp add glean_default https://linkedin-be.glean.com/mcp/default --transport http \
            || echo "WARN: failed to add glean MCP (copilot)."
    fi

    # Register each marketplace, then materialize the enabled plugins. Copilot
    # keys plugins as <name>@<marketplace>, so derive the install list from the
    # cfgli-shipped settings.json enabledPlugins map (the same source of truth
    # the laptop uses) rather than hardcoding the set here. Use the SSH-with-org
    # URL form authenticates through the forwarded agent under LinkedIn's
    # enterprise protocol policy.
    # proven to clone headlessly via the forwarded agent under LinkedIn's
    # enterprise protocol policy (owner/repo would resolve to an HTTPS clone that
    # needs interactive credentials on rdev).
    copilot_prepare_marketplace() {
        # $1 = display name, $2 = SSH-with-org clone URL.
        #
        # The cfgli-shipped settings.json extraKnownMarketplaces pre-registers
        # these as a GitHub owner/repo source, which Copilot resolves to an
        # *HTTPS* clone. HTTPS has no credentials on a headless rdev, so any
        # `marketplace update` / `plugin install` against that source fails. We
        # must force the source to the SSH-with-org URL (which authenticates via
        # the forwarded agent under LinkedIn's enterprise protocol policy).
        #
        # `marketplace add` has no overwrite flag and `update` takes no source,
        # so the only way to re-point an existing registration is remove+add.
        # The list renders an SSH source as "<name> (URL: ...)" and the HTTPS
        # source as "<name> (GitHub: ...)"; only rewrite when it isn't already
        # the URL form, so re-runs are idempotent and don't churn installed
        # plugins (remove --force would uninstall them).
        local entry
        entry="$("$COPILOT_BIN" plugin marketplace list 2>/dev/null | grep "$1 (")"
        if ! printf '%s' "$entry" | grep -q "(URL:"; then
            if [ -n "$entry" ]; then
                "$COPILOT_BIN" plugin marketplace remove "$1" --force >/dev/null 2>&1 \
                    || echo "WARN: failed to remove pre-registered $1 marketplace (copilot)."
            fi
            "$COPILOT_BIN" plugin marketplace add "$2" \
                || echo "WARN: failed to register $1 marketplace via SSH (copilot)."
        fi
        # A freshly-cloned catalog can lag the marketplace HEAD, so without this
        # `plugin install` fails with "<plugin> not found in marketplace" for
        # entries that exist upstream but not in the stale snapshot.
        "$COPILOT_BIN" plugin marketplace update "$1" \
            || echo "WARN: failed to update $1 marketplace catalog (copilot)."
    }
    copilot_prepare_marketplace linkedin-plugins \
        org-127256988@github.com:linkedin-multiproduct/li-productivity-agents.git
    copilot_prepare_marketplace linkedin-plugin-sandbox \
        org-127256988@github.com:linkedin-multiproduct/linkedin-plugin-sandbox.git
    # enterprise-security-hooks lives in a third marketplace (the security org's
    # private .github repo).
    copilot_prepare_marketplace linkedin-security \
        org-127256988@github.com:linkedin-managed/.github-private.git

    COPILOT_SETTINGS="$HOME/.copilot/settings.json"
    if [ -f "$COPILOT_SETTINGS" ]; then
        installed="$("$COPILOT_BIN" plugin list 2>/dev/null)"
        while IFS= read -r plugin; do
            [ -z "$plugin" ] && continue
            if printf '%s\n' "$installed" | grep -q "$plugin"; then
                continue
            fi
            # Retry once: a plugin install occasionally fails on a just-cloned
            # catalog that hasn't fully settled; a second attempt clears it.
            "$COPILOT_BIN" plugin install "$plugin" \
                || "$COPILOT_BIN" plugin install "$plugin" \
                || echo "WARN: failed to install copilot plugin $plugin."
        done < <(python3 -c '
import json, sys
data = json.load(open(sys.argv[1]))
for key, enabled in data.get("enabledPlugins", {}).items():
    if enabled:
        print(key)
' "$COPILOT_SETTINGS" 2>/dev/null)
    fi
fi

# 7b. Wire herdr's native Copilot integration (session-restore identity hook
#     at ~/.copilot/hooks/herdr-agent-state.sh). setup.sh installs herdr; the
#     SessionStart entry it adds to settings.json is idempotent
#     against the same hook already shipped via cfgli. This only takes effect
#     once a herdr server is (re)started; running herdr servers don't pick it
#     up live.
HERDR_BIN="$HOME/.local/bin/herdr"
if [ -x "$HERDR_BIN" ] && [ -x "$COPILOT_BIN" ]; then
    "$HERDR_BIN" integration install copilot || echo "WARN: herdr integration install copilot failed."
fi

# 8. Pull latest xkrogen/cfg + cfgli so the respawned tmux server picks up
#    the current .tmux.conf. xkrogen init.sh only clones — it doesn't fetch
#    on subsequent runs, so a stale .tmux.conf would stick around.
if [ -d "$HOME/.cfg.git" ]; then
    git --git-dir="$HOME/.cfg.git/" config --replace-all remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*' 2>/dev/null
    git --git-dir="$HOME/.cfg.git/" fetch --quiet origin 2>/dev/null
    git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME" merge --ff-only origin/main 2>/dev/null \
        || echo "WARN: xkrogen/cfg fast-forward failed (uncommitted changes? stale refspec?)"
fi
if [ -d "$HOME/.cfg.li.git" ]; then
    git --git-dir="$HOME/.cfg.li.git/" config --replace-all remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*' 2>/dev/null
    git --git-dir="$HOME/.cfg.li.git/" fetch --quiet origin 2>/dev/null
    git --git-dir="$HOME/.cfg.li.git/" --work-tree="$HOME" merge --ff-only origin/master 2>/dev/null \
        || echo "WARN: cfgli fast-forward failed"
fi

# 9. Leave rdev's auto-spawned "build" tmux session alone. It lives on
#    /etc/rdev/tmux under /usr/bin/tmux 3.2a and gets re-created by rdev
#    on every pod boot. Our workflow uses a separate "rdev" session on
#    the linuxbrew default socket (/tmp/tmux-<uid>/default) via rdev-tmux,
#    which is immune to rdev's lifecycle. Earlier versions of this script
#    tried to kill+respawn the build server on /etc/rdev/tmux with the
#    3.6a binary, but rdev's init re-spawned the 3.2a server on every
#    pod restart, and the two would collide.

echo "=== rdev_finish_setup finished at $(date -Is) ==="
