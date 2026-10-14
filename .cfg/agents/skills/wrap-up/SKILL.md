---
name: wrap-up
description: Close out a work or personal session or prepare a handoff by updating durable context, recording outcomes and next steps, and completing the authorized Git workflow. Use when Erik asks to wrap up, save session context, or hand work to another agent.
---

# Shared wrap-up and handoff

Leave enough current, durable context for the next agent to continue without the
chat transcript. Read the repository's instructions and recent session notes first.

## Where the record belongs

Determine whether the current task is work or personal from the active agent and
repository context. For work, use the work project's instructions and authorized
systems; never put work notes into personal agent-space/homelab. For personal work,
default decisions and notes to **agent-space**. If the work is specific
to homelab or another project with its own Git repo, record it there. For system
initialization/dotfiles, cfg owns the configuration; keep general context pointers
in agent-space. Locate repositories from the current workspace or agent-space's
repository map; do not create a second workspace because a machine path differs.

This shared skill provides a method, not shared task memory or authorization.
Keep Copilot work and personal Codex context/accounts/artifacts separate. Use the
current authorized session and its artifacts, without cross-context history searches.

## Close out the work

- Append actual outcomes, decisions, meaningful failures, unresolved work, and
  useful artifact references to the existing session log under local conventions.
  Do not rewrite earlier journal entries. If a record is missing, create one and
  identify retrospective notes as such rather than implying incremental capture.
- Update maintained docs in place to reflect current facts and plans, including
  corrections to stale statements. Distinguish proposed, prepared, executed, and
  verified state. Preserve external sources of truth with pointers rather than
  competing copies.
- Record the next concrete action, prerequisites, and blockers. Include only the
  commands/paths needed to resume; reference existing artifacts instead of pasting
  them repeatedly. Keep credentials and sensitive raw content out of the record.
- Include only decisions supported by the session. Do not invent missing results,
  run unrelated fixes, or install a memory system to complete a handoff.

## Git and delivery

Follow the active project's Git/publication workflow. For work, preserve its review
and publication requirements; do not apply personal defaults. For personal work,
repos are agent-managed with **no PRs**. Commit and push directly to
master normally. If parallel work uses a feature branch, coordinate its completed
work for squash integration into master; do not merge another agent's unfinished
branch or disturb its edits. Respect an explicitly documented legacy branch while
alignment is pending. Stage intended files, especially with cfg's home worktree.

Use the remote appropriate to the active work/personal context and authorization;
never infer that credentials or visibility carry across contexts. If no remote is
configured, retain the commit and report the missing destination. Do not create a hosted repo or guess
visibility. If a push fails, record the real error and preserve the local commit.

Finish with a short continuation summary: outcome, durable paths, commit/push
status, and next action/blocker. Ask about the next session's goal only if it is
materially unclear; no routine confirmation is needed for already authorized
documentation or Git work.
