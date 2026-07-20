from __future__ import annotations

import hashlib
import json
import re

from app.supervisor.agent_registry import AgentRegistry
from app.supervisor.schemas import ExecutionPlan


COMPOSER_PROMPT_VERSION = "v2-c1-composer-1"


def normalize_supervisor_request(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().casefold())


def supervisor_cache_fingerprint(
    *,
    question: str,
    plan: ExecutionPlan,
    registry: AgentRegistry,
    knowledge_revision: str | None,
    operations_content_hash: str | None,
    employee_scope: str | None,
    composer_prompt_version: str = COMPOSER_PROMPT_VERSION,
) -> str:
    """Build a non-reversible supervised-result cache key.

    The cache is disabled by default. Callers must supply current source revisions
    before a future cache implementation may use this fingerprint.
    """
    agent_versions = {
        agent_id: registry.get(agent_id).definition.version
        for agent_id in sorted(set(plan.required_agents))
    }
    payload = {
        "normalized_request": normalize_supervisor_request(question),
        "capabilities": sorted({task.capability for task in plan.tasks}),
        "knowledge_revision": knowledge_revision,
        "operations_content_hash": operations_content_hash,
        "employee_scope": employee_scope,
        "agent_versions": agent_versions,
        "planner_version": plan.planner_version,
        "composer_prompt_version": composer_prompt_version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
