# Shared agent skills

Skill scope is defined by discovery directory:

| Directory | Scope | Source repository |
| --- | --- | --- |
| `~/.agents/skills` | Shared generic methods for Copilot and Codex | Personal cfg; sources here under `.cfg/agents/skills` |
| `~/.copilot/skills` | Work-specific skills | Work cfgli/overlay |
| `~/.codex/skills` | Personal Codex-specific skills | Personal cfg |

The shared wrap-up/handoff, coding-guidelines, and disk-cleanup sources are linked
into `~/.agents/skills`. There are no duplicate installations of these skills in
Copilot/Codex-specific roots. The old separate handoff is folded into wrap-up.

Shared methods must respect the current task's context. Work notes stay in work
systems; personal notes default to agent-space unless project-specific. Personal
Git defaults must not replace work review rules. Credentials, histories, artifacts,
indexes, and authorization do not become shared merely because a skill is shared.

Use `python3 ~/.cfg/scripts/install_codex_personal.py` to recreate the shared links
and personal Codex global instruction link. It removes only recognized formerly
managed Codex links, preserving unrelated or conflicting files. Copilot copy
removal is an explicit, separately tracked migration rather than a blanket cleanup.

gh-stack, diagramming, make-pages-interactive, public-docs, skill-simplifier, and
voice-transcription are review candidates, not installed shared skills. Their
review and decisions belong in agent-space until adoption.
