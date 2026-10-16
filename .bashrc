# .bashrc

export PATH="$PATH:/home/linuxbrew/.linuxbrew/bin:$HOME/bin"

alias cfg='git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME"'

# Volta (Node toolchain manager). Keeps an existing VOLTA_HOME and adds its
# bin to PATH only once, so re-sourcing does not grow PATH.
export VOLTA_HOME="${VOLTA_HOME:-$HOME/.volta}"
case ":$PATH:" in
  *":$VOLTA_HOME/bin:"*) ;;
  *) export PATH="$VOLTA_HOME/bin:$PATH" ;;
esac

# Source local configs if they are present
[ -f ~/.bashrc.local ] && source "$HOME/.bashrc.local"
