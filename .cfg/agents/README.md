# Shared agent skills

Skill scope is defined by discovery directory:

| Directory | Scope | Source repository |
| --- | --- | --- |
| `~/.agents/skills` | Shared generic methods for Copilot and Codex | Personal cfg; sources here under `.cfg/agents/skills` |
| `~/.copilot/skills` | Work-specific skills | Work cfgli/overlay |
| `~/.codex/skills` | Personal Codex-specific skills | Personal cfg |

The shared set is wrap-up, coding-guidelines, disk-cleanup,
gh-stack, make-pages-interactive, voice-transcription, skill-simplifier, and oss. Sources
are linked into `~/.agents/skills`; former Copilot copies are removed. Work-only
interactive-page conventions remain in cfgli's `.copilot/skill-overlays`.
Voice transcription uses the existing `voice-transcription` executable on PATH
and existing local storage; this skill migration does not relocate the helper,
recordings, authentication, ledger or transcripts.

Shared methods must respect the current task's context. Work notes stay in work
systems; personal notes default to agent-space unless project-specific. Personal
Git defaults must not replace work review rules. Credentials, histories, artifacts,
indexes, and authorization do not become shared merely because a skill is shared.

Use `python3 ~/.cfg/scripts/install_codex_personal.py` to recreate the shared links
and personal Codex global instruction link. It removes only recognized formerly
managed Codex links, preserving unrelated or conflicting files. Copilot copy
removal is an explicit, separately tracked migration rather than a blanket cleanup.

OSS preserves the xkrogen account/fork workflow with generic enterprise boundaries.
Wrap-up performs durable session closeout only; the handoff skill/capability is removed.
Diagramming remains work-only and was left unchanged. Public-docs was not
selected for sharing. Review decisions and findings belong in agent-space.
