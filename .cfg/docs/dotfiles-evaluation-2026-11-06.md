# A better home for your dotfiles

Dotdrop, GNU Stow, chezmoi, and mise dot · Research and sandbox evaluation · November 6, 2026

## Recommendation

**Follow-up qualification:** You have since narrowed the shortlist to dotdrop and mise and emphasized application-written config drift across machines. That strengthens mise's case and makes the initial recommendation below provisional. See [the drift and reconciliation follow-up](dotfiles-drift-reconciliation.md), including 11 additional two-machine history checks.

**Choose dotdrop for the cfg migration. Keep mise as the strongest alternative if you want to consolidate machine setup, package management, and development runtimes.**

Dotdrop most directly matches your critical requirement: a personal base and a private work overlay in separate Git repositories, composed through explicit profiles and templates. It can retain your existing setup scripts and deploy regular files where your current agent configuration expects them. Its smaller community is active, and its approach has a substantially longer history than mise's dotfiles subsystem.

Mise is a close second. Its current implementation passed the same repository-composition experiment and has the richest setup facilities. I would choose it instead if reducing the number of tools and hand-written setup steps matters more than the maturity of the dotfiles-specific workflow. This is a judgment about your priorities, not a measured reliability ranking.

Chezmoi has the strongest established dotfiles-specific ecosystem here, but separate repositories require composition conventions around its deliberately single-source design. Stow is dependable at symlinking; it leaves too much of your requested functionality to scripts you would maintain. The detailed evidence follows. [Dotdrop project](https://github.com/deadc0de6/dotdrop), [chezmoi design](https://www.chezmoi.io/user-guide/frequently-asked-questions/design/), [mise dotfiles launch](https://github.com/jdx/mise/releases/tag/v2026.6.6), [Stow manual](https://www.gnu.org/s/stow/manual/stow.html).

**Status:** research completed; 35 sandbox checks passed. No manager adopted, no production dotfiles migrated, and no work repository read.

## What your replacement actually needs to handle

I inspected the personal cfg README, tracked path inventory, `init.sh`, `setup.sh`, and `brew_standard_tools.sh`. The live arrangement remains a bare `~/.cfg.git` database with your home directory as its worktree. Its branch is `main`, and its personal origin is `xkrogen/cfg`. Existing unrelated edits were preserved.

Your setup has two distinct responsibilities:

| Responsibility | Examples in your current cfg | What the replacement should provide |
| --- | --- | --- |
| Deliver configuration | Shell configuration, tmux, Git settings, shared skills, agent instructions, local launchers | Select files by machine; render differences; preserve permissions and deliberate links |
| Prepare a machine | Homebrew formulae/casks, Volta and Pyright, jdtls, native px0 and terminal-browser installers, Herdr integrations, Oh My Zsh, tmux plugins | Order setup operations, rerun safely, distinguish installation from update |

Your homelab documentation describes the Dell OptiPlex running Ubuntu Desktop as an always-on machine administered through SSH. That makes **server versus laptop** an independent dimension from **Linux versus macOS**: you should not infer the desired package set from the OS alone. I used the existing local docs; I did not connect to or change that host.

The design should express these dimensions separately:

| Machine | Context | Platform | Role | Configuration sources |
| --- | --- | --- | --- | --- |
| Personal laptop | Personal | macOS / arm64 | Laptop | Personal base + Mac + laptop + personal-agent selections |
| Work computer | Work | Its actual platform | Workstation/laptop | Shared base + applicable platform/role + private work repo |
| Homelab | Personal | Linux / x86_64 | Server | Personal base + Linux + server + personal-agent selections |

The work row is a design target, not an inspection of enterprise configuration. Generic reusable methods can be shared; enterprise settings, credentials, Copilot state, and work-specific instructions remain work-owned.

**Git requirement:** desired configuration, templates, scripts, and profile definitions can all live in Git with any of these tools. They do not make credentials, installed binaries, caches, or local execution databases appropriate Git content. For reproducibility, track the machine/profile selection or the manifest that generates it as well; do not leave important desired state only in an undocumented local setting.

## Comparison at a glance

“Native” means the tool supplies the mechanism; it does not mean it clones and authenticates every repository automatically.

| Requirement | dotdrop | GNU Stow | chezmoi | mise dot |
| --- | --- | --- | --- | --- |
| Git-owned source files | Yes; ordinary Git repo | Yes; ordinary Git repo | Yes; Git-aware workflow | Yes; ordinary source repo, plus optional separate history store |
| Templates | Jinja2 | None | Go templates | Tera |
| OS / context / role selection | Named profiles, includes, variables | Select packages in your own wrapper | Template data and ignore rules | Config environments, variants, template functions |
| Separate base and private overlay repos | Native config imports | Multiple source directories | Supported patterns need orchestration | Native config discovery across linked repo folders |
| Whole-file override | Override the same dotfile key | Conflict; choose one package yourself | Apply order or composed source tree | Higher-precedence declaration wins |
| Contribute to the same file | Template composition or application includes | Application includes or external renderer | Template composition or application includes | Managed blocks, lines, structured key merges |
| Run setup scripts | Pre/post actions; explicit rerun policy | External wrapper | Normal, once, or content-change scripts | Tasks and bootstrap phase hooks |
| Declarative host packages | Script it | Script it | Script/template package manifests | Built-in bootstrap package facilities |
| Regular files at runtime | Default | No; symlinks are the mechanism | Default | Copy/template modes; default is symlink |
| Main tradeoff for you | Smaller ecosystem; setup remains partly scripted | You build profiles, templates, and setup | Repository composition fights the default model | Younger dotfiles subsystem; broader configuration surface |

Feature sources: [dotdrop templates](https://dotdrop.readthedocs.io/en/latest/template/templating/), [profiles](https://dotdrop.readthedocs.io/en/latest/config/config-profiles/), [actions](https://dotdrop.readthedocs.io/en/latest/config/config-actions/); [Stow manual](https://www.gnu.org/s/stow/manual/stow.html); [chezmoi machine differences](https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/) and [scripts](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/); [mise managed files](https://mise.jdx.dev/dotfiles/managed.html), [configuration](https://mise.jdx.dev/configuration.html), and [bootstrap](https://mise.jdx.dev/bootstrap.html).

## The important distinction: three kinds of layering

**Adding different files** is straightforward. For example, one repo owns `~/.config/shell/common.zsh`, and the work repo owns `~/.config/shell/work.zsh`. All four tools can support this arrangement.

**Replacing a whole file** needs a defined winner. Dotdrop can override a shared dotfile key. Mise can resolve competing declarations before deployment. Stow rejects the collision. Two independent chezmoi applies can replace the file in turn; the next base apply can undo the work version. Those behaviors were observed in the sandbox.

**Combining content inside a file** needs a stronger contract. Prefer an application's own include mechanism where practical: a shared shell entrypoint can source separate fragments, and a Git configuration can include a separate local/work file. This makes ownership understandable whichever manager you choose. Mise also offers native partial-file edits, which I tested with two separately managed blocks and an existing manual line. [Mise partial-file edits](https://mise.jdx.dev/dotfiles/edits.html).

Separate Git repositories provide access and ownership boundaries. Once deployed on a work machine, both layers' selected outputs may legitimately coexist. The essential boundary is that work content never enters the personal repository, research artifacts, or personal memory.

## Dotdrop: the most direct fit

### Profiles and repository composition

Dotdrop uses YAML declarations and a directory of source files. `import_configs` brings another configuration's dotfiles, profiles, actions, and related definitions into the importing configuration. Source paths remain associated with their configuration. This works with independently cloned sibling repositories; neither needs to be nested inside the other. I verified that arrangement with two real, synthetic Git repositories. [Configuration imports](https://dotdrop.readthedocs.io/en/latest/config/config-config/).

Profiles can include other profiles, so a machine can combine shared, platform, and role selections. Profile-specific variables can specialize shared templates. I tested personal Mac/laptop, simulated Linux/server, and work Mac/laptop profiles; the work profile reused a template owned by the base repo and supplied its work value successfully. [Profiles](https://dotdrop.readthedocs.io/en/latest/config/config-profiles/), [variable precedence](https://dotdrop.readthedocs.io/en/latest/config/config-variables/).

An importing configuration can refer to profiles in the configuration it imports. The imported configuration cannot depend on profiles defined above it in the import tree. **Make the private work repo import the personal base.** This keeps the dependency one-way and avoids teaching the base about enterprise details. Use explicit, documented keys for replacements instead of declaring unrelated keys that happen to target the same path. [Import scope](https://dotdrop.readthedocs.io/en/latest/config/config-file/).

### Templates, deployment, and editing

The template engine is Jinja2 with dotdrop-specific delimiters. It can render platform paths, role-dependent sections, and profile values. The default deployment copies files; absolute/relative links and child links are optional. A templated linked file is rendered through a work directory first, so editing its generated destination is not the same as editing its template. [Templating](https://dotdrop.readthedocs.io/en/latest/template/templating/), [link modes](https://dotdrop.readthedocs.io/en/latest/howto/symlink-dotfiles/).

Your current cfg policy also tracks agent files at their actual runtime locations. A source/destination manager changes that Git ownership model: the source becomes authoritative, and the real runtime file becomes generated output. Update that policy deliberately before cutover; preserving regular files alone does not preserve the existing tracking arrangement.

For agent configuration, use regular-file deployment where runtime files and directories must remain real. Preserve intentional agent-to-agent reference links separately. Avoid managing all of `~/.codex`, `~/.gemini`, or `~/.ssh` as a single wholesale directory: those parents also hold machine-local or sensitive state.

Day to day, edit the source and install the selected profile. Use `compare` to detect drift. If you edit a plain deployed file, `update` can bring changes back; template changes require review rather than blindly replacing the template with one machine's rendered output. [Daily commands](https://dotdrop.readthedocs.io/en/latest/usage/).

### Setup behavior and tradeoffs

Dotdrop has pre/post actions at file and profile levels. It can invoke your existing scripts without translating their logic into a new language. However, a file's normal action is skipped when the file is unchanged; I verified that a second install did not rerun its marker action. `--force-actions` explicitly reran it. Fake dotfiles can also represent always-run operations. [Actions](https://dotdrop.readthedocs.io/en/latest/config/config-actions/), [CLI behavior](https://dotdrop.readthedocs.io/en/latest/usage/).

I would keep two explicit operations: **apply configuration** and **set up/update software**. A small tracked launcher can call the appropriate dotdrop profile and the existing setup scripts. That prevents a harmless configuration refresh from unexpectedly updating many tools, while still providing one bootstrap entrypoint for a new machine.

The cost is Python dependencies, a smaller support ecosystem, explicit YAML bookkeeping, and no built-in package-state engine comparable to mise bootstrap. The sandbox emitted an optional `python-magic` warning; all exercised text/profile/action behavior still passed. **Verdict: best conservative match for your requested repository and profile model.**

## GNU Stow: a useful primitive, too little policy

Stow makes source-directory packages appear in a target tree through symlinks. Git is an ordinary storage choice around it. Separate repositories can each supply packages to the same home directory, provided their installed paths do not conflict. It offers simulation, unstowing, and control over directory folding. [Stow manual](https://www.gnu.org/s/stow/manual/stow.html).

In the experiment, base and work packages installed disjoint files successfully. When the work package also supplied the base file's path, Stow returned a conflict and preserved the original link. This is sensible behavior for a link manager, but it is not an overlay winner policy.

You would need a tracked wrapper to choose package combinations such as common + Mac + laptop + work. You would also need a renderer for templates and a separate setup runner. Selecting a platform-specific package is possible, but Stow itself does not evaluate profile data or generate a file from those dimensions.

Its editing model is attractive: editing a linked live file edits its Git-owned source immediately. Its minimalism and long history are strengths if you want that arrangement. For your current real-file agent configuration policy, however, adopting symlinks into a dotfiles checkout would be a deliberate policy change. Avoid `--adopt` as a casual migration switch: moving existing target content into a package deserves an explicit backup and diff review. [Stow options and conflicts](https://www.gnu.org/s/stow/manual/stow.html).

**Verdict: not my recommendation here.** You would replace the bare Git limitation with a custom framework around Stow. It becomes compelling only if you intentionally simplify the requirements to symlinked packages, application includes, and separately maintained setup scripts.

## Chezmoi: excellent tooling, awkward repository composition

### Where it is strong

Chezmoi maintains source state and computes the target files for each machine. Its Git-aware commands, templates, ignore rules, explicit diffs, and secret integrations make it particularly capable for diverse personal machines. macOS/Linux differences and custom laptop/server/context data are natural uses of its templates. Files are normally materialized as regular files rather than requiring a symlink tree. [Setup](https://www.chezmoi.io/user-guide/setup/), [machine differences](https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/).

Script names express lifecycle behavior: normal execution, `run_once_`, `run_onchange_`, and before/after ordering. A useful subtlety is that `run_once_` is based on successfully executed script content, not a permanent “this filename has run” flag. In the sandbox, the unchanged script ran once across repeated applies, and changed content ran again. Package installation can be implemented through these scripts and tracked manifests. [Script semantics](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/).

### How separate repositories would work

The upstream design explicitly chooses one branch in one repository as the main source of truth. It documents alternatives: multiple invocations using distinct sources/configs; assembling one source tree; or invoking another instance through a script. This is **supported through orchestration**, not a claim that multiple repos are impossible. [Multiple-source design discussion](https://www.chezmoi.io/user-guide/frequently-asked-questions/design/).

A workable arrangement for you would give the base and work repo disjoint target ownership. The shared `.zshrc` or `.gitconfig` would load a separate fragment installed by the work instance. Each instance should have its own source/config and persistent-state path. I verified independent sources and state paths with one target directory.

If both instances own the same file, apply order is the policy. The experiment applied base, then work, then base again: the contents changed base → work → base. An ordered wrapper can hide that churn, but each instance's view of the file can still disagree with the other. A composed source tree avoids some deployment churn at the price of your own composition and edit-routing rules.

Externals and submodules help pull in other repositories, especially complete application trees. They do not automatically solve two independently authoritative templates contributing to one file. [Externals and submodules](https://www.chezmoi.io/user-guide/include-files-from-elsewhere/).

**Verdict: strong third choice for this particular requirement set.** It would move ahead if one primary configuration repo plus private, disjoint application fragments satisfied you. I would not recommend moving enterprise files into the personal repo merely to fit its default model.

## Mise dot: strongest integrated setup option

### What exists now

This is the current `mise dotfiles` command family, shortened to `mise dot`, not an assumed third-party plugin. It supports repository-based deployment as links, copies, templates, and inline content. A separate tracking workflow records live-file changes in a history Git store. For your ownership model, I would start with **repository-based deployment and ordinary reviewed Git commits**. The optional history/watch/sync mechanism introduces another persistence model that you do not need to solve this migration. [Overview](https://mise.jdx.dev/dotfiles.html), [history](https://mise.jdx.dev/dotfiles/history.html).

Current deployment features include variants, file permissions, directory deployment, and selectors. The default mode is symlink, so explicitly choose copy/template where you need regular runtime files. Tera functions can inspect the real OS and architecture, while environments select work/personal or laptop/server policy. Platform-named config files require `auto_env` to be enabled in the evaluated version; their names alone do not guarantee automatic loading. [Managed files](https://mise.jdx.dev/dotfiles/managed.html), [environments](https://mise.jdx.dev/configuration/environments.html), [templates](https://mise.jdx.dev/templates.html).

### Multiple repos work, with an important trap

Mise can load configuration folders under `~/.config/mise/conf.d`. Those folders can be links to separate Git checkouts and keep declarations beside their source files. I tested `10-base` and `90-work` folders pointing at independent synthetic repositories; the work environment overrode the base's target declaration and supplied variables to the shared template. A fresh server selection omitted work-only targets. [Configuration folders](https://mise.jdx.dev/configuration.html#conf-d-folders), [machine modules](https://mise.jdx.dev/bootstrap/modules.html).

Do not confuse this with generic `include = [...]`. In the evaluated version, included configs cannot contain `[dotfiles]` or `[tasks]`, even though other sections are accepted. I tested the rejection. **Use normal config discovery/folders for the dotfiles layers**, and verify precedence with `mise config`. The directory's own `config.toml` can override its fragments. [Include restrictions](https://mise.jdx.dev/configuration.html#include).

Mise is the standout for partial-file composition. Separate layers can supply different managed block IDs, individual lines, or structured key edits. The sandbox preserved an existing manual line alongside base and work blocks. This is valuable when an application has no useful include mechanism, although competing edits to the same keys still need an ownership rule. [Partial-file edits](https://mise.jdx.dev/dotfiles/edits.html).

### Setup strengths and lifecycle costs

Mise bootstrap covers host packages, repositories, files, services, and platform-specific setup, in addition to development tools and tasks. That gives it the clearest path to replacing substantial parts of your setup shell script. Existing installers can remain task or hook commands during a gradual transition. These facilities were reviewed in documentation; I did not execute host package or service changes. [Bootstrap facilities](https://mise.jdx.dev/bootstrap.html), [tasks](https://mise.jdx.dev/tasks/).

Its pre/post dotfile hooks ran on both the initial and unchanged second apply in my fixture. Hook commands need idempotence or guards for expensive operations. A repeated apply resolved the work winner before deployment and needed no forced collision override.

Removing a selected environment is also not a general uninstall operation. In the sandbox, deactivating work restored the base-owned replacement but left the previously deployed work-only file. Mise documents explicit module removal and cleanup mechanisms; you must plan them rather than assuming profile selection reverses every prior action. [Module removal](https://mise.jdx.dev/bootstrap/modules.html).

The dotfiles workflow appeared in release **2026.6.6, dated June 13, 2026**. It has substantial functionality and ongoing fixes, but about five months of history at this research date. The parent project's popularity is not a measure of how many users exercise dotfiles or bootstrap. **Verdict: choose it over dotdrop if integrated machine provisioning is the deciding priority; pin the version and begin with a limited pilot.** [Launch release](https://github.com/jdx/mise/releases/tag/v2026.6.6), [current releases](https://github.com/jdx/mise/releases).

## Community adoption and project health

The numbers below are a live GitHub REST API snapshot from November 6, 2026 in Los Angeles. They are signals, not installed-user counts. “Latest commit” means the sampled default-branch commit, not the repository's `pushed_at` field. Raw metadata and the sampled commit range are saved with the research.

| Project | Stars / forks | Latest stable release | Default-branch commit observed, UTC | Assessment |
| --- | --- | --- | --- | --- |
| dotdrop | 1,956 / 111 | 1.18.1 · Nov 6, 2026 | Nov 6, 2026 | Smaller, longstanding, actively releasing |
| chezmoi | 22,192 / 699 | 2.74.0 · Nov 1, 2026 | Nov 6, 2026 | Large established dotfiles ecosystem; active |
| mise | 35,882 / 1,528 | 2026.11.3 · Nov 6, 2026 | Nov 7, 2026 UTC / Nov 6 local | Very active parent project; younger subsystem |
| Stow, GitHub mirror | 1,158 / 58 | 2.4.1 · Sep 8, 2024 | Dec 3, 2025 in the mirror | Mature and slow-moving; mirror undercounts broader GNU use |

Sources: [dotdrop repository API](https://api.github.com/repos/deadc0de6/dotdrop) and [releases](https://github.com/deadc0de6/dotdrop/releases), [chezmoi repository API](https://api.github.com/repos/twpayne/chezmoi) and [releases](https://github.com/twpayne/chezmoi/releases), [mise repository API](https://api.github.com/repos/jdx/mise) and [releases](https://github.com/jdx/mise/releases), [Stow mirror API](https://api.github.com/repos/aspiers/stow), [GNU release announcement](https://lists.gnu.org/archive/html/info-gnu/2024-09/msg00003.html).

**Dotdrop:** the last four releases span May to November 2026. This is active maintenance, despite a much smaller audience. Contribution totals are heavily concentrated in the primary maintainer. That is a continuity tradeoff worth accepting consciously, rather than treating “active” as equivalent to a broad maintainer team. [Contributor history](https://api.github.com/repos/deadc0de6/dotdrop/contributors?per_page=5).

**Chezmoi:** recent releases span several October dates and November 1. Its latest 100 default-branch commits covered roughly six weeks. Its primary maintainer also dominates lifetime contributions, alongside recurring outside contributions. Among these options, it offers the clearest combination of substantial dotfiles-specific adoption and active development. [Commit sample](https://api.github.com/repos/twpayne/chezmoi/commits?per_page=100), [contributors](https://api.github.com/repos/twpayne/chezmoi/contributors?per_page=5).

**Mise:** releases were appearing daily in the latest sample, and 100 default-branch commits covered about four days. Several contributors have substantial lifetime totals. That indicates energy and a broad parent ecosystem, while also implying a higher update rate to follow. It does not establish adoption or stability of the dotfiles component alone. [Commit sample](https://api.github.com/repos/jdx/mise/commits?per_page=100), [contributors](https://api.github.com/repos/jdx/mise/contributors?per_page=5).

**Stow:** an older release date is not sufficient evidence of abandonment for a narrowly scoped GNU utility. The official release remains 2.4.1; the inspected mirror includes later development, but I did not establish a newer canonical release. GitHub stars are an especially incomplete comparison here. [GNU project](https://www.gnu.org/software/stow/), [mirror commits](https://api.github.com/repos/aspiers/stow/commits?per_page=100).

License snapshot: dotdrop and Stow report GPLv3-family licensing; chezmoi and mise report MIT. This is project metadata, not a legal assessment. All four inspected GitHub repositories were unarchived. None of these indicators guarantees future maintenance.

## What I actually tested

I installed pinned runtimes only in a temporary research directory and generated separate synthetic Git repos with fake HOME/XDG directories. All 35 assertions passed. The fixtures and full command output are retained alongside this report.

| Tool | Executed checks | Result |
| --- | --- | --- |
| dotdrop 1.18.1 | Dry runs for three profiles; imported shared templates; Mac/laptop and simulated Linux/server data; work variables; same-key replacement; unchanged and forced action reruns | 15 passed |
| chezmoi 2.74.0 | Dry run; two sources with separate persistent state; disjoint targets; collision overwritten by last apply; base reapply; once-script rerun after content change | 6 passed |
| Stow 2.4.1 | Simulation; two repos with disjoint links; deliberate collision | 3 passed; collision rejected as expected |
| mise 2026.11.3 | Dry run and hooks; linked repo folders; shared template variables; resolved replacement; partial-file blocks; repeated apply; profile deactivation; fresh server role; generic include rejection | 11 passed |

Mise and chezmoi binaries matched their official release checksum files. Dotdrop came from PyPI in an isolated virtual environment. Stow was built into a temporary prefix from the official GNU source tarball. The checksums verify download integrity; I did not independently authenticate release signatures.

**Limits:** execution was on macOS arm64. Linux/server selections were configuration simulations, not native Linux deployment. No enterprise settings, password-manager authentication, privileged operations, package installation, or real service management were exercised. These experiments validate the difficult composition behaviors; they do not certify a complete migration or production reliability.

## Proposed layout for your cfg

The following is a proposal, not an applied restructuring. Keep the base checkout available independently and have the private work repo import it only on work machines.

```text
Personal cfg repository                 Private work repository
├── config.yaml                        ├── config.yaml
├── files/                             │   imports ../cfg/config.yaml
│   ├── shell/                         ├── files/
│   ├── git/                           │   └── work-owned fragments/settings
│   └── shared-skills/                  └── scripts/
├── scripts/                               └── work setup
│   └── existing reviewed installers
└── docs/ and machine/profile records
```

Define reusable base, platform, and role profiles, then name the actual machine combinations. A minimal example follows the pattern exercised in the sandbox:

```yaml
# personal cfg/config.yaml: excerpt
profiles:
  mac-laptop:
    include: [_common, _mac, _laptop]
  linux-server:
    include: [_common, _linux, _server]
```

```yaml
# private work/config.yaml: excerpt
config:
  dotpath: files
  import_configs: [../cfg/config.yaml]
profiles:
  work-mac:
    include: [mac-laptop]
    variables:
      context: work
    dotfiles: [f_work_shell, f_work_git]
```

These are excerpts, not standalone installable configurations. The committed experiment provides complete minimal fixtures. A real base should select context-specific agents separately from common shell/platform/role profiles. Generic shared skills can come from the base; personal Codex/Antigravity configuration belongs only in personal selections, and work-only Copilot configuration belongs in the private layer.

For files shared across contexts, establish a small ownership contract:

| Target | Recommended owner and extension point |
| --- | --- |
| Shell entrypoint | Base owns entrypoint; load separate base and optional work fragments |
| Git configuration | Base owns common settings; work repo owns a separately included file |
| SSH configuration | Manage explicit non-secret config fragments; leave keys and client runtime files outside Git |
| Shared skills | Base owns approved generic skills; work-specific additions stay work-owned |
| Agent settings | Manage approved individual files; preserve ignored machine-local config/hooks/auth |
| Complete platform-specific file | Use a template or one explicit selected replacement; document its key |

The base should not fetch a private work repository on personal machines. The work bootstrap can clone the base and its private layer, authenticate through the work environment, and record the intended base revision. Ordinary sibling checkouts are simpler to operate initially than submodules; use a submodule or revision manifest only when reproducible cross-repo version coupling is needed.

## A migration plan with clear stopping points

1. **Inventory ownership and current differences.** List tracked cfg paths, intended machine selections, and known overlay collisions. Do any enterprise inventory from the work environment; bring back only general requirements.
2. **Pilot a narrow set.** In a separate target directory, migrate a shell fragment, tmux configuration, Git includes, and one shared skill. Confirm the generated results and intended file/link types.
3. **Exercise platform and role policy.** Validate a personal Mac profile and perform a real Linux dry run/test on homelab before declaring Linux support verified. Keep host service/VPN management in the homelab repository.
4. **Keep installers intact initially.** Expose existing scripts through an explicit setup command. Record whether each command installs, upgrades, or only verifies. Change package/runtime ownership separately from changing dotfile delivery.
5. **Test the work layer privately.** Check both additions and at least one intentional override. Verify that no enterprise files or work repo credentials appear in the base checkout or its Git history.
6. **Cut over with one owner per path.** Back up existing targets and tag the old cfg state. Explicitly update the current runtime-path tracking policy for migrated agent files. Once a path is managed by the new system, stop tracking its live generated copy in the bare HOME worktree. Preserve the new source and its history; keep the old repository available for rollback.
7. **Document operation and removal.** Provide one apply command, one setup command, and a cleanup procedure for deactivated profiles. Removing a declaration does not generally reverse its previous side effects.

Do not combine this migration with silently renaming cfg's legacy `main` branch. Choose branch alignment explicitly as part of the migration plan. Do not switch Volta to mise's runtime management merely because mise is installed; each runtime should have a clear owner during any transition.

## Decision guide

| If this matters most | Choose | Why |
| --- | --- | --- |
| Separate repos and explicit profiles, with a focused dotfiles tool | **dotdrop** | Closest direct match; keep your reviewed installers |
| One tool for files, packages, runtime tools, and machine setup | **mise** | Most integrated feature set; accept the younger subsystem |
| Large established dotfiles ecosystem, with disjoint work fragments | **chezmoi** | Excellent workflow if its single-source preference is acceptable |
| Minimal link management and a self-maintained setup wrapper | **Stow** | Small, transparent scope; you supply the rest |

**My recommendation remains dotdrop, with mise as a credible alternate architecture.** The choice turns on whether you want a better configuration composition tool around your existing setup scripts, or to adopt an integrated machine setup system at the same time. Your critical repository-separation requirement can be met with either; the sandbox confirmed both paths.
