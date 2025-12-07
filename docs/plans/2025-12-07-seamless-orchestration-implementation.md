# Implementation Plan: Seamless Orchestration

## Task 1: Rewrite CLAUDE.md

**File:** `CLAUDE.md`

Add sections:
1. Detection logic (when to delegate vs handle directly)
2. Orchestration protocol (how to dispatch agents)
3. Parallel execution pattern
4. Escalation rules
5. Final handoff format

## Task 2: Simplify Orchestra Package

**Remove:**
- `orchestra/orchestra/loop.py` - No longer needed (Claude orchestrates directly)
- `orchestra/setup.py` - Setup script not needed

**Keep:**
- `orchestra/orchestra/server.py` - MCP tools for state/messaging
- `orchestra/orchestra/agents.py` - Agent invokers
- `orchestra/orchestra/state.py` - Persistent state
- `orchestra/orchestra/models.py` - Data models

**Modify:**
- `orchestra/orchestra/config.py` - Simplify, remove loop references

## Task 3: Update MCP Config

**File:** `mcp_config.json`

Ensure Orchestra MCP server is configured for Claude to use directly.

## Task 4: Test

Run a real multi-file task and verify:
- Detection triggers correctly
- Agents are dispatched in parallel
- Results are merged
- Final summary is formatted correctly
