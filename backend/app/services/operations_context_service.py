import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from app.connectors.base import ConnectorError
from app.connectors.manager import connector_manager
from app.connectors.models import ConnectorTask
from app.services.intelligence_router import intelligence_router


@dataclass
class OperationsContext:
    applied: bool
    text: str
    task_count: int
    board_count: int
    summary: str | None


def _done(status: str | None) -> bool:
    value = (status or "").lower()
    return any(term in value for term in ("done", "complete", "completed", "finished"))


def _overdue(task: ConnectorTask, now: datetime) -> bool:
    return bool(task.due_at and not _done(task.status) and task.due_at < now)


def _due_today(task: ConnectorTask, now: datetime) -> bool:
    return bool(
        task.due_at
        and not _done(task.status)
        and task.due_at.astimezone(timezone.utc).date() == now.date()
    )


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 3
    }


def _question_is_operational(question: str) -> bool:
    return intelligence_router.route(question).use_operations


def _task_score(task: ConnectorTask, question_tokens: set[str], now: datetime) -> float:
    board = str(task.metadata.get("board_name") or "")
    group = str(task.metadata.get("group_title") or "")
    haystack = _tokens(
        " ".join(
            (
                task.title,
                task.status or "",
                task.priority or "",
                board,
                group,
            )
        )
    )

    score = float(len(question_tokens & haystack) * 5)

    priority = (task.priority or "").lower()
    status = (task.status or "").lower()

    if "critical" in priority or "urgent" in priority:
        score += 8
    elif "high" in priority:
        score += 5

    if _overdue(task, now):
        score += 10
    elif _due_today(task, now):
        score += 8

    if "stuck" in status or "blocked" in status:
        score += 8

    return score


class OperationsContextService:
    async def build(
        self,
        question: str,
        max_tasks: int = 12,
        max_boards: int = 10,
        force: bool = False,
    ) -> OperationsContext:
        if not force:
            return OperationsContext(
                applied=False,
                text="",
                task_count=0,
                board_count=0,
                summary=None,
            )

        try:
            tasks = await connector_manager.tasks("monday")
            projects = await connector_manager.projects("monday")
        except ConnectorError:
            return OperationsContext(
                applied=False,
                text="",
                task_count=0,
                board_count=0,
                summary=None,
            )

        now = datetime.now(timezone.utc)
        question_tokens = _tokens(question)

        active = [task for task in tasks if not _done(task.status)]
        completed = [task for task in tasks if _done(task.status)]
        overdue = [task for task in active if _overdue(task, now)]
        due_today = [task for task in active if _due_today(task, now)]

        board_counts = Counter(
            str(task.metadata.get("board_name") or "Unknown board")
            for task in tasks
        )

        ranked = sorted(
            active,
            key=lambda task: _task_score(task, question_tokens, now),
            reverse=True,
        )[:max_tasks]

        task_lines: list[str] = []

        for index, task in enumerate(ranked, 1):
            board = str(task.metadata.get("board_name") or "Unknown board")
            group = str(task.metadata.get("group_title") or "No group")
            due = (
                task.due_at.astimezone(timezone.utc).date().isoformat()
                if task.due_at
                else "No deadline"
            )

            days_overdue = None
            if _overdue(task, now) and task.due_at:
                days_overdue = (now.date() - task.due_at.date()).days

            task_lines.append(
                f"[Monday Task {index}] {task.title}\n"
                f"Board: {board}\n"
                f"Group: {group}\n"
                f"Status: {task.status or 'Not set'}\n"
                f"Priority: {task.priority or 'Not set'}\n"
                f"Deadline: {due}\n"
                f"Days overdue: {days_overdue if days_overdue is not None else 'Not overdue'}\n"
                f"URL: {task.url or 'Not available'}"
            )

        board_lines = [
            f"- {name}: {count} task(s)"
            for name, count in board_counts.most_common(max_boards)
        ]

        summary = (
            f"{len(active)} active; {len(overdue)} overdue; "
            f"{len(due_today)} due today; {len(completed)} completed."
        )

        text = f"""
LIVE OPERATIONAL CONTEXT — MONDAY.COM

Current UTC date
- {now.date().isoformat()}

Operational summary
- Total tasks: {len(tasks)}
- Active tasks: {len(active)}
- Completed tasks: {len(completed)}
- Overdue tasks: {len(overdue)}
- Due today: {len(due_today)}
- Connected boards: {len(projects)}

Board workload
{chr(10).join(board_lines) if board_lines else "- No board data"}

Relevant operational items
{chr(10).join(task_lines) if task_lines else "- No relevant active tasks"}

Rules
- monday.com is the source of truth for operational facts.
- Cite tasks as [Monday Task 1], [Monday Task 2], and so on.
- Never label an old deadline as today.
- Use the backend-computed Days overdue field.
- Never claim that a task was modified.
""".strip()

        return OperationsContext(
            applied=True,
            text=text,
            task_count=len(ranked),
            board_count=min(len(board_counts), max_boards),
            summary=summary,
        )


operations_context_service = OperationsContextService()
