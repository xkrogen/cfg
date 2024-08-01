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

### Reinitialize the SSH agent if needed

if [ "$OS_OSX" = true ]; then
    ssh-add -D && \
        ssh-add --apple-use-keychain ~/.ssh/personal_github_xkrogen && \
        ssh-add --apple-use-keychain ~/.ssh/ekrogen_at_linkedin.com_ssh_key
else
    ssh-add -D && \
        ssh-add ~/.ssh/personal_github_xkrogen && \
        ssh-add ~/.ssh/ekrogen_at_linkedin.com_ssh_key
fi
