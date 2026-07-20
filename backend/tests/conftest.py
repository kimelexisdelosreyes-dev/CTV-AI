"""Deterministic, external-service-free test process configuration."""

import os


TEST_ENVIRONMENT = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:1/ctv_one_test",
    "MONDAY_ENABLED": "false",
    "MONDAY_API_TOKEN": "",
    "MONDAY_BOARD_IDS": "",
    "OLLAMA_BASE_URL": "http://127.0.0.1:1",
    "QDRANT_URL": "http://127.0.0.1:1",
    "CTV_ONE_MONDAY_SNAPSHOT_REFRESH_ENABLED": "false",
}

for name, value in TEST_ENVIRONMENT.items():
    os.environ[name] = value
