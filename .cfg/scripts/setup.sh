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
    bash
    bat
    cloc
    fd
    fzf
    gcc
    gh
    gron
    jenv
    pipx
    tldr
    tree
    tmux
    rename
    ripgrep
    walk
    wget
    zsh
    ynqa/tap/jnv
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

# note that this has to be done AFTER brew installations because
# modern bash is required

# oh-my-zsh plugins
declare -A omz_plugins
omz_plugins[gradle-completion]="https://github.com/gradle/gradle-completion.git"
omz_plugins[zsh-autosuggestions]="https://github.com/zsh-users/zsh-autosuggestions.git"
omz_plugins[zsh-syntax-highlighting]="https://github.com/zsh-users/zsh-syntax-highlighting.git"

# Volta/npm packages
npm_install_list=()

#################################################################################
# oh-my-zsh install and plugins
#################################################################################

# Install oh-my-zsh if it is not already installed; else update
if [ ! -d ~/.oh-my-zsh ]; then
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --keep-zshrc
fi

omz_plugin_dir="$cfg_dir/.oh-my-zsh.custom/plugins"
mkdir -p "$omz_plugin_dir"
# mapping of plugin-name to plugin-repo
for p in "${!omz_plugins[@]}"; do
    if [ ! -d "$omz_plugin_dir/$p" ]; then
        git clone "${omz_plugins[$p]}" "$omz_plugin_dir/$p"
    else
        (cd "$omz_plugin_dir/$p" && git pull)
    fi
done

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
