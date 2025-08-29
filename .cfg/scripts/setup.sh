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

# brew installs
brew_install_list=(
    atuin
    bash
    bat
    cloc
    fd
    fzf
    gcc
    gh
    gradle-completion
    gron
    jenv
    pipx
    the_silver_searcher
    tldr
    tree
    tmux
    ripgrep
    walk
    wget
    ynqa/tap/jnv
    zsh
    zsh-autosuggestions
    zsh-syntax-highlighting
)


if ! command -v brew &>/dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ "$OS_OSX" = "false" ]]; then
        eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"
    fi
fi
brew install "${brew_install_list[@]}"

export PATH="$(brew --prefix)/bin:$PATH"

#################################################################################
# other installation lists
#################################################################################

# Volta/npm packages
npm_install_list=()

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
if [ ${#npm_install_list[@]} -gt 0 ]; then
  volta install "${npm_install_list[@]}"
fi

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
