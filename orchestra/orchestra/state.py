"""State management for Orchestra - persists conversation state to disk."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from .models import (
    AgentRole,
    ConversationState,
    Message,
    MessageType,
    Priority,
    ReviewRequest,
    Task,
    TaskStatus,
    Vote,
)


class StateManager:
    """Manages persistent state for multi-agent communication."""

    def __init__(self, state_dir: str = ".orchestra"):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "state.json"
        self.conversation_log = self.state_dir / "conversation.md"
        self._state: Optional[ConversationState] = None

    async def initialize(self) -> ConversationState:
        """Initialize or load existing state."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

        if self.state_file.exists():
            async with aiofiles.open(self.state_file, "r") as f:
                data = json.loads(await f.read())
                self._state = ConversationState(**data)
        else:
            self._state = ConversationState()
            await self._save()

        return self._state

    async def _save(self):
        """Persist state to disk."""
        async with aiofiles.open(self.state_file, "w") as f:
            await f.write(self._state.model_dump_json(indent=2))

    async def _append_to_log(self, entry: str):
        """Append to human-readable conversation log."""
        async with aiofiles.open(self.conversation_log, "a") as f:
            await f.write(entry + "\n\n")

    @property
    def state(self) -> ConversationState:
        if self._state is None:
            raise RuntimeError("State not initialized. Call initialize() first.")
        return self._state

    # ─────────────────────────────────────────────────────────────
    # Message Operations
    # ─────────────────────────────────────────────────────────────

    async def send_message(
        self,
        from_agent: AgentRole,
        to_agent: Optional[AgentRole],
        content: str,
        message_type: MessageType = MessageType.TASK,
        priority: Priority = Priority.NORMAL,
        in_reply_to: Optional[str] = None,
    ) -> Message:
        """Send a message from one agent to another (or broadcast if to_agent is None)."""
        msg = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            priority=priority,
            in_reply_to=in_reply_to,
        )
        self.state.messages.append(msg)
        await self._save()

        # Log to conversation file
        target = to_agent.value if to_agent else "ALL"
        await self._append_to_log(
            f"---\n**[{msg.timestamp.isoformat()}]** `{from_agent.value}` → `{target}` ({message_type.value})\n\n{content}"
        )

        return msg

    async def get_inbox(self, agent: AgentRole, unread_only: bool = True) -> list[Message]:
        """Get messages for a specific agent."""
        messages = []
        for msg in self.state.messages:
            # Message is for this agent if: direct message OR broadcast (to_agent is None)
            is_for_agent = msg.to_agent == agent or msg.to_agent is None
            # Don't include own messages
            is_from_self = msg.from_agent == agent

            if is_for_agent and not is_from_self:
                if unread_only and msg.read:
                    continue
                messages.append(msg)

        return messages

    async def mark_read(self, message_id: str, agent: AgentRole):
        """Mark a message as read by an agent."""
        for msg in self.state.messages:
            if msg.id == message_id:
                msg.read = True
                break
        await self._save()

    async def get_conversation(self, limit: int = 50) -> list[Message]:
        """Get recent conversation history."""
        return self.state.messages[-limit:]

    # ─────────────────────────────────────────────────────────────
    # Task Operations
    # ─────────────────────────────────────────────────────────────

    async def create_task(
        self,
        title: str,
        description: str,
        created_by: AgentRole,
        assigned_to: Optional[AgentRole] = None,
        dependencies: Optional[list[str]] = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            title=title,
            description=description,
            created_by=created_by,
            assigned_to=assigned_to,
            dependencies=dependencies or [],
        )
        self.state.tasks.append(task)
        await self._save()

        await self._append_to_log(
            f"---\n**[TASK CREATED]** `{task.id}` by `{created_by.value}`\n\n"
            f"**Title:** {title}\n**Assigned:** {assigned_to.value if assigned_to else 'Unassigned'}\n\n{description}"
        )

        return task

    async def claim_task(self, task_id: str, agent: AgentRole) -> Optional[Task]:
        """Claim a task for work. Returns None if already claimed."""
        for task in self.state.tasks:
            if task.id == task_id:
                if task.claimed_by is not None and task.claimed_by != agent:
                    return None  # Already claimed by someone else

                # Check dependencies
                for dep_id in task.dependencies:
                    dep_task = await self.get_task(dep_id)
                    if dep_task and dep_task.status != TaskStatus.COMPLETED:
                        return None  # Dependency not complete

                task.claimed_by = agent
                task.status = TaskStatus.IN_PROGRESS
                task.updated_at = datetime.utcnow()
                await self._save()

                await self._append_to_log(
                    f"---\n**[TASK CLAIMED]** `{task_id}` claimed by `{agent.value}`"
                )
                return task

        return None

    async def complete_task(
        self,
        task_id: str,
        agent: AgentRole,
        result: str,
        files_modified: Optional[list[str]] = None,
    ) -> Optional[Task]:
        """Mark a task as complete with result."""
        for task in self.state.tasks:
            if task.id == task_id:
                if task.claimed_by != agent:
                    return None  # Not claimed by this agent

                task.status = TaskStatus.COMPLETED
                task.result = result
                task.files_modified = files_modified or []
                task.updated_at = datetime.utcnow()
                await self._save()

                await self._append_to_log(
                    f"---\n**[TASK COMPLETED]** `{task_id}` by `{agent.value}`\n\n"
                    f"**Result:**\n{result}\n\n**Files:** {', '.join(files_modified or [])}"
                )
                return task

        return None

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        for task in self.state.tasks:
            if task.id == task_id:
                return task
        return None

    async def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[AgentRole] = None,
    ) -> list[Task]:
        """Get tasks, optionally filtered."""
        tasks = self.state.tasks
        if status:
            tasks = [t for t in tasks if t.status == status]
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        return tasks

    # ─────────────────────────────────────────────────────────────
    # Review Operations
    # ─────────────────────────────────────────────────────────────

    async def request_review(
        self,
        from_agent: AgentRole,
        to_agent: AgentRole,
        content: str,
        task_id: Optional[str] = None,
        files: Optional[list[str]] = None,
    ) -> ReviewRequest:
        """Request a code review from another agent."""
        review = ReviewRequest(
            from_agent=from_agent,
            to_agent=to_agent,
            task_id=task_id,
            content=content,
            files=files or [],
        )
        self.state.reviews.append(review)
        await self._save()

        # Also send as message
        await self.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=f"[REVIEW REQUEST {review.id}]\n\n{content}",
            message_type=MessageType.REVIEW_REQUEST,
            priority=Priority.HIGH,
        )

        return review

    async def submit_review(
        self,
        review_id: str,
        agent: AgentRole,
        verdict: str,
        feedback: str,
    ) -> Optional[ReviewRequest]:
        """Submit a review verdict."""
        for review in self.state.reviews:
            if review.id == review_id and review.to_agent == agent:
                review.verdict = verdict
                review.feedback = feedback
                await self._save()

                # Send result back
                await self.send_message(
                    from_agent=agent,
                    to_agent=review.from_agent,
                    content=f"[REVIEW RESULT {review_id}]\n\n**Verdict:** {verdict}\n\n{feedback}",
                    message_type=MessageType.REVIEW_RESULT,
                    priority=Priority.HIGH,
                )

                return review
        return None

    async def get_pending_reviews(self, agent: AgentRole) -> list[ReviewRequest]:
        """Get reviews pending for an agent."""
        return [r for r in self.state.reviews if r.to_agent == agent and r.verdict is None]

    # ─────────────────────────────────────────────────────────────
    # Context Operations
    # ─────────────────────────────────────────────────────────────

    async def set_context(self, key: str, value: str):
        """Set a shared context value."""
        self.state.context[key] = value
        await self._save()

    async def get_context(self, key: str) -> Optional[str]:
        """Get a shared context value."""
        return self.state.context.get(key)

    async def append_context(self, key: str, value: str):
        """Append to a shared context value."""
        existing = self.state.context.get(key, "")
        self.state.context[key] = existing + "\n" + value if existing else value
        await self._save()

    async def get_all_context(self) -> dict[str, str]:
        """Get all shared context."""
        return self.state.context.copy()

    # ─────────────────────────────────────────────────────────────
    # Voting Operations
    # ─────────────────────────────────────────────────────────────

    async def create_vote(self, topic: str, options: list[str]) -> Vote:
        """Create a vote for agents to participate in."""
        vote = Vote(topic=topic, options=options)
        self.state.active_votes.append(vote)
        await self._save()

        await self.send_message(
            from_agent=AgentRole.CLAUDE,  # Votes initiated by orchestrator
            to_agent=None,  # Broadcast
            content=f"[VOTE] {topic}\n\nOptions: {', '.join(options)}\n\nPlease vote!",
            message_type=MessageType.BROADCAST,
        )

        return vote

    async def cast_vote(self, topic: str, agent: AgentRole, choice: str) -> Optional[Vote]:
        """Cast a vote."""
        for vote in self.state.active_votes:
            if vote.topic == topic:
                if choice in vote.options:
                    vote.votes[agent.value] = choice
                    await self._save()
                    return vote
        return None

    # ─────────────────────────────────────────────────────────────
    # Escalation
    # ─────────────────────────────────────────────────────────────

    async def escalate_to_human(self, agent: AgentRole, reason: str):
        """Request human intervention."""
        self.state.human_intervention_requested = True
        self.state.escalation_reason = reason
        await self._save()

        await self._append_to_log(
            f"---\n**[ESCALATION]** `{agent.value}` requests human intervention\n\n{reason}"
        )

        await self.send_message(
            from_agent=agent,
            to_agent=None,
            content=f"[ESCALATION] Human intervention requested: {reason}",
            message_type=MessageType.ESCALATION,
            priority=Priority.URGENT,
        )

    async def clear_escalation(self):
        """Clear escalation after human intervenes."""
        self.state.human_intervention_requested = False
        self.state.escalation_reason = None
        await self._save()

    # ─────────────────────────────────────────────────────────────
    # Session Management
    # ─────────────────────────────────────────────────────────────

    async def set_initial_prompt(self, prompt: str):
        """Set the initial user prompt for this session."""
        self.state.initial_prompt = prompt
        await self._save()

        await self._append_to_log(
            f"# Orchestra Session `{self.state.session_id}`\n\n"
            f"**Started:** {self.state.started_at.isoformat()}\n\n"
            f"## Initial Prompt\n\n{prompt}"
        )

    async def reset(self):
        """Reset state for a new session."""
        self._state = ConversationState()
        await self._save()

        # Clear conversation log
        if self.conversation_log.exists():
            self.conversation_log.unlink()

    async def get_status(self) -> dict:
        """Get current orchestration status."""
        pending_tasks = len([t for t in self.state.tasks if t.status == TaskStatus.PENDING])
        in_progress = len([t for t in self.state.tasks if t.status == TaskStatus.IN_PROGRESS])
        completed = len([t for t in self.state.tasks if t.status == TaskStatus.COMPLETED])

        return {
            "session_id": self.state.session_id,
            "started_at": self.state.started_at.isoformat(),
            "message_count": len(self.state.messages),
            "tasks": {
                "pending": pending_tasks,
                "in_progress": in_progress,
                "completed": completed,
                "total": len(self.state.tasks),
            },
            "pending_reviews": len([r for r in self.state.reviews if r.verdict is None]),
            "human_intervention_requested": self.state.human_intervention_requested,
            "escalation_reason": self.state.escalation_reason,
        }
