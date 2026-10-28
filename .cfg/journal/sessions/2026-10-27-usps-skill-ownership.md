# USPS shared skill source

Erik confirmed USPS repository source-of-truth and daemon-owned machine-wide
installation, shared across coding agents with separate agent references.
Deployment to Mac/homelab verified all three installed skill digests and retired
old recognized `agent-mailbox` trees to rollback storage. Removed the old cfg
tracked copy; the new runtime tree is generated from USPS, not a cfg-owned source.
See `docs/usps.md` and USPS `docs/session-log.md`. Other pending cfg changes were
left untouched. cfg's existing branch remains main; no default rename performed.
