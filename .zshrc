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
ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# The optional three formats: "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# HIST_STAMPS="mm/dd/yyyy"

ZSH_CUSTOM="$HOME/.cfg/.oh-my-zsh.custom"

ZSH_AUTOSUGGEST_STRATEGY=(match_prev_cmd completion)
ZSH_AUTOSUGGEST_USE_ASYNC="yes"
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=244"

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
  gradle-completion
  gitfast
  zsh-autosuggestions
  zsh-syntax-highlighting
)

# User configuration

source $ZSH/oh-my-zsh.sh

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

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

# If Emacs is installed, set it to be the default editor
# Use emacsclient if available
if [ "$EMACS_PLUGIN_LAUNCHER" != "" ]; then
    alias emacs="$EMACS_PLUGIN_LAUNCHER -nw"
    alias emacsw="$EMACS_PLUGIN_LAUNCHER"
    export EDITOR="$EMACS_PLUGIN_LAUNCHER -nw"
    export VISUAL="$EDITOR"
elif [ "$(command -v emacs)" != "" ]; then
    alias emacs="\emacs -nw"
    alias emacsw="\emacs"
    export EDITOR="\emacs -nw"
    export VISUAL="$EDITOR"
fi
alias emacs-clean='rm -f *\~ \#*\# .\#*'
alias emacs-cleanr='find . -name "*~" -o -name "#*#" -o -name ".#*" | xargs rm -f'

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

alias dud='du -d 1 -h'
alias fd='find . -type d -name'
alias ff='find . -type f -name'
alias hgrep="fc -El 0 | grep"
alias rgrep="grep -R . -e " # recursive grep

_editor_fts=(cpp cxx cc c hh h txt TXT tex java md scala xml out)
for ft in $_editor_fts; do alias -s $ft=$EDITOR; done
#list whats inside packed file
alias -s zip="unzip -l"
alias -s tar="tar tf"
alias -s gz="tar ztf" # Assume all .gz are .tar.gz

# Make zsh autocomplete know about hosts already accessed by SSH
zstyle -e ':completion:*:(ssh|scp|sftp|rsh|rsync):hosts' hosts 'reply=(${=${${(f)"$(cat {/etc/ssh_,~/.ssh/known_}hosts(|2)(N) /dev/null)"}%%[# ]*}//,/ })'

## FASD CONFIG - only if fasd is present
if [ "$(command -v fasd)" != "" ]; then
    fasd_cache="${ZSH_CACHE_DIR}/fasd-init-cache"
    if [ "$(command -v fasd)" -nt "$fasd_cache" -o ! -s "$fasd_cache" ]; then
        fasd --init auto >| "$fasd_cache"
    fi
    source "$fasd_cache"
    unset fasd_cache

    alias a='fasd -a'        # any
    alias s='fasd -si'       # show / search / select
    alias d='fasd -d'        # directory
    alias f='fasd -f'        # file
    alias sd='fasd -sid'     # interactive directory selection
    alias sf='fasd -sif'     # interactive file selection
    alias z='fasd_cd -d'     # cd, same functionality as j in autojump
    alias zz='fasd_cd -d -i' # cd with interactive selection

    alias e='f -e "emacs -nw"' # quick opening files with emacs (in term)
    alias ew='f -e emacs' # quick opening files with emacs (in window)
    if [ "$OS_OSX" = "true" ]; then
        alias oo='a -e open'
        alias o='open'
    else
        alias oo='a -e xdg-open' # quick opening files with xdg-open
        alias o='xdg-open ' # easily use default program to open on x systems
    fi
fi

## Configure FZF if it is present
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Create GitHub CLI token-specific aliases, if the token files exist
[ -f ~/.github/token_personal ] && alias ghp='GITHUB_TOKEN=$(cat ~/.github/token_personal) gh'
[ -f ~/.github/token_enterprise ] && alias ghe='GITHUB_TOKEN=$(cat ~/.github/token_enterprise) gh'

# Init GitHub Copilot CLI, if installed
if [ "$(command -v github-copilot-cli)" != "" ]; then
    # load aliases ?? git? gh?
    eval "$(github-copilot-cli alias -- "$0")"
fi

# Init 1Password CLI, if installed
if [ "$(command -v op)" != "" ]; then
    eval "$(op completion zsh)"; compdef _op op
    source "$HOME/.config/op/plugins.sh"
fi

# Init Volta, if installed
if [ "$(command -v volta)" != ""]; then
    export VOLTA_HOME="$HOME/.volta"
    export PATH="$VOLTA_HOME/bin:$PATH"
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

# Define precmd_functions if not already defined
[[ -z $precmd_functions ]] && precmd_functions=()
# Enable title function as an additional precmd function
precmd_functions=($precmd_functions _title_internal)

eval "$(_META_COMPLETE=source_zsh meta)"

alias cfg='git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME"'

# Source local configs if they are present
[ -f ~/.zshrc.local ] && source "$HOME/.zshrc.local"
