"""Orchestra Status Dashboard - Minimal CLI dashboard for orchestration status."""

import argparse
import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text


STATE_FILE = Path(".orchestra/state.json")
REFRESH_INTERVAL = 2


def load_state() -> dict | None:
    """Load orchestration state from .orchestra/state.json."""
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def format_duration(start_time: str) -> str:
    """Format duration since start time as human-readable string."""
    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
        delta = now - start

        if delta.total_seconds() < 60:
            return f"{int(delta.total_seconds())}s ago"
        elif delta.total_seconds() < 3600:
            return f"{int(delta.total_seconds() // 60)}m ago"
        else:
            return f"{int(delta.total_seconds() // 3600)}h ago"
    except (ValueError, TypeError):
        return "unknown"


def render_dashboard(state: dict | None) -> Panel:
    """Render the dashboard as a Rich Panel."""
    if state is None:
        return Panel(
            Text("No orchestration data found", style="dim"),
            title="Orchestra Status",
            border_style="dim",
        )

    session_id = state.get("session_id", "unknown")[:8]
    started_at = state.get("started_at", "")
    duration = format_duration(started_at) if started_at else "unknown"

    # Count tasks by status
    tasks = state.get("tasks", [])
    pending = sum(1 for t in tasks if t.get("status") in ("pending", "claimed"))
    in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
    completed = sum(1 for t in tasks if t.get("status") == "completed")
    total = len(tasks)

    # Build content
    table = Table.grid(padding=(0, 1))
    table.add_column()

    # Session info
    session_text = Text()
    session_text.append(f"Session: ", style="dim")
    session_text.append(f"{session_id}", style="cyan")
    session_text.append(f" | Started: ", style="dim")
    session_text.append(f"{duration}", style="white")
    table.add_row(session_text)
    table.add_row(Text("-" * 50, style="dim"))

    # Task progress
    if total > 0:
        progress = Progress(
            TextColumn("Tasks   "),
            BarColumn(bar_width=30),
            TextColumn(f"{completed}/{total} complete"),
            expand=False,
        )
        task_id = progress.add_task("", total=total, completed=completed)
        table.add_row(progress)
    else:
        table.add_row(Text("Tasks    No tasks yet", style="dim"))

    # Task breakdown
    breakdown = Text()
    breakdown.append("         ")
    breakdown.append("* ", style="yellow")
    breakdown.append(f"{pending} pending  ")
    breakdown.append("* ", style="blue")
    breakdown.append(f"{in_progress} in progress  ")
    breakdown.append("* ", style="green")
    breakdown.append(f"{completed} done")
    table.add_row(breakdown)

    table.add_row(Text("-" * 50, style="dim"))

    # Escalation status
    escalation = state.get("escalation_reason")
    if escalation:
        esc_text = Text()
        esc_text.append("! ESCALATION: ", style="bold red")
        esc_text.append(escalation, style="red")
        table.add_row(esc_text)
    else:
        table.add_row(Text("[OK] No escalations", style="green"))

    return Panel(
        table,
        title="Orchestra Status",
        border_style="cyan",
    )


def main():
    """Main entry point for orchestra-status command."""
    parser = argparse.ArgumentParser(description="Show orchestration status")
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Watch mode - refresh every 2 seconds"
    )
    args = parser.parse_args()

    console = Console()

    if args.watch:
        try:
            with Live(render_dashboard(load_state()), console=console, refresh_per_second=1) as live:
                while True:
                    time.sleep(REFRESH_INTERVAL)
                    live.update(render_dashboard(load_state()))
        except KeyboardInterrupt:
            pass
    else:
        console.print(render_dashboard(load_state()))


if __name__ == "__main__":
    main()
