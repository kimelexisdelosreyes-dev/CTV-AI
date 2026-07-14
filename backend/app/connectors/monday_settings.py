import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# monday_settings.py → connectors → app → backend
BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env", override=False)


def split_csv(value: str | None) -> tuple[str, ...]:
    return tuple(
        item.strip()
        for item in (value or "").split(",")
        if item.strip()
    )


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
            enabled=os.getenv("MONDAY_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"},
            api_token=os.getenv("MONDAY_API_TOKEN", "").strip(),
            api_version=os.getenv(
                "MONDAY_API_VERSION",
                "2026-07",
            ).strip(),
            board_ids=split_csv(os.getenv("MONDAY_BOARD_IDS")),
            status_column_ids=split_csv(
                os.getenv("MONDAY_STATUS_COLUMN_IDS", "status")
            ),
            priority_column_ids=split_csv(
                os.getenv("MONDAY_PRIORITY_COLUMN_IDS", "priority")
            ),
            due_date_column_ids=split_csv(
                os.getenv(
                    "MONDAY_DUE_DATE_COLUMN_IDS",
                    "date,timeline",
                )
            ),
            people_column_ids=split_csv(
                os.getenv(
                    "MONDAY_PEOPLE_COLUMN_IDS",
                    "person,people",
                )
            ),
            timeout_seconds=float(
                os.getenv("MONDAY_REQUEST_TIMEOUT_SECONDS", "45")
            ),
            page_size=min(
                max(int(os.getenv("MONDAY_PAGE_SIZE", "100")), 1),
                500,
            ),
        )

    @property
    def configured(self) -> bool:
        return (
            self.enabled
            and bool(self.api_token)
            and bool(self.board_ids)
        )