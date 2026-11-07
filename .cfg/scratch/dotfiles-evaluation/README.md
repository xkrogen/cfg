# Dotfiles evaluation fixtures

Research date: November 6, 2026 (America/Los_Angeles).

`evaluate.py` creates independent synthetic Git repositories and fake HOME/XDG
roots in a new temporary directory. It never reads real work configuration or
runs real package installers/services. Tool runtimes must be supplied explicitly.

Verified versions:
- dotdrop 1.18.1, installed in an isolated Python virtual environment from PyPI
- chezmoi 2.74.0, official darwin-arm64 release binary
- mise 2026.11.3, official macos-arm64 release binary
- GNU Stow 2.4.1, built into a temporary prefix from the GNU release source tarball

The two release binaries were matched against their release's SHA-256 checksum
files. This verifies download integrity, not an independently authenticated
signature. Stow source was downloaded over HTTPS; recorded SHA-256:
`2a671e75fc207303bfe86a9a7223169c7669df0a8108ebdf1a7fe8cd2b88780b`.
The dotdrop run warned that optional `python-magic` was absent; the exercised
text deployment/profile/action behaviors passed without it.

Example invocation (paths refer to this research session's temporary runtimes):

```sh
python3 ~/.cfg/scratch/dotfiles-evaluation/evaluate.py \
  --runtime-dir /tmp/cfg-dotfiles-evaluation-2026-11-06 \
  --output ~/.cfg/scratch/dotfiles-evaluation/results.json
```

`results.json` records every CLI command, return code, output, and assertion.
`project-health.json` records live GitHub API metadata, releases, and a bounded
sample of the most recent 100 default-branch commits. Author-name counts include
bots, merge authors, and identity variations and are not contributor headcounts.
Stow's GitHub mirror is not a complete measure of its GNU ecosystem.

Linux/server profiles were simulated as configuration data on macOS arm64.
No native Linux deployment, real work overlay, secret-manager authentication,
root-managed files, package installation, or production migration was tested.
