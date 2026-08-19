# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
	. ~/.bashrc
fi

# Source local configs if they are present
[ -f ~/.bash_profile.local ] && source "$HOME/.bash_profile.local"

if [ -n "${BASH_VERSION:-}" ] && command -v zsh &>/dev/null && [[ "$DISABLE_ZSH" != "true" ]]; then
  exec "$(command -v zsh)" --login
fi
