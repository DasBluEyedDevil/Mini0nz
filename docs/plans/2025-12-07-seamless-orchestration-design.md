# Seamless Multi-Agent Orchestration

**Date:** 2025-12-07
**Status:** Approved

## Overview

Transform Orchestra from a manual command-line tool into invisible, automatic behavior. Claude Code analyzes tasks, delegates to agents (Gemini, Codex, Copilot) when appropriate, and reports back only when complete.

## Core Experience

User gives Claude a task. Claude silently decides whether to handle it directly or delegate. If delegating, Claude dispatches agents, monitors progress, merges results, and returns a concise summary with key decisions and tradeoffs. User only sees the final result.

## Smart Detection

**Delegate when:**
- Task touches 3+ files
- Task requires understanding existing patterns
- Task has distinct parallelizable parts
- Task involves both frontend and backend
- Keywords: "implement", "add feature", "refactor", "debug across"

**Handle directly when:**
- Single file change
- Mechanical task (rename, fix typo)
- Question or explanation request
- Documentation only
- Quick fix with obvious solution

## Parallel Execution

```
Task
  │
  ▼
Gemini (research) ──────────────────────┐
  │                                     │
  ▼                                     │
Claude dispatches parallel work         │
  │                                     │
  ├──► Codex (subtask A)               │
  │                                     │
  ├──► Copilot (subtask B)             │
  │                                     │
  ▼                                     │
Claude merges & resolves conflicts ◄────┘
  │
  ▼
Cross-review (agents swap)
  │
  ▼
Final result to user
```

**Conflict resolution:**
- Claude picks cleaner approach for incompatible changes
- Gemini's research breaks ties on patterns
- Claude decides stylistic disagreements (no escalation)

## Escalation Rules

**Escalate for blockers:**
- Missing credentials or access
- Ambiguous requirements with multiple valid interpretations
- External dependencies unavailable

**Escalate for risky changes:**
- Deleting files or significant code
- Security-sensitive modifications
- Breaking changes to public APIs
- Database migrations
- CI/CD or deployment config changes

**Never escalate for:**
- Stylistic disagreements
- Equivalent library choices
- Code organization decisions
- Test coverage choices

## Final Handoff Format

```
**Done.** [One-line summary]

**Changes:**
- path/to/file.py - [what changed]
- (N files total)

**Key decisions:**
- [Decision]: [Rationale]

**Tradeoffs:**
- [Chose X over Y because Z]

**Verification:**
- Tests: [status]
- Lint: [status]

Ready to commit?
```

## Implementation

**No new infrastructure.** Leverage existing Orchestra MCP server with enhanced CLAUDE.md instructions.

**Components:**
1. CLAUDE.md - Detection logic, orchestration behavior, output formatting
2. Orchestra MCP server - Agent invocation, state management, message passing
3. Background execution - Spawn agents via Task tool, poll for completion, merge results

**Changes to current Orchestra:**
- Remove `python -m orchestra.loop` entry point
- All orchestration through Claude's native tools
- State persists in `.orchestra/` for debugging

## Activation

Always on for this project via CLAUDE.md. Every session automatically uses multi-agent approach when detection logic triggers.
