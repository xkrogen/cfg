---
name: coding-guidelines
description: Apply Erik's code-quality preferences to substantive implementation, refactoring, or code review. Focus on clear contracts, existing patterns, scoped solutions, and meaningful validation; not a required ceremony for trivial edits.
---

# Shared coding guidelines

Read applicable project instructions and nearby code before choosing a design.
Use these decision criteria in the work; do not dump a checklist into every reply.

## Design and scope

- Look for existing utilities, domain types, tests, and established patterns before
  introducing parallel machinery. A dependency needs a concrete advantage; do not
  add one merely because reuse is generally desirable.
- Make the smallest complete change that satisfies the actual request. Avoid
  speculative configuration, abstractions, fallback paths, and unrelated cleanup.
  An optimization should preserve semantics unless behavior change was requested.
- Make invariants and ownership clear: units/ranges, nullability, mutation, resource
  lifetime, concurrency, ordering, and failure behavior where they matter. Prefer
  names and types that carry the contract over comments compensating for ambiguity.
- Handle errors at a useful boundary. Preserve diagnostic context and meaningful
  failures; do not silently substitute a guessed result or retry without a reason
  to expect new information. Match defensive checks to real input/trust boundaries.

## Explanations and documentation

Document non-obvious contracts, rationale, tradeoffs, and surprising behavior.
Describe the code's current behavior, not an edit history or the mechanics a reader
can see. Do not add rote docstrings or comments to every member. Keep examples and
public interfaces consistent with implementation.

## Verification and review

Choose checks that establish the requested behavior and relevant invariants.
Run required project checks. For meaningful logic changes, cover realistic success,
failure, boundary, and regression cases as appropriate; avoid tests that merely
repeat implementation or assert incidental wording. Do not add ritual tests for
reversible, low-impact edits.

Treat review suggestions as evidence to assess against the real contract. Fix
concrete defects; explain when a suggestion adds speculative complexity or changes
scope. Once sufficient checks pass, continue to completion rather than repeatedly
testing without a new concern. Report actual checks, failures, and remaining limits.

Follow the active repository's Git and publication conventions. In personal repos,
use agent-managed no-PR integration: direct master commits/pushes normally and
feature branches with squash integration for parallel work, honoring documented
legacy branches. In work repos, follow work review/publication rules instead.
Sharing these methods does not authorize moving code, context, or credentials
between work and personal systems.
