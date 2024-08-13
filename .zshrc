# Path to your oh-my-zsh installation.
export ZSH=$HOME/.oh-my-zsh

# Set name of the theme to load.
# Look in ~/.oh-my-zsh/themes/
# Optionally, if you set this to "random", it'll load a random theme each
# time that oh-my-zsh is loaded.
ZSH_THEME="verbose"

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

zstyle ':omz:update' mode auto

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
ENABLE_CORRECTION="false"

# Uncomment the following line to display red dots whilst waiting for completion.
COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
DISABLE_UNTRACKED_FILES_DIRTY="true"

ZSH_CUSTOM="$HOME/.cfg/.oh-my-zsh.custom"

ZSH_AUTOSUGGEST_STRATEGY=(match_prev_cmd completion)
ZSH_AUTOSUGGEST_USE_ASYNC="yes"
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=244"

# History configuration inspired by:
# https://martinheinz.dev/blog/110
HISTFILE="$HOME/.zsh_history"
HISTSIZE=10000000
SAVEHIST=10000000
# No ignores for now ...
# HISTORY_IGNORE="(ls|cd|pwd|exit|cd)*"
HIST_STAMPS="yyyy-mm-dd"
setopt EXTENDED_HISTORY      # Write the history file in the ':start:elapsed;command' format.
setopt INC_APPEND_HISTORY    # Write to the history file immediately, not when the shell exits.
setopt SHARE_HISTORY         # Share history between all sessions.
setopt HIST_IGNORE_DUPS      # Do not record an event that was just recorded again.
setopt HIST_IGNORE_ALL_DUPS  # Delete an old recorded event if a new event is a duplicate.
setopt HIST_IGNORE_SPACE     # Do not record an event starting with a space.
setopt HIST_SAVE_NO_DUPS     # Do not write a duplicate event to the history file.
setopt HIST_VERIFY           # Do not execute immediately upon history expansion.
setopt APPEND_HISTORY        # append to history file (Default)
setopt HIST_NO_STORE         # Don't store history commands
setopt HIST_REDUCE_BLANKS    # Remove superfluous blanks from each command line being added to the history.

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.

#  git
#  git-extras

plugins=(
  mvn
  pip
  colored-man-pages
  emacs
  gitfast
  zsh-autosuggestions
  zsh-syntax-highlighting
)
# temporarily (?) disable gradle-completion
# gradle-completion

# User configuration

source $ZSH/oh-my-zsh.sh

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# ssh
# export SSH_KEY_PATH="~/.ssh/dsa_id"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"


###############
# USER CONFIG #
###############

## Check if OSX
if [ "$(uname)" = "Darwin" ]; then
    OS_OSX=true
else
    OS_OSX=false
fi

export PATH="$(brew --prefix)/bin:$HOME/.local/bin:$PATH"

alias dev='cd ~/dev'
alias py2='python2'
alias py3='python3'
alias py='py2'
alias sudo='sudo '
alias plz='sudo '
alias pls='sudo '
alias which='which -a' # more useful version

alias ..="cd .."
alias ...="cd ..."
function cdl() {
    cd "$@"
    ls
}

alias ungz='tar xzf '

if [ "$OS_OSX" = true ]; then
    alias clip='pbcopy'
    alias paste='pbpaste'
else
    alias clip='xclip -selection clipboard'
    alias paste='xclip -selection clipboard -o'
fi

# kcurl == "kerberos curl"
alias kcurl='curl -i -u : --negotiate'

# git aliases
alias glog='git log --format="%C(yellow)%h%C(auto)%d %Cgreen%cd%Creset %s %C(cyan)[%aN <%aE>]%Creset" --graph --decorate --color --date=short'
alias gst='git status'
alias gco='git checkout'
alias gcp='git cherry-pick'
alias grb='git rebase'
alias gcomma='git commit -am'
alias gcomm='git commit -m'
alias gpush='git push'
alias gpull='git pull --rebase'
alias grbc='grb --continue'
alias grba='grb --abort'
alias grbi='grb -i'
alias gcpc='gcp --continue'
alias gcpa='gcp --abort'
alias gbranch='git branch | cat'
alias git-latest="git log --format='%D' | grep -E -v -e '^$' -e 'HEAD' -e 'tag:' | awk -F',' '{ print \$1 }' | head -n 1"
alias grestore="git restore --staged . && gco -- . && git clean -fd"
alias gprune='git fetch --all --prune'
alias gfixup='git log -n 50 --pretty=format:"%h %s" --no-merges | fzf | cut -c -7 | xargs -o git commit --fixup'

# git rebase -i "latest" -> interactive rebase off of the most recent branch besides the current
function grbl() {
  grb -i $(git-latest)
}
alias gws='git rebase --whitespace=fix'
function gwsl() {
  git rebase --whitespace=fix $(git-latest)
}

# mvn aliases
alias mvnskip='mvn -DskipTests -Dmaven.javadoc.skip '

alias restart='shutdown -r 0'

# if-statements commented out - might as well bind both in case
# you are ssh'd in from the other OS
# if [ "$OS_OSX" = "true" ]; then
    bindkey '[D' emacs-backward-word      # alt-cursor-left (mac)
    bindkey '[C' emacs-forward-word      # alt-cursor-right (mac)
