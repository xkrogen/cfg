---
name: skill-simplifier
description: "Optimize an existing skill by folding in learnings from a test session. Reduces tool calls, inlines scripts, eliminates temp files, and bakes in discovered knowledge. Use when a skill works but is inefficient — the agent had to figure things out on the fly, generated scripts ad-hoc, created temp files, or required many permission prompts. Also use when the user says 'simplify this skill', 'optimize this skill', 'fold in learnings', 'bake in what we learned', or 'make this skill more efficient'."
---

# skill-simplifier — Post-Session Skill Optimizer

You take a skill that works but is inefficient and refactor it so future executions are faster, need fewer permission prompts, and don't repeat work that's already been figured out.

If the user hasn't already told you which skill to optimize, ask them for it (a skill name or a path to the skill directory), and note any `--transcript <session-log>` or `--dry-run` intent.

## When to use this

After testing a skill in a session where the agent:
- Generated scripts on the fly that should be bundled
- Used many Bash calls where one piped command would do
- Created temp files that forced extra Read/Write permission prompts
- Figured out paths, APIs, flags, or patterns by trial and error
- Made the same discovery in multiple test runs

The user wants those learnings folded back into the skill definition.

## Step 0: Resolve the Skill

From the user's request, extract:
- The skill to optimize: a skill name OR a path to the skill directory
- An optional `--transcript <path>`: a session transcript or log to analyze
- An optional `--dry-run` intent: analyze and report what would change, but don't edit anything

### Resolving the skill

The target can be a name (e.g., `pr-patrol`) or a full path. Resolve it as follows:

1. **If it's an absolute path** and contains SKILL.md, use it directly
2. **If it's a name**, search these locations in order:
   - `~/.agents/skills/<name>/SKILL.md` — shared skills
   - The active agent's own skill root: `~/.codex/skills` for personal tasks or `~/.copilot/skills` for work tasks
   - `.github/skills/<name>/SKILL.md` — repo-local skills
   - Installed plugins exposed by the active agent platform
3. **If it contains a colon** (e.g., `plugin-name:skill-name`), split on `:` and search the plugin namespace first, then the skill name within it
4. **If nothing is found**, list skills available in the current agent context and ask the user to pick

If the user didn't name a skill at all, check if the current directory contains a SKILL.md. If not, ask the user.

Use evidence authorized for the current task/context. Do not search another agent’s
private histories or sibling workspaces by default. Persist reusable methods in
shared skills; keep private endpoints, credentials and task data in their owning
context. Efficiency changes must preserve authorization boundaries.

## Step 1: Gather Context

You need two things: the **current skill** and the **session learnings**.

### 1a: Read the skill

Read the SKILL.md and inventory all bundled resources:
```
<skill-dir>/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

Note what scripts already exist and what the SKILL.md instructs the agent to do.

### 1b: Find session learnings

Session learnings come from one or more of these sources (check in order):

1. **Explicit transcript** — if `--transcript` was passed, read it
2. **Current conversation history** — the user may have just finished testing the skill in this session. Look back through the conversation for tool calls, Bash commands, scripts that were generated, errors hit, retries, and discoveries made
3. **Workspace artifacts** — check for a `<skill-name>-workspace/` sibling directory (from skill-creator iterations) containing run transcripts
4. **User description** — if none of the above, ask the user to describe what happened

From the learnings, extract:
- **Ad-hoc scripts**: Any script the agent wrote on the fly during execution. Capture the final working version (not intermediate broken attempts)
- **Discovered knowledge**: Paths, flags, API endpoints, tool quirks, workarounds that were figured out by trial and error
- **Repeated patterns**: Multi-step sequences that every execution had to repeat
- **Temp file usage**: Cases where data was written to a temp file just to be read back
- **Excessive tool calls**: Sequences of Bash/Read/Write that could be consolidated
- **Permission friction**: Tool calls that triggered permission prompts unnecessarily
- **Error-retry loops**: Commands that failed and were retried with fixes

## Step 2: Analyze and Plan

Categorize each finding into one of these optimization strategies:

### Strategy A: Bundle Scripts
**Signal**: the agent generated a script (Python, bash, jq pipeline, etc.) during execution that is general-purpose enough to reuse.

**Action**: Save the script to `<skill-dir>/scripts/`, make it executable, and add instructions in SKILL.md to use it. The script should:
- Accept input via arguments or stdin (not hardcoded paths)
- Produce output on stdout (not to a temp file)
- Be self-contained (no external dependencies beyond what's already available)
- Include a usage comment at the top

### Strategy B: Consolidate Bash Calls
**Signal**: The skill's execution required N sequential Bash calls where a single script or piped command would work.

**Action**: Either:
- Combine into a single bundled script that does all the steps
- Rewrite the SKILL.md instructions to use a single compound command with `&&` or pipes
- Use a here-document or stdin pipe to avoid intermediate files

**Examples**:
```
# BEFORE: 3 Bash calls + 2 temp files + 2 Read calls = 7 tool invocations
Bash: echo '{"query":"..."}' > /tmp/payload.json
Bash: curl -X POST -d @/tmp/payload.json https://api/endpoint > /tmp/result.json
Read: /tmp/result.json
Bash: jq '.data[] | .name' /tmp/result.json

