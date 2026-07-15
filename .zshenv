# Read by every zsh invocation -- login, interactive, or not -- unlike
# .zshrc, which OpenSSH's non-interactive `ssh host 'cmd'` form skips
# entirely. herdr's `--remote` reattach runs its remote-client-bridge
# exactly that way, so without this file, that bridge (and any herdr
# server it auto-spawns) inherits a bare system PATH. That breaks
# anything that execs a binary directly with no shell in between, e.g.
# herdr's `agent.start` socket API (confirmed via herdr source: see
# ~/.copilot/session-archive or ekrogen-misc journal for the investigation).
#
# Keep this file to essential PATH entries only. Interactive-only setup
# (prompt, aliases, keybindings, completions) belongs in .zshrc/.zshrc.local.
for _dir in \
    "/home/linuxbrew/.linuxbrew/bin" \
    "/opt/homebrew/bin" \
    "$HOME/.local/bin" \
    "$HOME/.copilot/bin" \
    ; do
    case ":$PATH:" in
        *":$_dir:"*) ;;
        *) [ -d "$_dir" ] && PATH="$_dir:$PATH" ;;
    esac
done
unset _dir
export PATH