# else
    bindkey '^[[1;3D' emacs-backward-word     # alt-cursor-left (linux)
    bindkey '^[[1;3C' emacs-forward-word      # alt-cursor-right (linux)
# fi

unsetopt nomatch # If a match for files isn't found, passes it through to the command instead of
                 # printing a no-match error. Useful since some characters e.g. ^ are zsh file
                 # search keywords but you may want to use them for e.g. git

eq() {
    calc="$@"
    # Attempt to use the slightly-more-powerful gcalccmd;
    # if not present, fall back to bc
    if [ "$(command -v gcalccmd)" != "" ]; then
        echo -ne "$calc\n quit" | gcalccmd | sed 's:^> ::g'
    else
        bc -l <<<"scale=10;$calc"
    fi
}

### Customized version of common-aliases
alias lart='ls -1Fcart'
alias lrt='ls -1Fcrt'

alias -g H='| head'
alias -g T='| tail'
alias -g G='| grep'
alias -g L="| less"
alias -g LL="2>&1 | less"
alias -g NE="2> /dev/null"
alias -g NUL="> /dev/null 2>&1"

_editor_fts=(cpp cxx cc c hh h txt TXT tex java md scala xml out)
for ft in $_editor_fts; do alias -s $ft=$EDITOR; done
#list whats inside packed file
alias -s zip="unzip -l"
alias -s tar="tar tf"
alias -s gz="tar ztf" # Assume all .gz are .tar.gz

alias ??='gh copilot suggest'

# This seems to cause performance issues; disabling for now
# Make zsh autocomplete know about hosts already accessed by SSH
# zstyle -e ':completion:*:(ssh|scp|sftp|rsh|rsync):hosts' hosts 'reply=(${=${${(f)"$(cat {/etc/ssh_,~/.ssh/known_}hosts(|2)(N) /dev/null)"}%%[# ]*}//,/ })'

## Configure FZF if it is present
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
# If 'fd' is present, use it instead of the default find command for fzf path/dir listing
if command -v fd &>/dev/null; then
    _fzf_compgen_path() {
      fd --hidden --follow --exclude ".git" . "$1"
    }
    _fzf_compgen_dir() {
      fd --type d --hidden --follow --exclude ".git" . "$1"
    }
fi

if [[ "$OS_OSX" = "false" ]] && [[ -d /home/linuxbrew/.linuxbrew ]]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Create GitHub CLI token-specific aliases, if the token files exist
[ -f ~/.github/token_personal ] && alias ghp='GITHUB_TOKEN=$(cat ~/.github/token_personal) gh'
[ -f ~/.github/token_enterprise ] && alias ghe='GITHUB_TOKEN=$(cat ~/.github/token_enterprise) gh'

# Init 1Password CLI, if installed
if command -v op &>/dev/null; then
    eval "$(op completion zsh)"; compdef _op op
    source "$HOME/.config/op/plugins.sh"
fi

# Init Volta, if installed
if command -v volta &>/dev/null; then
    export VOLTA_HOME="$HOME/.volta"
    export PATH="$VOLTA_HOME/bin:$PATH"
fi

# Init walk to be used with cd, if installed
if command -v walk &>/dev/null; then
    function walkcd {
      cd "$(walk "$@")"
    }
fi

# Init br, if installed
if command -v br &>/dev/null && [ -d "$HOME/.config/broot" ]; then
    source "$HOME/.config/broot/launcher/bash/br"
fi

# Configs for 'bat'
export BAT_THEME="Coldark-Dark"
# Use 'bat' for git diff to get line numbers, syntax highlighting, etc.
batdiff() {
    git diff --name-only --relative --diff-filter=d "$@" | xargs bat --diff
}

# Init jenv, if installed
if command -v jenv &>/dev/null; then
    export PATH="$HOME/.jenv/shims:$PATH"
    eval "$(jenv init -)"
fi

# iTerm2 shell integration
test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"

# iTerm2 tab titles
function _title_internal {
    if [ -z "$current_iterm_title" ]; then
        echo -ne "\e]1;${PWD/#$HOME/~}\a"
    else
        echo -ne "\e]1;${current_iterm_title}\a"
    fi
}

# If called with no args, revert back to setting title to be pwd
# Otherwise, set title to be the argument supplied
function title {
    if [ "$1" ]; then
        export current_iterm_title="${*}"
    else
        unset current_iterm_title
    fi
}

jenv_add_jdks() {
    if [ "$OS_OSX" = true ]; then
        for jdk in /Library/Java/JavaVirtualMachines/*.jdk; do
            jenv add "$jdk/Contents/Home"
        done
    else
        if [ "$#" != 1 ]; then
            echo "Must provide Java base directory for discovering where JDKs can be discovered, e.g. '/usr/lib/jvm/'" 1>&2
            return 1
        fi
        for jdk in "$1/"*; do
            jenv add "$jdk"
        done
    fi
}

# Define precmd_functions if not already defined
[[ -z $precmd_functions ]] && precmd_functions=()
# Enable title function as an additional precmd function
precmd_functions=($precmd_functions _title_internal)

eval "$(_META_COMPLETE=source_zsh meta)"

alias cfg='git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME"'

export EDITOR=vi
bindkey -e

# Source local configs if they are present
[ -f ~/.zshrc.local ] && source "$HOME/.zshrc.local"
