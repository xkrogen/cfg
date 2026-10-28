#!/usr/bin/env bash

# Run this file to perform one-time setup
# This script is idempotent so it is safe to re-run if anything gets messed up
# It will also update things if they are outdated

cfg_dir="$( cd "$(dirname "$( dirname "${BASH_SOURCE[0]}" )" )" >/dev/null 2>&1 && pwd)"
if [ "$(uname)" = "Darwin" ]; then
    OS_OSX=true
else
    OS_OSX=false
fi

#################################################################################
# brew installations
#################################################################################

# The Brew bootstrap and package lists live in brew_standard_tools.sh, which
# restore_rdev_brew.sh also uses.
source "$cfg_dir/scripts/brew_standard_tools.sh"
brew_install_standard_formulas
# The other Brew packages remain best effort; Java tooling is required unless skipped.
if [ "${CFG_SKIP_JDTLS:-0}" != "1" ]; then
    brew install jdtls || exit $?
fi
brew_install_standard_casks
"$cfg_dir/scripts/install_git_sprout.sh"

#################################################################################
# oh-my-zsh install and plugins
#################################################################################

# Install oh-my-zsh if it is not already installed; else update
if [ ! -d ~/.oh-my-zsh ]; then
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --keep-zshrc
fi

#################################################################################
# Volta package manager setup
#################################################################################

if ! command -v volta &>/dev/null; then
    curl https://get.volta.sh | bash -s -- --skip-setup
fi
"$cfg_dir/scripts/install_pyright.sh" || exit $?

#################################################################################
# Native installers
#################################################################################

if [ ! -x "$HOME/.local/bin/herdr" ]; then
    curl -fsSL https://herdr.dev/install.sh | sh
fi
"$cfg_dir/scripts/install_herdr_skill.sh"
if [ -x "$HOME/.local/bin/herdr" ]; then
    "$HOME/.local/bin/herdr" integration install codex || echo "WARN: herdr integration install codex failed."
    "$HOME/.local/bin/herdr" integration install antigravity-cli || echo "WARN: herdr integration install antigravity-cli failed."
    python3 -c '
import json
from pathlib import Path
p = Path.home() / ".gemini/config/hooks.json"
data = json.loads(p.read_text()) if p.is_file() else {}
herdr = data.setdefault("herdr", {})
cmd = "python3 \"$HOME/.local/bin/named-session.py\" agy hook"
entry = {"command": cmd, "timeout": 10, "type": "command"}
for event in ("PreInvocation", "Stop"):
    hooks = herdr.setdefault(event, [])
    if not any(h.get("command") == cmd for h in hooks):
        hooks.append(entry)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(data, indent=2) + "\n")
'
fi
"$cfg_dir/scripts/install_px0.sh" || exit $?
"$cfg_dir/scripts/install_terminal_browser.sh" || exit $?

#################################################################################
# TMUX plugin manager setup
#################################################################################

tmux_plugin_dir="$HOME/.tmux/plugins"
if [ ! -d "$tmux_plugin_dir/tpm" ]; then
    mkdir -p "$tmux_plugin_dir"
    git clone "git@github.com:tmux-plugins/tpm" "$tmux_plugin_dir/tpm"
else
    (cd "$tmux_plugin_dir/tpm" && git pull)
fi

#################################################################################
# Misc
#################################################################################

git config --global core.excludesfile "$cfg_dir/.gitignore_global"
# install fzf key bindings and completion for zsh
"$(brew --prefix)/opt/fzf/install" --no-fish --no-bash --key-bindings --no-update-rc --completion
# enable jenv to export JAVA_HOME
jenv enable-plugin export

echo "NOTE: Upon first time running tmux, press prefix + I to install plugins"
echo "      (see setup instructions at https://github.com/tmux-plugins/tpm)"
