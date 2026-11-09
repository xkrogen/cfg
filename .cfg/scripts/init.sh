#!/usr/bin/env bash

# Run the following command to initialize the dotfiles repo
# > sh -c "$(curl -fsSL https://raw.githubusercontent.com/xkrogen/cfg/master/.cfg/scripts/init.sh)"
# To clone using HTTPS instead of GIT:
# > GIT_CLONE_HTTPS=1 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xkrogen/cfg/master/.cfg/scripts/init.sh)"

if [[ -v GIT_CLONE_HTTPS ]]; then
    repo_url='https://github.com/xkrogen/cfg.git'
else
    repo_url='git@github.com:xkrogen/cfg.git'
fi

git clone --bare "$repo_url" "$HOME/.cfg.git"

# `git clone --bare` writes no fetch refspec, remote-tracking refs, or branch upstream.
# Without a branch upstream, `git pull` cannot pick the branch to merge. This sets the
# refspec if absent and, for the checked-out branch, a complete remote+merge pair to
# origin/<same branch>. Complete existing tracking is left unchanged; a partial pair is
# reported, not completed; a branch with no origin counterpart gets no upstream.
function cfg_ensure_tracking {
    local gd="$HOME/.cfg.git" branch remote merge
    git --git-dir="$gd" config --get remote.origin.fetch >/dev/null 2>&1 \
        || git --git-dir="$gd" config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*' || return 1
    branch=$(git --git-dir="$gd" symbolic-ref --short HEAD) || return 1
    remote=$(git --git-dir="$gd" config --get "branch.$branch.remote") || remote=""
    merge=$(git --git-dir="$gd" config --get "branch.$branch.merge") || merge=""
    if [ -n "$remote" ] && [ -n "$merge" ]; then return 0; fi
    if [ -n "$remote$merge" ]; then
        echo "WARN: branch $branch has partial tracking config; leaving it unchanged."
        return 1
    fi
    if ! git --git-dir="$gd" rev-parse --verify --quiet "refs/remotes/origin/$branch" >/dev/null; then
        git --git-dir="$gd" fetch --quiet origin || return 1
    fi
    if git --git-dir="$gd" rev-parse --verify --quiet "refs/remotes/origin/$branch" >/dev/null; then
        git --git-dir="$gd" branch --set-upstream-to="origin/$branch" "$branch" >/dev/null || return 1
    else
        echo "WARN: branch $branch has no origin/$branch; it is local-only and has no upstream."
        return 1
    fi
}
cfg_ensure_tracking || echo "WARN: could not set cfg remote tracking; plain git fetch/pull may not update it."

function cfg {
   git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME" "$@"
}

mkdir -p "$HOME/.cfg-bak"

if cfg checkout; then
    echo "Checked out config.";
else
    echo ""
    echo "Checkout failed, backing up pre-existing dot files into ~/.cfg-bak ..."
    echo ""
    cfg checkout 2>&1 \
        | grep -E "\s+\." \
        | sed -e 's/^[[:space:]]*//' \
        | tr '\n' '\0' \
        | xargs -0 sh -c 'for f do echo "Moving \"~/$f\" into ~/.cfg-bak/ ..."; if [[ "$f" =~ / ]]; then target_dir="$(dirname "$HOME/.cfg-bak/$f")"; mkdir -p "$target_dir"; else target_dir="$HOME/.cfg-bak/"; fi; mv "$HOME/$f" "$target_dir"; done' _
    echo ""
    echo "Attempting checkout again..."
    echo ""
    cfg checkout
fi
cfg config status.showUntrackedFiles no
