#!/bin/bash

# Run the following command to initialize the dotfiles repo
# > sh -c "$(curl -fsSL https://raw.githubusercontent.com/xkrogen/cfg/master/.cfg/scripts/init.sh)"

git clone --bare https://github.com/xkrogen/dotfiles "$HOME/.cfg.git"

function cfg {
   /usr/bin/git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME" "$@"
}

cfg_backup="$HOME/.cfg-bak"
mkdir -p "$cfg_backup"

if cfg checkout; then
  echo "Checked out config.";
else
    echo "Backing up pre-existing dot files into $cfg_backup"
    cfg checkout 2>&1 | grep -E "\s+\." | awk '{ print $1 }' | xargs -I{} mv {} ".cfg-bak/{}"
fi
cfg checkout
cfg config status.showUntrackedFiles no
