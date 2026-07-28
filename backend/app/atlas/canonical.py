"""Canonical, JSON-safe serialization and practical deep immutability for Atlas."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict


class FrozenJson:
    """An immutable JSON tree kept as canonical UTF-8 JSON text."""
    __slots__ = ("_json",)

    def __init__(self, value: Any = None) -> None:
        self._json = canonical_json(value)

    def to_python(self) -> Any:
        return json.loads(self._json)

    def __repr__(self) -> str:
        return f"FrozenJson({self._json!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FrozenJson) and self._json == other._json

    def __hash__(self) -> int:
        return hash(self._json)


def canonical_value(value: Any) -> Any:
    if isinstance(value, FrozenJson):
        return value.to_python()
    if isinstance(value, BaseModel):
        return {key: canonical_value(item) for key, item in value.__dict__.items()}
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Atlas timestamps must be timezone-aware.")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, Mapping):
        return {str(key): canonical_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, frozenset, set)):
        return [canonical_value(item) for item in value]
    if isinstance(value, float) and (not math.isfinite(value)):
        raise ValueError("Atlas canonical JSON rejects non-finite numbers.")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("Atlas contracts accept JSON-safe values only.")


def canonical_json(value: Any) -> str:
    return json.dumps(canonical_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


class AtlasCanonicalModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    def canonical_dict(self) -> dict[str, Any]:
        value = canonical_value(self)
        assert isinstance(value, dict)
        return value

    def canonical_json(self) -> str:
        return canonical_json(self)

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self)

    def deterministic_fingerprint(self) -> str:
        return fingerprint(self)
