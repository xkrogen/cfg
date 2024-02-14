# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
	. ~/.bashrc
fi

# User specific environment and startup programs

export PATH="$PATH:/home/linuxbrew/.linuxbrew/bin:$HOME/bin"

alias cfg='git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME"'

# Source local configs if they are present
[ -f ~/.bash_profile.local ] && source "$HOME/.bash_profile.local"

if command -v zsh &>/dev/null && [[ "$SHELL" != "$(command -v zsh 2>/dev/null)" ]] && [[ "$DISABLE_ZSH" != "true" ]]; then
  export SHELL="$(command -v zsh)"
  exec $SHELL --login
fi
