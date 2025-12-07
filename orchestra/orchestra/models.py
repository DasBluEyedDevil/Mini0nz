"""Data models for Orchestra multi-agent communication."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class AgentRole(str, Enum):
    CLAUDE = "claude"
    GEMINI = "gemini"
    CODEX = "codex"
    COPILOT = "copilot"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class MessageType(str, Enum):
    TASK = "task"
    QUESTION = "question"
    RESPONSE = "response"
    REVIEW_REQUEST = "review_request"
    REVIEW_RESULT = "review_result"
    BROADCAST = "broadcast"
    ESCALATION = "escalation"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    from_agent: AgentRole
    to_agent: Optional[AgentRole] = None  # None = broadcast
    message_type: MessageType
    content: str
    priority: Priority = Priority.NORMAL
    in_reply_to: Optional[str] = None
    read: bool = False


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    created_by: AgentRole
    assigned_to: Optional[AgentRole] = None
    claimed_by: Optional[AgentRole] = None
    dependencies: list[str] = Field(default_factory=list)
    result: Optional[str] = None
    files_modified: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    from_agent: AgentRole
    to_agent: AgentRole
    task_id: Optional[str] = None
    content: str
    files: list[str] = Field(default_factory=list)
    verdict: Optional[str] = None  # APPROVED, NEEDS_CHANGES, REJECTED
    feedback: Optional[str] = None


class Vote(BaseModel):
    topic: str
    options: list[str]
    votes: dict[str, str] = Field(default_factory=dict)  # agent -> choice
    deadline: Optional[datetime] = None
    result: Optional[str] = None


class ConversationState(BaseModel):
    """Full state of the multi-agent conversation."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = Field(default_factory=datetime.utcnow)
    initial_prompt: Optional[str] = None
    messages: list[Message] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    reviews: list[ReviewRequest] = Field(default_factory=list)
    context: dict[str, str] = Field(default_factory=dict)
    active_votes: list[Vote] = Field(default_factory=list)
    human_intervention_requested: bool = False
    escalation_reason: Optional[str] = None
