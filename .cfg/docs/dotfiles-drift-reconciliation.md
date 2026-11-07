# Application-written dotfile drift: dotdrop and mise

November 6, 2026 follow-up to the dotfiles evaluation. Erik narrowed the shortlist
to dotdrop and mise. Explicit new priority: see application/plugin changes to live
configuration and reconcile concurrent changes across machines. No adoption or
live synchronization was authorized or performed.

## Three comparisons that should remain distinct

- Desired configuration versus live output: dotdrop compare; mise dot diff/status
  for deployed entries. Answers whether the live file differs from its source.
- Current live content versus last saved snapshot: mise dot history diff/status
  for tracked entries. Once the watcher saves a change, it is no longer unsaved.
- Changes since a reviewed baseline: compare named/numbered history checkpoints
  or the curated configuration repo. Autosaving is not an approval workflow.

## Mise history, watcher, and synchronization

`mode = "track"` leaves an existing regular file where the application reads and
writes it. `mise dot track <path>` saves an initial checkpoint; `mise dot save`
saves explicitly. The foreground watcher or a configured user service records
settled application edits. `mise dot history` and `history diff` inspect versions.
A before/after operation can be captured with `mise dot capture --label <label>
-- <command>`; this checkpoints tracked file contents, not installed packages.

History uses a separate bare Git store. An origin must have compatible history
(or be empty); pointing it at an existing conventional cfg branch does not merge
the two models. A private history repo or dedicated branch is a deliberate choice.

Commands have separate effects:
- `mise dot sync`: exchanges saved history; does not rewrite live files.
- `mise dot pull`: applies fetched tracked contents.
- `mise dot apply`: generates deployed targets from their local sources.

Watcher modes: manual saves locally but makes no automatic network changes;
fetch-only fetches automatically without publishing/applying; sync publishes and
pulls automatically when allowed. Manual sync still exchanges every accumulated
saved checkpoint, including intermediate edits; it is not selective publication.

Concurrent changes to the same path are conflicts even when separate JSON keys
changed. Conflicts pause publication/application while saves and fetching continue.
`mise dot conflicts <path>` shows differences; edit the live file to combine the
results, save it, then resolve with `mise dot pull --keep-local <path>`. Afterwards
sync publishes the resolved history. Use status rather than assuming sync's exit
code alone reports outstanding conflicts: observed sync returned zero with a
conflict warning; the unresolved pull returned one.

For independent edits to different files, the tested flow was sync, pull, then
sync again to publish the combined history, followed by the other machine's
sync/pull. The watcher schedules these passes automatically in sync mode.

## What history does not solve

Tracking a template's generated destination does not infer source-template changes.
An application edit can be checkpointed and still be overwritten by the next
apply of the unchanged template. Copy-mode capture (`mise dot add` or
`mise dot add --changed`) is a separate operation; template capture is refused
by default. Review and change the template yourself.

Prefer limited ownership for app-rewritten configuration: mise's structured merge
entries own selected keys while preserving unrelated application keys. Nested
objects merge recursively, but arrays are replaced and this is not a semantic
plugin-list union. Preserve app changes by keeping those keys outside the owned
source, or explicitly promote the desired change into it.

Tracked variants separate whole versions by OS, profile, or machine. They are not
access-control boundaries: variants still enter the same shared origin. An
inspected history store has one configured origin, so do not assume multiple
source repos imply separated personal/work history. Keep separate trust domains
or local-only tracking; do not sync work data into a personal history origin.

## Dotdrop comparison and recommendation effect

Dotdrop compare reports drift from the selected profile. Update copies a changed
plain file into its source; review the Git diff and commit it, then use Git to
reconcile machine edits. Templated output requires manually adapting its source;
update's show-patch workflow helps, but is not reverse templating. Application
include files and narrow file ownership can reduce collisions with either tool.

This requirement strengthens mise's case, beyond its package/setup facilities.
The initial dotdrop recommendation is now provisional: compare dotdrop's explicit
review-before-commit approach with mise's live-file history plus manual sharing.
A sensible pilot would use specific non-secret app-written personal configs,
a local watcher, manual synchronization, and a separate private history origin.
Keep templated desired settings distinct from observed application mutations.
No pilot on real files or remote history repository has been performed.

## Evidence and primary sources

Pinned runtime: mise 2026.11.3 on macOS arm64, two synthetic HOME/XDG roots and a
local bare Git remote. Script and detailed outputs:
`~/.cfg/scratch/dotfiles-evaluation/evaluate-history.py` and `history-results.json`.
No background service was installed. The watcher test used `watch --once`;
continuous debounce/service behavior is documented rather than tested here.

- [History and watching](https://mise.jdx.dev/dotfiles/history.html)
- [Synchronization and variants](https://mise.jdx.dev/dotfiles/sync.html)
- [Pull conflict handling](https://mise.jdx.dev/cli/dotfiles/pull.html)
- [Managed-source capture](https://mise.jdx.dev/dotfiles/managed.html#capturing-changes)
- [Partial-file structured edits](https://mise.jdx.dev/dotfiles/edits.html)
- [Dotdrop compare and update](https://dotdrop.readthedocs.io/en/latest/usage/)

Initial experiment harness assumptions were corrected: conflict detection is
reported in sync warnings/status, not necessarily a failing sync exit code;
and a post-pull sync is needed to publish combined independent-file history.
These were test-harness expectations, not observed data-loss bugs.
