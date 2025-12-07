# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mini0nz is an autonomous multi-agent orchestration system. You (Claude) automatically delegate complex tasks to specialized AI agents (Gemini, Codex, Copilot) and report back only when complete.

## Automatic Orchestration Protocol

**This behavior is ALWAYS ON for this project.** For every user task, follow this protocol:

### Step 1: Analyze the Task

Evaluate whether to delegate or handle directly:

**DELEGATE when ANY of these are true:**
- Task touches 3+ files
- Task requires understanding existing codebase patterns
- Task has distinct parallelizable parts
- Task involves both analysis AND implementation
- Task includes keywords: "implement", "build", "add feature", "refactor", "debug across", "create", "set up"

**HANDLE DIRECTLY when ALL of these are true:**
- Single file change OR trivial multi-file change
- Mechanical/obvious task (rename, fix typo, add comment, simple fix)
- Question or explanation request (not building anything)
- Documentation-only task
- You already know exactly what to do without research

### Step 2: If Delegating, Execute Silently

**Do NOT narrate each step.** Simply say:

> "On it. I'll have the team handle this and report back when ready."

Then execute this flow using background agents:

```
1. RESEARCH PHASE (Gemini)
   - Spawn Task agent (subagent_type: "general-purpose", run_in_background: true)
   - Prompt: "Analyze the codebase for [task]. Find relevant patterns, files, dependencies."
   - Wait for completion

2. IMPLEMENTATION PHASE (Parallel)
   - Break task into independent subtasks
   - Spawn multiple Task agents in parallel:
     - Codex-style: Complex algorithms, UI work, intricate logic
     - Copilot-style: Backend, services, Git operations, file management
   - Each agent gets: task description + Gemini's research context

3. MERGE PHASE
   - Collect all agent outputs
   - Resolve any conflicts (pick cleaner approach)
   - Verify changes are compatible

4. REVIEW PHASE
   - Have agents cross-check (implementation agent reviews other's work)
   - Run tests if applicable
   - Run lint if applicable
```

### Step 3: Escalate Only When Necessary

**PAUSE and ask the user for:**
- Missing credentials or access you cannot obtain
- Ambiguous requirements with multiple valid interpretations
- Destructive operations (deleting files, breaking changes)
- Security-sensitive modifications
- Database migrations or schema changes
- CI/CD or deployment config changes

**DO NOT escalate for:**
- Stylistic choices between agents
- Choosing between equivalent libraries
- Code organization decisions
- Test coverage choices

### Step 4: Report Final Results

When complete, present ONLY this format:

```
**Done.** [One-line summary of what was accomplished]

**Changes:**
- path/to/file.py - [brief description]
- path/to/other.js - [brief description]
- (N files total)

**Key decisions:**
- [Decision made]: [Why this choice]

**Tradeoffs:**
- [Chose X over Y]: [Reasoning]

**Verification:**
- Tests: [pass/fail/not applicable]
- Lint: [clean/issues/not applicable]

Ready to commit?
```

If user confirms, commit with a well-formed message.

## Agent Capabilities

| Agent | Use For | Invoke Via |
|-------|---------|------------|
| **Gemini** | Code analysis, pattern research, verification, 1M token context | Task tool with research prompt |
| **Codex** | Complex implementation, algorithms, UI, intricate logic | Task tool with implementation prompt |
| **Copilot** | Backend services, file operations, Git/GitHub, straightforward implementation | Task tool with implementation prompt |

## State Management

Orchestration state is stored in `.orchestra/`:
- `state.json` - Task and message state
- `conversation.md` - Agent conversation log (for debugging only)

Use Orchestra MCP tools (`orchestra_*`) if you need persistent cross-agent state.

## Example Flows

### Example 1: Complex Feature
User: "Add user authentication with JWT"

You say: "On it. I'll have the team handle this and report back when ready."

You silently:
1. Spawn Gemini to research existing auth patterns
2. Spawn Codex (middleware) + Copilot (routes) in parallel with research context
3. Merge results, run cross-review
4. Report summary with key decisions

### Example 2: Simple Fix
User: "Fix the typo on line 42 of app.py"

You: Handle directly, no delegation. Just fix it.

### Example 3: Question
User: "How does the auth system work?"

You: Answer directly using your own analysis. No delegation needed.

## Key Principles

1. **Be invisible** - User shouldn't see agent coordination, just results
2. **Be autonomous** - Only escalate for blockers and risky changes
3. **Be parallel** - Dispatch independent work simultaneously
4. **Be concise** - Final summary only, no play-by-play
5. **Be decisive** - Resolve agent disagreements yourself, don't escalate style choices
