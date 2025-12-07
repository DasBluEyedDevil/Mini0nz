# Orchestra - Seamless Multi-Agent Orchestration

Orchestra enables Claude Code to automatically delegate complex tasks to specialized AI agents (Gemini, Codex, Copilot) and report back only when complete.

## How It Works

**You don't run Orchestra.** It runs automatically via CLAUDE.md instructions.

1. You give Claude a task
2. Claude analyzes whether to delegate or handle directly
3. If delegating, Claude silently dispatches agents in parallel
4. Agents research, implement, and cross-review
5. Claude reports the final result with key decisions

## Architecture

```
User Task
    │
    ▼
Claude (Orchestrator)
    │
    ├──► Analyze: Delegate or handle directly?
    │
    ├──► Research: Spawn Gemini for codebase analysis
    │
    ├──► Implement: Spawn Codex + Copilot in parallel
    │
    ├──► Review: Agents cross-check each other
    │
    └──► Report: Summary with key decisions
```

## Agent Roles

| Agent | Specialty | Subscription |
|-------|-----------|--------------|
| **Gemini** | Code analysis, research, 1M token context | Google (free) |
| **Codex** | Complex implementation, algorithms | ChatGPT Plus |
| **Copilot** | Backend, Git/GitHub operations | GitHub Copilot |

## Installation

```bash
# Install Orchestra package
cd orchestra && pip install -e .

# Install AI CLIs (subscription-based, no API keys)
npm install -g @openai/codex && codex login
gh extension install github/gh-copilot
# Gemini uses Google OAuth automatically
```

## Configuration

Check agent availability:
```bash
python -m orchestra.config --check
```

Generate MCP config:
```bash
python -m orchestra.config --setup
```

## Files

- `orchestra/server.py` - MCP server for state management
- `orchestra/agents.py` - Agent CLI invokers
- `orchestra/state.py` - Persistent state
- `orchestra/models.py` - Data models

## State

During execution, state is stored in `.orchestra/`:
- `state.json` - Tasks, messages, reviews
- `conversation.md` - Agent conversation log (for debugging)
