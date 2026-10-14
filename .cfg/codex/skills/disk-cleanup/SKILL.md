---
name: disk-cleanup
description: Inspect and reclaim local disk space when Erik explicitly requests cleanup. Identify exact targets, preserve valuable state, perform authorized deletion narrowly, and verify results. Not for formatting disks, flashing installers, or routine unrelated maintenance.
---

# Personal disk cleanup

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

Record meaningful personal results in agent-space by default, or in the relevant
project repo when project-specific, without copying sensitive listings into Git.
