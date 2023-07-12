#!/usr/bin/env bash

# Run this file to perform one-time setup
# This script is idempotent so it is safe to re-run if anything gets messed up
# It will also update things if they are outdated

cfg_dir="$( cd "$(dirname "$( dirname "${BASH_SOURCE[0]}" )" )" >/dev/null 2>&1 && pwd)"

#################################################################################
# installation lists
#################################################################################

# brew installs
brew_install_list=(
    bash
    tmux
    wget
    zsh
)
# oh-my-zsh plugins
declare -A omz_plugins
omz_plugins[gradle-completion]="git@github.com:gradle/gradle-completion.git"
omz_plugins[zsh-autosuggestions]="git@github.com:zsh-users/zsh-autosuggestions.git"
omz_plugins[zsh-syntax-highlighting]="git@github.com:zsh-users/zsh-syntax-highlighting.git"


#################################################################################
# brew installations
#################################################################################

if [ "$(command -v brew)" == "" ]; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
brew install "${brew_install_list[@]}"

#################################################################################
# oh-my-zsh install and plugins
#################################################################################

# Install oh-my-zsh if it is not already installed; else update
if [ ! -d ~/.oh-my-zsh ]; then
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
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
# SSH configs
#################################################################################

# If no SSH config file is present, create one that simply loads the `config.custom` file
# This is helpful for systems that already contain a managed SSH config file
[ -f ~/.ssh/config ] || echo "Include ~/.ssh/config.custom" > ~/.ssh/config

#################################################################################
# TMUX plugin manager setup
#################################################################################

tmux_plugin_dir="$HOME/.tmux.plugins"
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
