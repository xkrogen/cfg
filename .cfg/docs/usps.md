# USPS skill ownership

The USPS repository (`xkrogen/usps`, `assets/agent-mailbox/`) owns `/usps`.
Its daemon installs/updates the single shared tree at `~/.agents/skills/usps`.
The main skill contains common commands and protocol; agent-specific guidance
lives in separate references. Do not maintain a second source in cfg or copy
runtime skill edits back into cfg. Change the USPS repository and deploy instead.

cfg owns generic shared methods and the personal Codex hook configuration.
USPS private hook configs and daemon/skill installation state remain outside Git.
The daemon preserves old recognized skills in private rollback storage outside
skill discovery. This project-owned source is Erik's explicit October 27 decision.
