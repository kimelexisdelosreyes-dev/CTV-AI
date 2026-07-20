import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectorError
from app.connectors.models import (
    ConnectorCapability, ConnectorHealth, ConnectorIdentity,
    ConnectorProject, ConnectorSearchResult, ConnectorStatus, ConnectorTask,
)
from app.connectors.monday_settings import MondaySettings


class MondayApiError(ConnectorError):
    category = "monday_api_error"
    retryable = False

    def __init__(
        self,
        safe_detail: str = "Monday data could not be retrieved safely.",
        *,
        category: str | None = None,
        retryable: bool | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(safe_detail)
        self.safe_detail = safe_detail
        self.category = category or self.category
        self.retryable = self.retryable if retryable is None else retryable
        self.retry_after_seconds = retry_after_seconds


class MondayConnector(BaseConnector):
    name = "monday"
    display_name = "monday.com"
    description = "Read-only tasks and projects from configured monday boards."
    capabilities = {
        ConnectorCapability.health,
        ConnectorCapability.identity,
        ConnectorCapability.tasks,
        ConnectorCapability.projects,
        ConnectorCapability.search,
    }

    def __init__(self, config: MondaySettings | None = None) -> None:
        self.config = config or MondaySettings.from_env()
        self.enabled = self.config.configured
        self.last_task_fetch_diagnostics: dict[str, object] = {}

    async def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.config.configured:
            raise MondayApiError(
                "Monday is not configured.",
                category="monday_not_configured",
            )
        headers = {
            "Authorization": self.config.api_token,
            "Content-Type": "application/json",
            "API-Version": self.config.api_version,
        }
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(
                    "https://api.monday.com/v2",
                    headers=headers,
                    json={"query": query, "variables": variables or {}},
                )
        except httpx.TimeoutException as exc:
            raise MondayApiError(
                "Monday request timed out.",
                category="monday_timeout",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise MondayApiError(
                "Monday is temporarily unavailable.",
                category="monday_network_error",
                retryable=True,
            ) from exc

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            try:
                retry_after_seconds = float(retry_after) if retry_after else None
            except ValueError:
                retry_after_seconds = None
            raise MondayApiError(
                "Monday rate limit reached.",
                category="monday_rate_limited",
                retryable=True,
                retry_after_seconds=retry_after_seconds,
            )
        if response.status_code in {401, 403}:
            raise MondayApiError(
                "Monday authentication failed.",
                category="monday_authentication_failed",
            )
        if response.status_code >= 500:
            raise MondayApiError(
                "Monday is temporarily unavailable.",
                category="monday_upstream_error",
                retryable=True,
            )
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPStatusError, ValueError) as exc:
            raise MondayApiError(
                "Monday returned an invalid response.",
                category="monday_invalid_response",
            ) from exc

        if payload.get("errors"):
            raise MondayApiError(
                "Monday rejected the requested operation.",
                category="monday_graphql_error",
            )

        return payload.get("data") or {}

    async def health(self) -> ConnectorHealth:
        started = perf_counter()
        if not self.config.configured:
            return ConnectorHealth(
                name=self.name,
                status=ConnectorStatus.disabled,
                checked_at=datetime.now(timezone.utc),
                detail="monday.com is not configured.",
            )
        try:
            data = await self._graphql("query { version { value } me { id name email } }")
            me = data.get("me") or {}
            version = (data.get("version") or {}).get("value") or self.config.api_version
            return ConnectorHealth(
                name=self.name,
                status=ConnectorStatus.healthy,
                checked_at=datetime.now(timezone.utc),
                latency_ms=(perf_counter() - started) * 1000,
                detail=f"Authenticated as {me.get('name') or me.get('email')}; API {version}.",
            )
        except Exception as exc:
            return ConnectorHealth(
                name=self.name,
                status=ConnectorStatus.unavailable,
                checked_at=datetime.now(timezone.utc),
                latency_ms=(perf_counter() - started) * 1000,
                detail=str(exc),
            )

    async def get_identity(self, user_email: str) -> ConnectorIdentity | None:
        data = await self._graphql(
            "query ($emails: [String!]) { users(emails: $emails) { id name email is_active } }",
            {"emails": [user_email.lower()]},
        )
        users = data.get("users") or []
        if not users:
            return None
        user = users[0]
        return ConnectorIdentity(
            external_user_id=str(user["id"]),
            display_name=user.get("name"),
            email=user.get("email"),
            metadata={"is_active": user.get("is_active")},
        )

    async def get_projects(self) -> list[ConnectorProject]:
        data = await self._graphql(
            '''
            query ($ids: [ID!]) {
              boards(ids: $ids) {
                id name description state board_kind updated_at url
                owners { id name email }
              }
            }
            ''',
            {"ids": list(self.config.board_ids)},
        )
        return [
            ConnectorProject(
                external_id=str(board["id"]),
                name=board["name"],
                status=board.get("state") or board.get("board_kind"),
                owner_ids=[str(owner["id"]) for owner in board.get("owners") or []],
                url=board.get("url"),
                metadata={
                    "description": board.get("description"),
                    "board_kind": board.get("board_kind"),
                    "updated_at": board.get("updated_at"),
                },
            )
            for board in data.get("boards") or []
        ]

    async def _items(
        self,
        board_id: str,
    ) -> tuple[list[dict[str, Any]], dict[str, object]]:
        query = '''
        query ($ids: [ID!], $limit: Int!, $cursor: String) {
          boards(ids: $ids) {
            id name url
            items_page(limit: $limit, cursor: $cursor) {
              cursor
              items {
                id name created_at updated_at url
                group { id title }
                column_values {
                  id type text value
                  column { title }
                }
              }
            }
          }
        }
        '''
        cursor = None
        results: list[dict[str, Any]] = []
        seen_cursors: set[str] = set()
        groups: set[str] = set()
        pages = 0
        board_returned = False

        while True:
            pages += 1
            if pages > 100:
                raise MondayApiError("monday.com pagination exceeded the safe page limit.")
            data = await self._graphql(
                query,
                {"ids": [board_id], "limit": self.config.page_size, "cursor": cursor},
            )
            boards = data.get("boards") or []
            if not boards:
                break
            board = boards[0]
            board_returned = True
            page = board.get("items_page") or {}
            for item in page.get("items") or []:
                item["_board"] = {"id": str(board["id"]), "name": board.get("name"), "url": board.get("url")}
                results.append(item)
                group_id = str((item.get("group") or {}).get("id") or "")
                if group_id:
                    groups.add(group_id)
            cursor = page.get("cursor")
            if not cursor:
                break
            if cursor in seen_cursors:
                raise MondayApiError("monday.com returned a repeated pagination cursor.")
            seen_cursors.add(cursor)

        return results, {
            "board_returned": board_returned,
            "groups_returned": len(groups),
            "raw_items_count": len(results),
            "pages_fetched": pages,
        }

    def _column(self, item, candidates, titles, types):
        columns = item.get("column_values") or []
        for col in columns:
            if str(col.get("id", "")).lower() in {x.lower() for x in candidates}:
                return col
        for col in columns:
            title = str((col.get("column") or {}).get("title") or "").lower()
            if any(word in title for word in titles):
                return col
        for col in columns:
            if str(col.get("type") or "").lower() in types:
                return col
        return None

    def _people(self, col):
        if not col:
            return []
        try:
            raw = json.loads(col.get("value") or "{}")
        except json.JSONDecodeError:
            return []
        return [
            str(person["id"])
            for person in raw.get("personsAndTeams") or []
            if person.get("kind") == "person" and person.get("id") is not None
        ]

    def _date(self, col):
        if not col:
            return None
        try:
            raw = json.loads(col.get("value") or "{}")
        except json.JSONDecodeError:
            raw = {}
        value = raw.get("date") or raw.get("to") or col.get("text")
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value)[:10])
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def _normalize(self, item) -> ConnectorTask:
        status = self._column(item, self.config.status_column_ids, ("status","stage","progress"), ("status",))
        priority = self._column(item, self.config.priority_column_ids, ("priority","urgency"), ("dropdown",))
        due = self._column(item, self.config.due_date_column_ids, ("due","deadline","date","timeline"), ("date","timeline"))
        people = self._column(item, self.config.people_column_ids, ("person","people","owner","assignee"), ("people",))
        board = item.get("_board") or {}
        group = item.get("group") or {}

        return ConnectorTask(
            external_id=str(item["id"]),
            title=item["name"],
            status=(status or {}).get("text") or None,
            priority=(priority or {}).get("text") or None,
            due_at=self._date(due),
            assignee_ids=self._people(people),
            project_id=str(board.get("id")) if board.get("id") else None,
            url=item.get("url"),
            metadata={
                "board_name": board.get("name"),
                "board_url": board.get("url"),
                "group_id": group.get("id"),
                "group_title": group.get("title"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            },
        )

    async def get_tasks(self, external_user_id: str | None = None) -> list[ConnectorTask]:
        tasks: list[ConnectorTask] = []
        diagnostics: dict[str, object] = {
            "boards_requested": len(self.config.board_ids),
            "boards_returned": 0,
            "groups_returned": 0,
            "raw_items_count": 0,
            "normalized_tasks_count": 0,
            "skipped_items_count": 0,
            "skip_reason_counts": {},
            "pages_fetched": 0,
        }
        for board_id in self.config.board_ids:
            items, board_metrics = await self._items(board_id)
            diagnostics["boards_returned"] += int(board_metrics["board_returned"])
            diagnostics["groups_returned"] += int(board_metrics["groups_returned"])
            diagnostics["raw_items_count"] += int(board_metrics["raw_items_count"])
            diagnostics["pages_fetched"] += int(board_metrics["pages_fetched"])
            for item in items:
                try:
                    task = self._normalize(item)
                except (KeyError, TypeError, ValueError):
                    diagnostics["skipped_items_count"] += 1
                    diagnostics["skip_reason_counts"] = {"normalization_error": diagnostics["skipped_items_count"]}
                    continue
                if external_user_id and external_user_id not in task.assignee_ids:
                    continue
                tasks.append(task)
        diagnostics["normalized_tasks_count"] = len(tasks)
        self.last_task_fetch_diagnostics = diagnostics
        return tasks

    async def search(self, query: str, limit: int = 10) -> list[ConnectorSearchResult]:
        needle = query.lower().strip()
        results: list[ConnectorSearchResult] = []

        for project in await self.get_projects():
            if needle in f"{project.name} {project.status or ''}".lower():
                results.append(
                    ConnectorSearchResult(
                        connector=self.name,
                        result_type="project",
                        external_id=project.external_id,
                        title=project.name,
                        snippet=project.status,
                        url=project.url,
                        score=1.0,
                        metadata=project.metadata,
                    )
                )

        for task in await self.get_tasks():
            if len(results) >= limit:
                break
            text = f"{task.title} {task.status or ''} {task.priority or ''}".lower()
            if needle in text:
                results.append(
                    ConnectorSearchResult(
                        connector=self.name,
                        result_type="task",
                        external_id=task.external_id,
                        title=task.title,
                        snippet=f"Status: {task.status or 'Unknown'}; Priority: {task.priority or 'Unknown'}",
                        url=task.url,
                        score=1.0,
                        metadata=task.metadata,
                    )
                )

        return results[:limit]
