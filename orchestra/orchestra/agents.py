"""Agent invokers - calls external AI CLIs to get responses."""

import asyncio
import json
import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import AgentRole

# Windows compatibility
IS_WINDOWS = sys.platform == "win32"


@dataclass
class AgentResponse:
    """Response from an agent invocation."""
    agent: AgentRole
    success: bool
    content: str
    error: Optional[str] = None


class AgentInvoker(ABC):
    """Base class for invoking AI agents."""

    role: AgentRole

    @abstractmethod
    async def invoke(self, prompt: str, context: Optional[str] = None) -> AgentResponse:
        """Send a prompt to the agent and get a response."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this agent is available/configured."""
        pass


class GeminiAgent(AgentInvoker):
    """Invoke Gemini CLI for code analysis and research."""

    role = AgentRole.GEMINI

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir)
        self.persona = """You are Gemini, the Researcher in a multi-agent AI team.
Your role: Code analysis, research, verification, and providing context.
You have a 1M+ token context window - use it for deep analysis.

When responding:
1. Be thorough but concise
2. Provide file paths and line numbers when referencing code
3. Include code excerpts for clarity
4. Give actionable recommendations

You're working with:
- Claude (Orchestrator): Plans and coordinates
- Codex (Engineer): Implements complex features
- Copilot (Engineer): Backend, Git, GitHub operations

Always end your response with a clear summary of findings."""

    def is_available(self) -> bool:
        """Check if Gemini CLI is available."""
        return shutil.which("gemini") is not None

    async def invoke(self, prompt: str, context: Optional[str] = None) -> AgentResponse:
        """Invoke Gemini CLI with a prompt."""
        full_prompt = f"{self.persona}\n\n"
        if context:
            full_prompt += f"CONTEXT FROM OTHER AGENTS:\n{context}\n\n"
        full_prompt += f"YOUR TASK:\n{prompt}"

        try:
            # Run gemini CLI
            process = await asyncio.create_subprocess_exec(
                "gemini",
                full_prompt,
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300  # 5 minute timeout
            )

            if process.returncode == 0:
                return AgentResponse(
                    agent=self.role,
                    success=True,
                    content=stdout.decode("utf-8", errors="replace")
                )
            else:
                return AgentResponse(
                    agent=self.role,
                    success=False,
                    content="",
                    error=stderr.decode("utf-8", errors="replace")
                )

        except asyncio.TimeoutError:
            return AgentResponse(
                agent=self.role,
                success=False,
                content="",
                error="Gemini CLI timed out after 5 minutes"
            )
        except Exception as e:
            return AgentResponse(
                agent=self.role,
                success=False,
                content="",
                error=str(e)
            )


class CodexAgent(AgentInvoker):
    """Invoke OpenAI Codex CLI for implementation."""

    role = AgentRole.CODEX

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir)
        self.persona = """You are Codex, Engineer #1 in a multi-agent AI team.
Your role: Implementation of features, complex algorithms, and UI work.

When implementing:
1. Follow existing code patterns
2. Write clean, maintainable code
3. Include appropriate error handling
4. Run tests after changes

You're working with:
- Claude (Orchestrator): Gives you specs and coordinates
- Gemini (Researcher): Provides code analysis and context
- Copilot (Engineer #2): Handles backend/Git - may review your work

Report what you did, files modified, and any issues encountered."""

    def is_available(self) -> bool:
        """Check if Codex CLI is available."""
        return shutil.which("codex") is not None

    async def invoke(self, prompt: str, context: Optional[str] = None) -> AgentResponse:
        """Invoke Codex CLI with a prompt."""
        full_prompt = f"{self.persona}\n\n"
        if context:
            full_prompt += f"CONTEXT FROM OTHER AGENTS:\n{context}\n\n"
        full_prompt += f"YOUR TASK:\n{prompt}"

        try:
            # Codex uses different invocation - it's interactive by default
            # We'll use the quiet/non-interactive mode
            process = await asyncio.create_subprocess_exec(
                "codex",
                "--quiet",
                "--approval-mode", "full-auto",
                full_prompt,
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600  # 10 minute timeout for implementation
            )

            if process.returncode == 0:
                return AgentResponse(
                    agent=self.role,
                    success=True,
                    content=stdout.decode("utf-8", errors="replace")
                )
            else:
                return AgentResponse(
                    agent=self.role,
                    success=False,
                    content=stdout.decode("utf-8", errors="replace"),
                    error=stderr.decode("utf-8", errors="replace")
                )

        except asyncio.TimeoutError:
            return AgentResponse(
                agent=self.role,
                success=False,
                content="",
                error="Codex CLI timed out after 10 minutes"
            )
        except Exception as e:
            return AgentResponse(
                agent=self.role,
                success=False,
                content="",
                error=str(e)
            )


