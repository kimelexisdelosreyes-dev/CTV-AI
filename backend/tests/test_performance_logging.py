import json
import logging

from app.core.config import settings
from app.core.logging import configure_performance_file_logging


def test_performance_jsonl_persistence(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "performance.jsonl"
    logger = logging.getLogger("ctv_one.performance")

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    monkeypatch.setattr(settings, "performance_log_path", str(log_path))
    monkeypatch.setattr(settings, "performance_log_max_bytes", 100_000)
    monkeypatch.setattr(settings, "performance_log_backup_count", 1)

    configure_performance_file_logging()
    logger.info(
        {
            "event": "company_brain_performance",
            "request_id": "request-1",
            "success": False,
            "error_category": "embedding_model_missing",
            "metrics": {"final_prompt_chars": 12},
        }
    )

    for handler in logger.handlers:
        handler.flush()

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "company_brain_performance"
    assert payload["error_category"] == "embedding_model_missing"


def test_performance_jsonl_does_not_include_sensitive_text(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "performance.jsonl"
    logger = logging.getLogger("ctv_one.performance")

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    monkeypatch.setattr(settings, "performance_log_path", str(log_path))
    configure_performance_file_logging()
    logger.info(
        {
            "event": "company_brain_performance",
            "request_id": "request-2",
            "metrics": {"final_prompt_chars": 20},
        }
    )

    for handler in logger.handlers:
        handler.flush()

    text = log_path.read_text(encoding="utf-8")
    assert "Bearer" not in text
    assert "secret prompt" not in text
    assert "document text" not in text
