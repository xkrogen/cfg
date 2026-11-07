# Personal Hindsight reminders

The runtime script `~/.codex/hooks/hindsight_reminder.py` is tracked directly by
cfg. Run `/usr/bin/python3 ~/.cfg/scripts/install_hindsight_hooks.py` after
restoring cfg on a machine to append registrations to `~/.codex/hooks.json`.
The installer preserves other hooks and is idempotent. Machine-specific hook
registrations, authentication and trust state remain outside Git.

SessionStart (all sources, including compaction) reminds the agent to recall
relevant personal context. UserPromptSubmit reminds it to recall for new topics
and retain durable knowledge with provenance and confirmed writes. These are
model reminders, not guaranteed enforcement of MCP calls. The script has no
network access and does not read prompts, transcripts or other task files.

Prerequisites: Python 3 at `/usr/bin/python3`, enabled authenticated Hindsight
MCP bank xkrogen, enabled Codex hooks, and user review/trust of the new handlers.
Use `/hooks` in Codex CLI or Settings > Hooks in the desktop app, then start or
resume a chat to verify lifecycle delivery. Direct script checks alone do not
establish live delivery.

According to https://learn.chatgpt.com/docs/hooks (checked 2026-11-06), local-only
Work and Codex threads support local hooks when orchestration and execution are
local. Cloud orchestration ignores local hooks; its enterprise Global MCP hooks
require workspace admin configuration and are unavailable to personal accounts.
This setup does not configure those enterprise hooks or authorize work ingestion.
