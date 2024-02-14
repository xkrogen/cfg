# .bashrc

export PATH="$PATH:/home/linuxbrew/.linuxbrew/bin:$HOME/bin"

alias cfg='git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME"'

# Source local configs if they are present
[ -f ~/.bashrc.local ] && source "$HOME/.bashrc.local"
