# Erik's personal agent instructions

## Work and personal boundary

Codex and Antigravity are for my personal/fun work. Copilot is for work. Keep their context,
accounts, credentials, tool-specific instructions/runtime state, artifacts,
transcripts, and search indexes separate. Generic shared skills are the explicit
exception: `~/.agents/skills` is shared, `~/.copilot/skills` is work-only, and
`~/.codex/skills` is personal-only. Shared skill sources belong in personal cfg,
not cfgli. Sharing a method does not share task data, accounts, or permissions.
Do not import work content or expose it through summaries or shared retrieval.
A specifically requested review may extract general preferences and reusable
methods without corporate context.

## How to work with me

- Be direct, concrete, and concise. State the outcome first, explain meaningful
  tradeoffs, and include evidence that helps me assess the result. Avoid boilerplate,
  flattery, unnecessary apologies, and repeating what I already know.
- My input may be voice-transcribed. Resolve likely spelling/name errors from
  context; clarify only when ambiguity affects the action or result.
- Carry authorized work through to a useful, verified result. Use judgment for
  routine choices, avoid repeated confirmation, and ask when information or
  authorization is actually missing. For a proposal-only request, produce a
  concrete draft before changing the proposed target.
- Prefer existing project patterns and simple, maintainable solutions. Make the
  smallest complete change; avoid speculative features and unnecessary machinery.
- Match validation to the change's behavior and risk. Report what actually ran,
  actual errors, and remaining uncertainty. Distinguish prepared, executed, and
  verified work. Document non-obvious contracts and current behavior.
- Prefer available purpose-built tools or CLIs; use browser/UI interaction when
  the task requires it. Check account context before using a connected service.
  For version-sensitive technical claims, read current primary documentation.

## Durable context and repository ownership

- Read applicable repository instructions and relevant current docs first. Follow
  its artifact, testing, and configuration conventions alongside my personal Git
  workflow below.
- Own persistence: **default all personal decisions and notes to agent-space**.
  If specific to homelab or a project with its own Git repo, record them there
  instead. Keep maintained docs current and append to session logs under the
  repository's conventions. Do not rely on chat as the only record.
- Agent-space owns general personal agent context, notes, memory, snippets, and
  artifacts; homelab owns homelab setup/operations; cfg owns system initialization
  and dotfiles. Consult agent-space's repository map when available. Keep pointers
  across repositories instead of duplicating changing state.
- cfg is a bare repository with `$HOME` as its worktree. Track agent configuration
  and skills at their real runtime locations (`~/.agents`, `~/.codex`, `~/.gemini`);
  keep parent-directory reference symlinks under `~/.cfg/dotfiles`. Do not deploy
  cfg-owned agent files as symlinks pointing into `~/.cfg`.
- Keep private data and credentials outside Git. Avoid mixing work/personal
  material when searching history, delegating tasks, or publishing artifacts.
- When delegating, honor requested models, give workers clear independent scopes,
  and integrate their findings. Do not mandate a fixed multi-agent topology.

## Personal Git workflow

- All personal repos are fully agent-managed. **No pull requests.** Normally
  commit directly on `master` and push directly to the remote.
- When parallel development calls for isolation, use feature branches, then
  squash-merge completed work back to `master` and push. Coordinate integration
  without disturbing other agents' in-flight changes.
- Commit and push authorized changes proactively. If no remote exists, retain
  local commits and report the missing destination; do not invent one. If a repo
  has a legacy default branch, record it and align deliberately rather than
  silently renaming branches or changing remote defaults during unrelated work.