# AFTER: 1 Bash call, 0 temp files = 1 tool invocation
Bash: curl -s -X POST -d '{"query":"..."}' https://api/endpoint | jq '.data[] | .name'
```

### Strategy C: Eliminate Temp Files
**Signal**: Data is written to a temp file just to be passed to another command or read back by the agent.

**Action**:
- Use pipes (`|`) to connect producers and consumers
- Use process substitution (`<(...)`) for commands that need file arguments
- Use heredocs (`<<'EOF'`) for inline data
- If the skill genuinely needs to stage data for the agent to inspect, use a script that handles the full pipeline and outputs the result

### Strategy D: Bake In Discovered Knowledge
**Signal**: the agent had to look something up, try multiple approaches, or figure out the right incantation during the session.

**Action**: Write the answer directly into SKILL.md or a reference file:
- Specific paths, URLs, or endpoints
- Correct flags or argument combinations
- API response formats and how to parse them
- Error conditions and their workarounds
- The "right" approach (skip the dead ends)

### Strategy E: Restructure Instructions
**Signal**: The skill's instructions are vague where they should be specific, causing the agent to improvise and make extra tool calls.

**Action**: Replace vague instructions with concrete steps. Turn "figure out X" into "X is Y, do Z." Add the exact commands or script invocations.

## Step 3: Present the Plan

Before making changes, present a numbered list of proposed optimizations:

```
Proposed optimizations for <skill-name>:

1. [Bundle] save the jq transform pipeline as scripts/transform.sh
   - Eliminates: 3 Bash calls per execution
   - Estimated savings: 2 permission prompts

2. [Consolidate] combine the 4-step API query into scripts/query-api.sh
   - Eliminates: 4 Bash calls + 2 temp files
   - Estimated savings: 5 permission prompts

3. [Bake In] add the Kusto cluster endpoint directly to SKILL.md
   - Eliminates: 1 discovery step (grep + read + parse)
   - Estimated savings: 3 tool calls

4. [Restructure] replace "find the right table" with the exact table name
   - Eliminates: exploratory search loop
   - Estimated savings: 2-5 tool calls
```

If `--dry-run`, stop here.

Otherwise, ask the user to confirm or adjust the plan.

## Step 4: Apply Optimizations

Apply each approved optimization:

### For new scripts:
1. Write the script to `<skill-dir>/scripts/<name>.sh` (or `.py`)
2. Make executable: `chmod +x`
3. Add a usage comment header
4. Update SKILL.md to reference the script with exact invocation syntax

### For SKILL.md changes:
1. Replace vague instructions with specific ones
2. Add discovered knowledge inline or in a reference file
3. Update any step-by-step instructions to use the new scripts
4. Remove instructions that are now handled by scripts

### Principles for all changes:
- **Don't change behavior** — the skill should produce the same output, just more efficiently
- **Don't add features** — this is optimization, not enhancement
- **Keep SKILL.md readable** — if adding lots of detail would bloat it, put it in `references/`
- **Prefer scripts that work on stdin/stdout** — avoids temp files and extra tool calls
- **Make scripts idempotent** — safe to re-run
- **Test each script** — run it once to verify it works before declaring victory

## Step 5: Validate

After applying changes:

1. Re-read the modified SKILL.md end-to-end
2. Verify all referenced scripts exist and are executable
3. Count the expected tool calls for a typical execution (before vs after)
4. Report the results:

```
Optimization complete for <skill-name>:

Before: ~N tool calls per execution, M permission prompts expected
After:  ~X tool calls per execution, Y permission prompts expected

Changes:
- Added scripts/transform.sh (jq pipeline)
- Added scripts/query-api.sh (API query + parse)
- Updated SKILL.md steps 3-7 with concrete commands
- Added references/api-format.md with response schema

Net reduction: ~K fewer tool calls, ~J fewer permission prompts
```

## Important Rules

- **Read before writing.** Always read the full SKILL.md and any existing scripts before making changes.
- **Scripts should be self-documenting.** Include a header comment with usage, expected input, and output format.
- **Stdin/stdout > temp files.** If a script needs input, take it from stdin or arguments. Write output to stdout. Let the caller redirect if needed.
- **One script per logical operation.** Don't create a mega-script. Group related steps that always run together.
- **Preserve the skill's voice.** Match the writing style and structure of the existing SKILL.md.
- **Don't over-optimize.** If a step is only 1-2 tool calls and is clear as-is, leave it alone. Optimize the expensive/repetitive parts.
