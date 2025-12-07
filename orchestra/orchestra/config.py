"""Configuration for Orchestra multi-agent system."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    enabled: bool = True
    timeout: int = 300  # seconds
    max_retries: int = 2


@dataclass
class OrchestraConfig:
    """Main configuration for Orchestra."""

    # State directory
    state_dir: str = ".orchestra"

    # Agent configurations
    claude: AgentConfig = field(default_factory=AgentConfig)
    gemini: AgentConfig = field(default_factory=AgentConfig)
    codex: AgentConfig = field(default_factory=AgentConfig)
    copilot: AgentConfig = field(default_factory=AgentConfig)

    # Escalation settings
    escalate_after_failures: int = 3

    # Review settings
    require_cross_review: bool = True

    @classmethod
    def load(cls, path: str = "orchestra.json") -> "OrchestraConfig":
        """Load configuration from file."""
        config_path = Path(path)
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
                return cls(**data)
        return cls()

    def save(self, path: str = "orchestra.json"):
        """Save configuration to file."""
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2, default=lambda x: x.__dict__)


def generate_mcp_config() -> dict:
    """Generate MCP configuration for Claude Code."""
    return {
        "mcpServers": {
            "orchestra": {
                "command": "python",
                "args": ["-m", "orchestra.server"],
                "env": {
                    "ORCHESTRA_STATE_DIR": ".orchestra",
                    "ORCHESTRA_AGENT": "claude"
                }
            },
            "gemini-cli": {
                "command": "npx",
                "args": ["-y", "gemini-mcp-tool"]
            },
            "codex-cli": {
                "command": "npx",
                "args": ["-y", "codex-cli-mcp-tool"]
            },
            "copilot": {
                "command": "npx",
                "args": ["-y", "@willianpaiva/copilot-mcp-server"]
            }
        }
    }


def main():
    """CLI for configuration management."""
    import sys

    if "--setup" in sys.argv:
        config = generate_mcp_config()
        print("\nAdd this to your Claude Code MCP settings:\n")
        print(json.dumps(config, indent=2))
        print("\n")
        OrchestraConfig().save()
        print("Created orchestra.json with default settings")

    elif "--check" in sys.argv:
        from .agents import AgentPool
        pool = AgentPool()
        availability = pool.check_availability()

        print("\nAgent Availability:")
        for agent, available in availability.items():
            status = "✅ Available" if available else "❌ Not found"
            print(f"  {agent}: {status}")
        print()

    else:
        print("""
Orchestra - Seamless Multi-Agent Orchestration

Usage:
  python -m orchestra.config --setup    Generate MCP configuration
  python -m orchestra.config --check    Check agent availability

Orchestra is automatically invoked by Claude Code via CLAUDE.md.
No manual commands needed - just give Claude a task.
""")


if __name__ == "__main__":
    main()
