---
name: oss
description: Work safely with external open-source repositories. Use for cloning, editing, filing issues, or contributing to public GitHub repositories; enforces scoped xkrogen authentication, personal-fork workflows, repository-native contribution rules, and enterprise confidentiality boundaries.
---

# Open-source repository workflow

Use this skill for any external open-source repository. The repository's own
contribution and development rules control the work. Do not import enterprise-wide
development workflows, conventions, tooling, review requirements, branch names,
task-tracking systems, or internal documentation references into an OSS project.
Follow practices required by that public repository itself.

## Non-negotiable rules

1. Use the `xkrogen` GitHub account for every `gh` command targeting GitHub.com.
   Run:

   ```bash
   "$HOME/.agents/skills/oss/scripts/gh-oss" <gh arguments>
   ```

   `gh-oss` obtains `xkrogen`'s stored GitHub.com token and passes it only to
   the delegated command. It leaves the global active `gh` account unchanged.
   Never run `gh auth switch`, `gh auth login`, `gh auth logout`, or `gh auth
   refresh`; never print, persist, or export a GitHub token.

2. Contribute from the personal `xkrogen` fork, not a branch pushed to the
   canonical repository. Name branches for the work, such as
   `fix-parser-overflow` or `docs/clarify-installation`; do not prefix them
   with a username.

3. Before editing, filing an issue, opening a PR, or making any external
   change, discover and follow the repository's current rules. The repository
   may require a signed CLA, DCO sign-off, a security disclosure path, a PR
   template, generated-file workflow, specific validation, or a particular
   commit style.

4. Treat every external surface as public. Do not disclose or upload enterprise
   confidential information, internal source or configuration, customer or
   employee data, credentials, tokens, internal URLs, operational details,
   security-sensitive information, or enterprise-only processes. This applies
   to code, patches, comments, issue/PR text, commit messages, logs,
   screenshots, configuration, hooks, and automation.

5. Do not install or run third-party plugins, hooks, scripts, or MCP
   integrations unless they are approved and verified. Prefer the
   repository's documented, already-present tooling.

## 1. Establish the repository and authentication

Identify the canonical `OWNER/REPO`, its default branch, and whether an
`xkrogen/REPO` fork already exists. Use the wrapper for all GitHub CLI
operations:

```bash
gh_oss="$HOME/.agents/skills/oss/scripts/gh-oss"
"$gh_oss" repo view OWNER/REPO
"$gh_oss" repo view xkrogen/REPO
```

If the personal fork does not exist, create it non-interactively:

```bash
"$gh_oss" repo fork OWNER/REPO --clone=false
```

Clone the personal fork and retain the canonical repository as `upstream`:

```bash
git clone git@github.com:xkrogen/REPO.git
cd REPO
git remote add upstream https://github.com/OWNER/REPO.git
git fetch upstream
```

If the repository is already cloned, inspect remotes before changing them.
`origin` must point to `xkrogen`'s fork and `upstream` to the canonical
repository. Do not overwrite an existing remote blindly.

## 2. Read the repository's rules first

Search the checkout, excluding Git internals, for contribution and governance
documents:

```bash
find . -path './.git' -prune -o -type f \( \
  -iname 'contributing*' -o -iname 'development*' -o -iname 'hacking*' -o \
  -iname 'security*' -o -iname 'code_of_conduct*' -o -iname 'governance*' -o \
  -iname 'maintainers*' -o -iname 'pull_request_template*' \
\) -print | sort
```

Read the results plus the README, relevant package/build documentation, and
the applicable `.github/` configuration. Also inspect nearby code, tests, and
recent commits for conventions the written guidance does not cover.

Follow security guidance exactly: report vulnerabilities through the specified
private channel rather than opening a public issue. If a CLA, DCO, or other
contributor agreement is required and has not been completed, pause before
external submission.

## 3. Develop against upstream

Start from the current upstream default branch and create a descriptive branch:

```bash
git switch --create fix-parser-overflow upstream/main
```

Replace `main` and the branch name with the repository's actual convention.
Follow its formatting, generation, test, documentation, commit, and
sign-off requirements. Run its documented validation before creating a PR.
Do not impose enterprise-specific automated reviews, commit prefixes, task-tracking
references, internal documentation links, PR templates, or checks.

Push only to the personal fork:

```bash
git push --set-upstream origin fix-parser-overflow
```

## 4. Make external changes through the fork

Before an issue or pull request, perform a final public-information review.
Remove any internal context and make the report self-contained using only
publicly shareable facts.

Create an issue with the wrapper and the repository's required template:

```bash
"$gh_oss" issue create --repo OWNER/REPO --title "..." --body-file issue.md
```

Create a pull request against the canonical repository from the personal fork:

```bash
"$gh_oss" pr create \
  --repo OWNER/REPO \
  --head xkrogen:fix-parser-overflow \
  --base main \
  --title "..." \
  --body-file pr-body.md
```

Use the canonical repository's actual default branch and PR-template content.
Do not open a PR, issue, or remote mutation if the repository rules or the
public-information boundary are not satisfied.

## Completion checks

- Every GitHub CLI command used `gh-oss` and therefore `xkrogen`'s
  per-command authentication.
- Global `gh` authentication was not changed.
- The contribution branch was pushed only to the `xkrogen` fork.
- Repository-native contribution, security, validation, and template rules
  were followed.
- All externally visible content contains only publicly shareable information.
