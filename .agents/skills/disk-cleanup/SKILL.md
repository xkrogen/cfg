---
name: disk-cleanup
description: Inspect and reclaim local disk space when Erik explicitly requests cleanup. Identify exact targets, preserve valuable state, perform authorized deletion narrowly, and verify results. Not for formatting disks, flashing installers, or routine unrelated maintenance.
---

# Shared disk cleanup

Start with read-only inspection of the actual machine and requested scope. Use
appropriate installed tools to establish free space and the largest relevant
directories; for example, filesystem usage plus a filesystem-bounded size inventory
of the requested tree. Avoid scanning all private histories or reading contents
when names, sizes, timestamps, and repository state suffice.

## Identify safe candidates

Distinguish regenerable caches/build outputs from source, user documents, personal
media, databases, credentials, VM/container volumes, and backups. Check whether
paths cross filesystem boundaries or are symlinks before traversing them. Label
estimates and state what regeneration or lost state would cost.

For Git checkouts/worktrees, inspect dirtiness, untracked files, branch ownership,
and work in progress. A merged PR, old timestamp, or branch name does not establish
that a directory is disposable. Never delete dirty worktrees, local commits,
untracked artifacts, or shared dependency stores merely to meet a space target.

Enumerate worktrees completely. Do not depth-cap the search or trust a partial
count. Find every main repo with a bounded search for `.git` entries, then run
`git worktree list --porcelain` in each. Include worktrees nested inside other
repos and under session/artifact directories, which are easy to miss.

Classify each worktree by its branch's PR state, using
`gh pr list --repo <owner/repo> --head <branch> --state all`. Derive the repo
from the origin URL. Handle the buckets as follows:
- MERGED and clean: removable after a recheck.
- MERGED but with untracked or dirty files: list the files and ask first.
- CLOSED without merge, OPEN, or no PR: list them with size, dirty count, and
  unpushed count, then get explicit approval. Pushed does not mean merged.

Detect unpushed commits with `git log HEAD --not --remotes`. Do not use
`@{u}..`, which returns nothing when the branch has no upstream and hides the
unpushed work.

Remove approved worktrees with `git worktree remove <path>` (add `--force` only
when the user approved the dirty state), then `git branch -D <branch>` in the
owning main repo, then `git worktree prune`. Never `rm -rf` a worktree. Some
approved removals discard uncommitted work, so state that cost explicitly before
acting.

Build-tool caches (Gradle, Maven, and similar) are shared. Before removing a
version-specific cache, check for a running daemon (for example `gradle --status`
or `ps`). Caches such as `build-cache-*` and `.tmp` are regenerable; removing
them slows the next builds while they refill.

Versioned extraction directories (for example `*.pyz_<hash>` under a tool's
data directory) can be duplicates. Keep the newest per prefix and remove only the
older siblings after confirming they are not in use.

Do not treat synced folders as a source of free disposable data. Distinguish local
cache/eviction from deletion that propagates to Dropbox or another sync service;
obtain authorization for the actual effect. Keep Copilot/work caches and artifacts
out of personal cleanup unless the user explicitly authorizes that exact scope.

## Authorization and execution

Before destructive action, make the specific targets and consequences clear. If
Erik already authorized exact targets or a defined cleanup policy, proceed within
that scope without asking again. Broad requests to free space do not by themselves
authorize deleting source, backups, persistent data, or unrelated directories.

Recheck candidate identity/state immediately before deletion; use quoted paths and
narrow commands or the tool's own cleanup operation. Avoid broad globs, following
symlinks, filesystem-wide sweeps, and guessed platform-specific locations. Prefer
staged/preview operations where they materially reduce risk. Do not kill services,
remove volumes, rewrite Git history, or alter system configuration as hidden steps.

Stop and report permission errors or changed/uncertain targets. Do not bypass
authentication or broaden deletion after a failure. This skill does not authorize
formatting, partitioning, or overwriting devices; handle such requests under their
explicit device-identification and confirmation requirements.

## Verify and record

Check both the intended targets and filesystem free space after cleanup. Explain
differences between estimated sizes and actual reclaimed space (for example,
snapshots, open files, or shared storage); do not claim all deleted bytes became
free immediately. Report actual errors and skipped targets.

Record results in the active context's authorized repository/system without copying
sensitive listings into Git. For personal work, default to agent-space unless the
results are specific to another project repo. Work results stay in work systems;
shared cleanup methods do not authorize cross-context data or account access.