class CopilotAgent(AgentInvoker):
    """Invoke GitHub Copilot CLI for backend and Git operations."""

    role = AgentRole.COPILOT

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir)
        self.persona = """You are Copilot, Engineer #2 in a multi-agent AI team.
Your role: Backend implementation, Git operations, GitHub operations.

Your specialties:
- Backend services and APIs
- Database operations
- Git commits, branches, PRs
- GitHub issues and project management
- Code reviews

You're working with:
- Claude (Orchestrator): Gives you specs and coordinates
- Gemini (Researcher): Provides code analysis and context
- Codex (Engineer #1): Handles UI - you may review their work

Report what you did, commands run, and any issues encountered."""

    def is_available(self) -> bool:
        """Check if Copilot CLI is available."""
        # Check for gh with copilot extension
        if shutil.which("gh"):
            try:
                result = subprocess.run(
                    ["gh", "copilot", "--version"],
                    capture_output=True,
                    timeout=5,
                    shell=IS_WINDOWS
                )
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        # Check for standalone copilot
        return shutil.which("copilot") is not None

    async def invoke(self, prompt: str, context: Optional[str] = None) -> AgentResponse:
        """Invoke Copilot CLI with a prompt."""
        full_prompt = f"{self.persona}\n\n"
        if context:
            full_prompt += f"CONTEXT FROM OTHER AGENTS:\n{context}\n\n"
        full_prompt += f"YOUR TASK:\n{prompt}"

        try:
            # Try gh copilot first, fall back to standalone
            cmd = ["gh", "copilot", "suggest", "-t", "shell", full_prompt]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300
            )

            if process.returncode == 0:
                return AgentResponse(
                    agent=self.role,
                    success=True,
                    content=stdout.decode("utf-8", errors="replace")
                )
            else:
                return AgentResponse(
                    agent=self.role,
                    success=False,
                    content=stdout.decode("utf-8", errors="replace"),
                    error=stderr.decode("utf-8", errors="replace")
                )

        except asyncio.TimeoutError:
            return AgentResponse(
                agent=self.role,
                success=False,
                content="",
                error="Copilot CLI timed out after 5 minutes"
            )
        except Exception as e:
            return AgentResponse(
                agent=self.role,
                success=False,
                content="",
                error=str(e)
            )


class ClaudeAgent(AgentInvoker):
    """Invoke Claude Code CLI as a subagent."""

    role = AgentRole.CLAUDE

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir)
        self.persona = """You are Claude, the Orchestrator in a multi-agent AI team.
Your role: Planning, coordination, final decisions, quality assurance.

Your responsibilities:
- Break down tasks into subtasks
- Assign work to appropriate agents
- Review and approve final output
- Make architectural decisions
- Resolve conflicts between agents

You work with:
- Gemini (Researcher): Deep code analysis
- Codex (Engineer #1): Feature implementation
- Copilot (Engineer #2): Backend/Git operations

Be decisive and keep the team moving forward."""

    def is_available(self) -> bool:
        """Check if Claude CLI is available."""
        return shutil.which("claude") is not None

    async def invoke(self, prompt: str, context: Optional[str] = None) -> AgentResponse:
        """Invoke Claude Code CLI with a prompt."""
        full_prompt = f"{self.persona}\n\n"
        if context:
            full_prompt += f"CONTEXT FROM OTHER AGENTS:\n{context}\n\n"
        full_prompt += f"YOUR TASK:\n{prompt}"

        try:
            # Claude Code in print mode for non-interactive use
            process = await asyncio.create_subprocess_exec(
                "claude",
                "--print",
                "--dangerously-skip-permissions",
                full_prompt,
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600
            )

            if process.returncode == 0:
                return AgentResponse(
                    agent=self.role,
                    success=True,
                    content=stdout.decode("utf-8", errors="replace")
                )
            else:
                return AgentResponse(
                    agent=self.role,
                    success=False,
                    content=stdout.decode("utf-8", errors="replace"),
                    error=stderr.decode("utf-8", errors="replace")
                )

        except asyncio.TimeoutError:
            return AgentResponse(
                agent=self.role,
                success=False,
                content="",
                error="Claude CLI timed out after 10 minutes"
            )
        except Exception as e:
            return AgentResponse(
                agent=self.role,
                success=False,
                content="",
                error=str(e)
            )


class AgentPool:
    """Pool of all available agents."""

    def __init__(self, working_dir: str = "."):
        self.working_dir = working_dir
        self.agents: dict[AgentRole, AgentInvoker] = {
            AgentRole.CLAUDE: ClaudeAgent(working_dir),
            AgentRole.GEMINI: GeminiAgent(working_dir),
            AgentRole.CODEX: CodexAgent(working_dir),
            AgentRole.COPILOT: CopilotAgent(working_dir),
        }

    def get_agent(self, role: AgentRole) -> Optional[AgentInvoker]:
        """Get an agent by role."""
        return self.agents.get(role)

    def get_available_agents(self) -> list[AgentRole]:
        """Get list of available agents."""
        available = []
        for role, agent in self.agents.items():
            if agent.is_available():
                available.append(role)
        return available

    async def invoke(
        self,
        role: AgentRole,
        prompt: str,
        context: Optional[str] = None
    ) -> AgentResponse:
        """Invoke an agent by role."""
        agent = self.get_agent(role)
        if not agent:
            return AgentResponse(
                agent=role,
                success=False,
                content="",
                error=f"Agent {role.value} not found"
            )

        if not agent.is_available():
            return AgentResponse(
                agent=role,
                success=False,
                content="",
                error=f"Agent {role.value} is not available (CLI not found)"
            )

        return await agent.invoke(prompt, context)

    def check_availability(self) -> dict[str, bool]:
        """Check availability of all agents."""
        return {
            role.value: agent.is_available()
            for role, agent in self.agents.items()
        }
