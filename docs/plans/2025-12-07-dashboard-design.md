# Orchestra Status Dashboard Design

**Date:** 2025-12-07

## Overview

A minimal CLI dashboard showing orchestration status using the Rich library.

## Command

```bash
orchestra-status          # Snapshot mode - show current state and exit
orchestra-status --watch  # Live mode - refresh every 2 seconds
orchestra-status -w       # Short flag for watch
```

## Output Format (~10 lines)

```
╭─ Orchestra Status ─────────────────────────────────╮
│ Session: abc123 │ Started: 2 min ago              │
├─────────────────────────────────────────────────────┤
│ Tasks    [████████░░░░░░░░] 3/6 complete           │
│          ● 2 pending  ● 1 in progress  ● 3 done    │
├─────────────────────────────────────────────────────┤
│ ✓ No escalations                                   │
╰─────────────────────────────────────────────────────╯
```

With escalation:
```
│ ⚠ ESCALATION: Missing API credentials for Gemini  │
```

## Data Source

- Reads directly from `.orchestra/state.json`
- No MCP server dependency required
- Path resolved relative to current working directory

## Edge Cases

- No `.orchestra/` folder → "No orchestration data found"
- Empty/corrupt state.json → "Unable to read state"
- No tasks yet → Shows "0/0 tasks" with empty progress bar
- No active session → "No active session"

## Files

- `orchestra/orchestra/dashboard.py` - Main dashboard logic
- `orchestra/pyproject.toml` - CLI entry point

## Dependencies

- `rich>=13.0.0` - Terminal UI library
