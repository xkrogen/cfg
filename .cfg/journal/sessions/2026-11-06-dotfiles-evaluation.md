# Dotfiles manager evaluation — 2026-11-06

## Scope and initial inspection

Erik requested a thorough comparison of dotdrop, GNU Stow, chezmoi, and mise dot,
including Git ownership, setup scripts, OS/profile customization, separate personal
base/work overlay repositories, project health, and optional isolated experiments.
Research and a recommendation are authorized; migration is not requested.

Read agent-space notes/repository map/conventions and cfg README, init.sh,
setup.sh, and brew_standard_tools.sh. cfg is still a bare ~/.cfg.git repository
with HOME worktree, branch main, personal HTTPS origin. Existing unrelated modified
files: .agents/AGENTS.md, .config/herdr/config.toml, and
.gemini/antigravity-cli/settings.json. Preserve them and stage only this research.
No upstream is configured for main; push destination will be explicit origin/main.

Homelab docs describe the Ubuntu Desktop host operated as an always-on SSH server;
no remote host access is necessary for this research. No work repository or work
configuration contents are needed: use synthetic work overlays in experiments.
Initial API metadata: dotdrop v1.18.1, chezmoi v2.74.0, mise v2026.11.3.
Experiments and downloaded runtimes stay under /tmp/cfg-dotfiles-evaluation-2026-11-06;
retain small reproducible scripts and results in cfg, excluding third-party binaries.

## Research and sandbox results

Reviewed upstream documentation and pinned release documentation for all four tools.
Live GitHub API metadata, release cadence, top contributors and the most recent
100 default-branch commits are saved in scratch/dotfiles-evaluation/project-health.json.
GNU's current release is Stow 2.4.1 (September 8, 2024). Mise's release changelog
places the dotfiles workflow in v2026.6.6 (June 13, 2026).

Isolated runtimes installed under /tmp only: dotdrop 1.18.1, chezmoi 2.74.0,
mise 2026.11.3, Stow 2.4.1. The mise and chezmoi binary hashes match official
release checksum files. Initial installer assertion rejected mise's checksum
filename spelling (`./name` versus `name`); normalized that prefix, confirmed
the actual digest matched, and continued. This was a verifier parsing issue,
not an integrity mismatch. Dotdrop emitted an optional python-magic warning.

The initial 31 experiment assertions passed. They verified dry runs, imported
profiles and templates, same-key overrides, action/hook reruns, two independent
chezmoi states and run_once content behavior, Stow conflicts, mise conf.d repo
composition and marker blocks, and mise include's rejection of [dotfiles].
Added checks for mise server role selection and profile deactivation cleanup.
All work repositories and enterprise settings used in the fixture are synthetic.
No native Linux execution, real package setup or real dotfile changes occurred.

Preparing a recommendation of dotdrop as the conservative fit for explicit
profile/repository composition, with mise as the more integrated, younger option.
This is a proposal, not an adoption decision or executed migration.

## Final validation and delivery

All 35 assertions passed (dotdrop 15, chezmoi 6, Stow 3, mise 11). Report source
and standalone HTML are in .cfg/docs/dotfiles-evaluation-2026-11-06.{md,html}.
Erik corrected the deliverable to HTML only; no PDF was authored.

Headless Chrome review at 1512x1120 and 390x844 verified the desktop/mobile layout,
13 navigation targets, seven tables, no page-level horizontal overflow, no broken
internal anchors, no JavaScript errors, and no external asset dependencies.
Inspected desktop, matrix, and mobile screenshots. Source diff checks passed.
The revised introductory sentence and removal-link correction were regenerated.

Personal Hindsight sync_retain confirmed completed storage for document
cfg-dotfiles-evaluation-2026-11-06, with pointers, requirements, proposal status,
and experiment limits. Agent-space has only a concise cross-repository pointer.
The personal cfg GitHub repository is public (verified before push); all work
examples are synthetic, and report/evidence contain no enterprise content or
credentials. Retained artifacts contain public upstream metadata and personal
configuration research, not work configuration.

Final contract review clarified that keeping runtime files real is distinct from
cfg's current policy of tracking those files at their runtime paths. The report
now calls for a deliberate policy update before a source/destination-manager
cutover; it does not suggest that copying alone preserves the old Git model.

## Follow-up: application-written config drift

Erik narrowed the shortlist to dotdrop and mise. New explicit priority: detect
application/plugin edits to live config files and reconcile concurrent changes
across machines without losing useful changes. This is not a decision to adopt
mise or enable sync. Reviewing pinned v2026.11.3 history, sync, track, pull,
conflicts, managed-file capture docs and dotdrop update/compare behavior.
Preparing two fake machine homes and a local bare Git remote to test same-file
versus different-file changes. No live config or watcher service will be changed.

The 11 follow-up assertions now pass: initial adoption, one-shot watcher capture,
sync leaving live files untouched, pull propagation, conflict for different keys
in the same JSON file, conflict diff, non-destructive unresolved pull, manual
combined convergence, independent-file convergence, and tracking a rendered file
without changing its template followed by apply restoring the original template.

Initial harness assumptions were corrected after observed output: sync can return
zero while reporting a recorded conflict; status/conflicts and a blocked pull show
it. Independent-file convergence also requires the next sync after pull to publish
the combined history. No data-loss bug was observed.

Saved docs/dotfiles-drift-reconciliation.md, fixtures and results; qualified the
original HTML/Markdown recommendation because the new requirement strengthens
mise's case. Agent-space's pointer reflects the narrowed shortlist. Only the
one-shot watcher was exercised, with a local remote; no background OS service,
live agent config, network history origin, or real work data was involved.

Personal Hindsight sync_retain confirmed the narrowed shortlist, new drift
priority, provisional ranking, and verified follow-up results with source pointers.
Updated HTML link and desktop/mobile structural checks passed; staged diff checks
passed. No live configuration edits or services were introduced.
