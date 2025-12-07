"""Orchestra MCP Server - Multi-Agent Autonomous Communication."""

import asyncio
import json
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .models import AgentRole, MessageType, Priority, TaskStatus
from .state import StateManager

# Initialize
server = Server("orchestra")
state_manager = StateManager(
    state_dir=os.environ.get("ORCHESTRA_STATE_DIR", ".orchestra")
)

# Track which agent is calling (set via environment or inferred)
def get_current_agent() -> AgentRole:
    """Determine which agent is making the call."""
    agent = os.environ.get("ORCHESTRA_AGENT", "claude")
    return AgentRole(agent.lower())


# ─────────────────────────────────────────────────────────────────────────────
# Tool Definitions
# ─────────────────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Orchestra tools."""
    return [
        # Communication
        Tool(
            name="orchestra_send_message",
            description="Send a message to another agent. Use to_agent='broadcast' to send to all.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_agent": {
                        "type": "string",
                        "enum": ["claude", "gemini", "codex", "copilot", "broadcast"],
                        "description": "Target agent or 'broadcast' for all"
                    },
                    "content": {"type": "string", "description": "Message content"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "default": "normal"
                    },
                    "message_type": {
                        "type": "string",
                        "enum": ["task", "question", "response", "review_request"],
                        "default": "response"
                    },
                    "in_reply_to": {
                        "type": "string",
                        "description": "Message ID this is replying to (optional)"
                    }
                },
                "required": ["to_agent", "content"]
            }
        ),
        Tool(
            name="orchestra_get_inbox",
            description="Get messages in your inbox. Returns unread messages by default.",
            inputSchema={
                "type": "object",
                "properties": {
                    "unread_only": {
                        "type": "boolean",
                        "default": True,
                        "description": "Only return unread messages"
                    }
                }
            }
        ),
        Tool(
            name="orchestra_get_conversation",
            description="Get the full conversation history between all agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum messages to return"
                    }
                }
            }
        ),

        # Task Management
        Tool(
            name="orchestra_create_task",
            description="Create a new task and optionally assign it to an agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short task title"},
                    "description": {"type": "string", "description": "Detailed task description"},
                    "assigned_to": {
                        "type": "string",
                        "enum": ["claude", "gemini", "codex", "copilot"],
                        "description": "Agent to assign (optional)"
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs that must complete first"
                    }
                },
                "required": ["title", "description"]
            }
        ),
        Tool(
            name="orchestra_claim_task",
            description="Claim an available task to work on. Prevents others from working on it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to claim"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="orchestra_complete_task",
            description="Mark a claimed task as complete with results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to complete"},
                    "result": {"type": "string", "description": "Result/output of the task"},
                    "files_modified": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files modified"
                    }
                },
                "required": ["task_id", "result"]
            }
        ),
        Tool(
            name="orchestra_get_tasks",
            description="Get tasks, optionally filtered by status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "claimed", "in_progress", "review", "completed", "blocked"],
                        "description": "Filter by status (optional)"
                    }
                }
            }
        ),

        # Code Review
        Tool(
            name="orchestra_request_review",
            description="Request a code review from another agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_agent": {
                        "type": "string",
                        "enum": ["claude", "gemini", "codex", "copilot"],
                        "description": "Agent to review"
                    },
                    "content": {"type": "string", "description": "What to review (code, changes, etc.)"},
                    "task_id": {"type": "string", "description": "Related task ID (optional)"},
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to review"
                    }
                },
                "required": ["to_agent", "content"]
            }
        ),
        Tool(
            name="orchestra_submit_review",
            description="Submit a code review verdict.",
            inputSchema={
                "type": "object",
                "properties": {
                    "review_id": {"type": "string", "description": "Review request ID"},
                    "verdict": {
                        "type": "string",
                        "enum": ["APPROVED", "NEEDS_CHANGES", "REJECTED"],
                        "description": "Review verdict"
                    },
                    "feedback": {"type": "string", "description": "Detailed feedback"}
                },
                "required": ["review_id", "verdict", "feedback"]
            }
        ),
        Tool(
            name="orchestra_get_pending_reviews",
            description="Get reviews waiting for you to complete.",
            inputSchema={"type": "object", "properties": {}}
        ),

        # Shared Context
        Tool(
            name="orchestra_set_context",
            description="Store shared context that all agents can access.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Context key"},
                    "value": {"type": "string", "description": "Context value"}
                },
                "required": ["key", "value"]
            }
        ),
        Tool(
            name="orchestra_get_context",
            description="Retrieve shared context by key, or all context if no key provided.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Context key (optional)"}
                }
            }
        ),
        Tool(
            name="orchestra_append_context",
            description="Append to existing shared context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Context key"},
                    "value": {"type": "string", "description": "Value to append"}
                },
                "required": ["key", "value"]
            }
        ),

        # Orchestration
        Tool(
            name="orchestra_start_session",
            description="Start a new orchestration session with an initial prompt.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Initial user prompt/task"}
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="orchestra_get_status",
            description="Get the current status of the orchestration session.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="orchestra_escalate",
            description="Request human intervention when stuck or need clarification.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Why human intervention is needed"}
                },
                "required": ["reason"]
            }
        ),
        Tool(
            name="orchestra_vote",
            description="Cast a vote on a topic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Vote topic"},
                    "choice": {"type": "string", "description": "Your vote choice"}
                },
                "required": ["topic", "choice"]
            }
        ),
        Tool(
            name="orchestra_create_vote",
            description="Create a new vote for agents to participate in.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "What to vote on"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Vote options"
                    }
                },
                "required": ["topic", "options"]
            }
        ),
        Tool(
            name="orchestra_reset",
            description="Reset the session and start fresh. Use with caution.",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tool Handlers
# ─────────────────────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    await state_manager.initialize()
    agent = get_current_agent()

    try:
        result = await _handle_tool(name, arguments, agent)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _handle_tool(name: str, args: dict[str, Any], agent: AgentRole) -> dict:
    """Route tool calls to handlers."""

    # ─── Communication ───
    if name == "orchestra_send_message":
        to = args["to_agent"]
        to_agent = None if to == "broadcast" else AgentRole(to)
        msg = await state_manager.send_message(
            from_agent=agent,
            to_agent=to_agent,
            content=args["content"],
            message_type=MessageType(args.get("message_type", "response")),
            priority=Priority(args.get("priority", "normal")),
            in_reply_to=args.get("in_reply_to"),
        )
        return {"success": True, "message_id": msg.id}

    elif name == "orchestra_get_inbox":
        messages = await state_manager.get_inbox(
            agent=agent,
            unread_only=args.get("unread_only", True)
        )
        return {
            "agent": agent.value,
            "message_count": len(messages),
            "messages": [m.model_dump() for m in messages]
        }

    elif name == "orchestra_get_conversation":
        messages = await state_manager.get_conversation(limit=args.get("limit", 50))
        return {
            "message_count": len(messages),
            "messages": [m.model_dump() for m in messages]
        }

    # ─── Task Management ───
    elif name == "orchestra_create_task":
        assigned = AgentRole(args["assigned_to"]) if args.get("assigned_to") else None
        task = await state_manager.create_task(
            title=args["title"],
            description=args["description"],
            created_by=agent,
            assigned_to=assigned,
            dependencies=args.get("dependencies"),
        )
        return {"success": True, "task_id": task.id, "task": task.model_dump()}

    elif name == "orchestra_claim_task":
        task = await state_manager.claim_task(args["task_id"], agent)
        if task:
            return {"success": True, "task": task.model_dump()}
        return {"success": False, "error": "Could not claim task (already claimed or dependencies not met)"}

    elif name == "orchestra_complete_task":
        task = await state_manager.complete_task(
            task_id=args["task_id"],
            agent=agent,
            result=args["result"],
            files_modified=args.get("files_modified"),
        )
        if task:
            return {"success": True, "task": task.model_dump()}
        return {"success": False, "error": "Could not complete task (not claimed by you)"}

    elif name == "orchestra_get_tasks":
        status = TaskStatus(args["status"]) if args.get("status") else None
        tasks = await state_manager.get_tasks(status=status)
        return {
            "task_count": len(tasks),
            "tasks": [t.model_dump() for t in tasks]
        }

    # ─── Code Review ───
    elif name == "orchestra_request_review":
        review = await state_manager.request_review(
            from_agent=agent,
            to_agent=AgentRole(args["to_agent"]),
            content=args["content"],
            task_id=args.get("task_id"),
            files=args.get("files"),
        )
        return {"success": True, "review_id": review.id}

    elif name == "orchestra_submit_review":
        review = await state_manager.submit_review(
            review_id=args["review_id"],
            agent=agent,
            verdict=args["verdict"],
            feedback=args["feedback"],
        )
        if review:
            return {"success": True, "review": review.model_dump()}
        return {"success": False, "error": "Review not found or not assigned to you"}

    elif name == "orchestra_get_pending_reviews":
        reviews = await state_manager.get_pending_reviews(agent)
        return {
            "pending_count": len(reviews),
            "reviews": [r.model_dump() for r in reviews]
        }

    # ─── Shared Context ───
    elif name == "orchestra_set_context":
        await state_manager.set_context(args["key"], args["value"])
        return {"success": True, "key": args["key"]}

    elif name == "orchestra_get_context":
        if args.get("key"):
            value = await state_manager.get_context(args["key"])
            return {"key": args["key"], "value": value}
        else:
            context = await state_manager.get_all_context()
            return {"context": context}

    elif name == "orchestra_append_context":
        await state_manager.append_context(args["key"], args["value"])
        return {"success": True, "key": args["key"]}

    # ─── Orchestration ───
    elif name == "orchestra_start_session":
        await state_manager.set_initial_prompt(args["prompt"])
        return {
            "success": True,
            "session_id": state_manager.state.session_id,
            "message": "Session started. Create tasks and assign to agents."
        }

    elif name == "orchestra_get_status":
        return await state_manager.get_status()

    elif name == "orchestra_escalate":
        await state_manager.escalate_to_human(agent, args["reason"])
        return {"success": True, "message": "Human intervention requested"}

    elif name == "orchestra_vote":
        vote = await state_manager.cast_vote(args["topic"], agent, args["choice"])
        if vote:
            return {"success": True, "votes_cast": len(vote.votes)}
        return {"success": False, "error": "Vote not found or invalid choice"}

    elif name == "orchestra_create_vote":
        vote = await state_manager.create_vote(args["topic"], args["options"])
        return {"success": True, "topic": vote.topic, "options": vote.options}

    elif name == "orchestra_reset":
        await state_manager.reset()
        return {"success": True, "message": "Session reset"}

    else:
        return {"error": f"Unknown tool: {name}"}


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Run the Orchestra MCP server."""
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
