import os
from dataclasses import dataclass


def split_csv(value: str | None) -> tuple[str, ...]:
    return tuple(x.strip() for x in (value or "").split(",") if x.strip())


@dataclass(frozen=True)
class MondaySettings:
    enabled: bool
    api_token: str
    api_version: str
    board_ids: tuple[str, ...]
    status_column_ids: tuple[str, ...]
    priority_column_ids: tuple[str, ...]
    due_date_column_ids: tuple[str, ...]
    people_column_ids: tuple[str, ...]
    timeout_seconds: float
    page_size: int

    @classmethod
    def from_env(cls) -> "MondaySettings":
        return cls(
            enabled=os.getenv("MONDAY_ENABLED", "false").lower() in {"1","true","yes","on"},
            api_token=os.getenv("MONDAY_API_TOKEN", "").strip(),
            api_version=os.getenv("MONDAY_API_VERSION", "2026-07").strip(),
            board_ids=split_csv(os.getenv("MONDAY_BOARD_IDS")),
            status_column_ids=split_csv(os.getenv("MONDAY_STATUS_COLUMN_IDS", "status")),
            priority_column_ids=split_csv(os.getenv("MONDAY_PRIORITY_COLUMN_IDS", "priority")),
            due_date_column_ids=split_csv(os.getenv("MONDAY_DUE_DATE_COLUMN_IDS", "date,timeline")),
            people_column_ids=split_csv(os.getenv("MONDAY_PEOPLE_COLUMN_IDS", "person,people")),
            timeout_seconds=float(os.getenv("MONDAY_REQUEST_TIMEOUT_SECONDS", "45")),
            page_size=min(max(int(os.getenv("MONDAY_PAGE_SIZE", "100")), 1), 500),
        )

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.api_token) and bool(self.board_ids)
