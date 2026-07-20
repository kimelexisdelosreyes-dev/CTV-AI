"""Bounded, fair, process-local admission control for Ollama inference."""

from __future__ import annotations

import asyncio
import math
import re
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import Literal
from uuid import uuid4

from app.core.config import settings
from app.services.service_errors import CompanyBrainServiceError


InferencePriority = Literal[
    "interactive_fast",
    "interactive_standard",
    "interactive_reasoning",
    "background",
]
PRIORITY_ORDER: tuple[InferencePriority, ...] = (
    "interactive_fast",
    "interactive_standard",
    "interactive_reasoning",
    "background",
)
PRIORITY_RANK = {priority: rank for rank, priority in enumerate(PRIORITY_ORDER)}


def normalize_model_env_key(model_name: str) -> str:
    """Return the documented environment-key fragment for a model name."""

    return re.sub(r"[^A-Z0-9]+", "_", model_name.upper()).strip("_")


def priority_for_model_role(model_role: str | None) -> InferencePriority:
    """Classify work without another model call or prompt-length heuristic."""

    if model_role == "reasoning":
        return "interactive_reasoning"
    if model_role in {"fast", "knowledge", "operations"}:
        return "interactive_fast"
    return "interactive_standard"


@dataclass(frozen=True)
class InferenceQueueConfig:
    enabled: bool
    global_concurrency: int
    queue_capacity: int
    default_timeout_seconds: float
    queue_wait_timeout_seconds: float
    per_user_active_limit: int
    per_user_queue_limit: int
    shutdown_grace_seconds: float
    aging_seconds: float
    model_limits: dict[str, int]

    @classmethod
    def from_settings(cls) -> "InferenceQueueConfig":
        qwen_limit = max(settings.ctv_one_inference_model_qwen3_8b_concurrency, 1)
        reasoning_limit = max(
            settings.ctv_one_inference_model_deepseek_r1_14b_concurrency,
            1,
        )
        model_limits: dict[str, int] = {"qwen3:8b": qwen_limit}
        for model_name in {
            settings.ctv_one_model_fast,
            settings.ctv_one_model_balanced,
            settings.ctv_one_model_operations,
            settings.ctv_one_model_knowledge,
            settings.ctv_one_model_default,
        }:
            if model_name:
                model_limits.setdefault(model_name, qwen_limit)
        for model_name in {"deepseek-r1:14b", settings.ctv_one_model_reasoning}:
            if model_name:
                model_limits[model_name] = min(
                    model_limits.get(model_name, reasoning_limit),
                    reasoning_limit,
                )
        return cls(
            enabled=settings.ctv_one_inference_queue_enabled,
            global_concurrency=max(settings.ctv_one_inference_global_concurrency, 1),
            queue_capacity=max(settings.ctv_one_inference_global_queue_size, 0),
            default_timeout_seconds=max(
                settings.ctv_one_inference_default_timeout_seconds,
                0.001,
            ),
            queue_wait_timeout_seconds=max(
                settings.ctv_one_inference_queue_wait_timeout_seconds,
                0.001,
            ),
            per_user_active_limit=max(
                settings.ctv_one_inference_per_user_active_limit,
                1,
            ),
            per_user_queue_limit=max(
                settings.ctv_one_inference_per_user_queue_limit,
                0,
            ),
            shutdown_grace_seconds=max(
                settings.ctv_one_inference_shutdown_grace_seconds,
                0.0,
            ),
            aging_seconds=max(settings.ctv_one_inference_priority_aging_seconds, 0.1),
            model_limits=model_limits,
        )

    def model_limit(self, model_name: str) -> int:
        return max(
            min(
                self.model_limits.get(model_name, self.global_concurrency),
                self.global_concurrency,
            ),
            1,
        )


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    user_id: str
    conversation_id: str | None
    model_name: str
    model_role: str
    priority: InferencePriority
    enqueued_at: float
    deadline_at: float
    streaming: bool
    estimated_cost_class: str
    owner_task: asyncio.Task[object] | None = field(compare=False, repr=False)


@dataclass(frozen=True)
class QueueAdmissionResult:
    admitted: bool
    queued: bool
    rejected: bool
    queue_position: int | None
    estimated_wait_seconds: float | None
    rejection_reason: str | None
    priority: InferencePriority
    model_name: str
    wait_duration_ms: float
    queue_depth_at_entry: int


class InferenceQueueError(CompanyBrainServiceError):
    def __init__(
        self,
        reason: str,
        *,
        status_code: int,
        retry_after_seconds: int | None = None,
        result: QueueAdmissionResult | None = None,
    ) -> None:
        details = {
            "queue_rejection_reason": reason,
            "retry_after_seconds": retry_after_seconds,
        }
        super().__init__(
            category=reason,
            status_code=status_code,
            safe_detail=(
                "Inference capacity is temporarily unavailable. Please retry shortly."
                if reason != "request_cancelled"
                else "The inference request was cancelled."
            ),
            diagnostics=details,
        )
        self.retry_after_seconds = retry_after_seconds
        self.result = result


class InferenceLease:
    def __init__(
        self,
        service: "InferenceQueueService | None",
        request: InferenceRequest,
        result: QueueAdmissionResult,
        *,
        active_global: int = 0,
        active_for_model: int = 0,
        user_active_count: int = 0,
    ) -> None:
        self.request_id = request.request_id
        self.model_name = request.model_name
        self.priority = request.priority
        self.acquired_at = monotonic()
        self.result = result
        self.active_global = active_global
        self.active_for_model = active_for_model
        self.user_active_count = user_active_count
        self.cancelled = False
        self._service = service
        self._released = False

    async def release(self, *, cancelled: bool = False) -> float:
        if self._released:
            return 0.0
        self._released = True
        self.cancelled = cancelled
        duration_ms = max((monotonic() - self.acquired_at) * 1000, 0.0)
        if self._service is not None:
            await self._service._release(self, duration_ms, cancelled=cancelled)
        return duration_ms

    async def __aenter__(self) -> "InferenceLease":
        return self

    async def __aexit__(self, exc_type, _exc, _tb) -> None:
        await self.release(cancelled=exc_type is asyncio.CancelledError)


@dataclass
class _PendingRequest:
    request: InferenceRequest
    future: asyncio.Future[InferenceLease]
    queue_depth_at_entry: int


class InferenceAdmission:
    def __init__(
        self,
        service: "InferenceQueueService",
        pending: _PendingRequest,
        initial_result: QueueAdmissionResult,
    ) -> None:
        self.service = service
        self.pending = pending
        self.initial_result = initial_result

    async def wait(
        self,
        *,
        cancellation_check: Callable[[], Awaitable[bool]] | None = None,
        poll_seconds: float = 0.1,
    ) -> InferenceLease:
        try:
            while not self.pending.future.done():
                if cancellation_check is not None and await cancellation_check():
                    await self.cancel()
                    raise asyncio.CancelledError()
                remaining = self.pending.request.deadline_at - monotonic()
                if remaining <= 0:
                    await self.service._expire(self.pending)
                    break
                try:
                    await asyncio.wait_for(
                        asyncio.shield(self.pending.future),
                        timeout=min(poll_seconds, remaining),
                    )
                except TimeoutError:
                    continue
            return await asyncio.shield(self.pending.future)
        except asyncio.CancelledError:
            await asyncio.shield(self.cancel())
            raise

    async def cancel(self) -> None:
        await self.service._cancel(self.pending)


class InferenceQueueService:
    """Fair in-memory scheduler scoped to one API process."""

    def __init__(self, config: InferenceQueueConfig | None = None) -> None:
        self.config = config or InferenceQueueConfig.from_settings()
        self._lock = asyncio.Lock()
        self._pending: list[_PendingRequest] = []
        self._active: dict[str, InferenceRequest] = {}
        self._active_by_model: Counter[str] = Counter()
        self._active_by_user: Counter[str] = Counter()
        self._active_by_priority: Counter[str] = Counter()
        self._queued_by_user: Counter[str] = Counter()
        self._last_user_by_rank: dict[int, str] = {}
        self._global_semaphore = asyncio.Semaphore(self.config.global_concurrency)
        self._model_semaphores: dict[str, asyncio.Semaphore] = {}
        self._accepting = True
        self._draining = False
        self._active_zero = asyncio.Event()
        self._active_zero.set()
        self._wait_total_ms = 0.0
        self._admitted_count = 0
        self._completed_count = 0
        self._lease_total_ms = 0.0
        self._cache_bypass_count = 0
        self._recent_rejections: Counter[str] = Counter()
        self._recent_timeouts = 0
        self._recent_cancellations = 0

    async def start(self) -> None:
        async with self._lock:
            self.config = InferenceQueueConfig.from_settings()
            if self._active or self._pending:
                raise RuntimeError("Cannot reconfigure a busy inference queue.")
            self._global_semaphore = asyncio.Semaphore(self.config.global_concurrency)
            self._model_semaphores = {}
            self._accepting = True
            self._draining = False

    def record_cache_bypass(self, instrumentation=None) -> None:
        self._cache_bypass_count += 1
        if instrumentation is not None:
            instrumentation.record_metric("inference_queue_enabled", self.config.enabled)
            instrumentation.record_metric("inference_queue_bypassed", True)
            instrumentation.record_metric("inference_queue_admitted", False)

    async def submit(
        self,
        *,
        user_id: str,
        model_name: str,
        model_role: str,
        priority: InferencePriority | None = None,
        request_id: str | None = None,
        conversation_id: str | None = None,
        streaming: bool = False,
        estimated_cost_class: str | None = None,
        timeout_seconds: float | None = None,
    ) -> InferenceAdmission:
        now = monotonic()
        selected_priority = priority or priority_for_model_role(model_role)
        request = InferenceRequest(
            request_id=request_id or str(uuid4()),
            user_id=user_id,
            conversation_id=conversation_id,
            model_name=model_name,
            model_role=model_role,
            priority=selected_priority,
            enqueued_at=now,
            deadline_at=now
            + (timeout_seconds or self.config.queue_wait_timeout_seconds),
            streaming=streaming,
            estimated_cost_class=estimated_cost_class or model_role,
            owner_task=asyncio.current_task(),
        )
        future: asyncio.Future[InferenceLease] = asyncio.get_running_loop().create_future()
        pending = _PendingRequest(request=request, future=future, queue_depth_at_entry=0)

        async with self._lock:
            if not self._accepting:
                return self._rejected_admission(pending, "service_shutting_down", 503)
            if not self.config.enabled:
                result = self._result(request, admitted=True, queue_depth=0)
                future.set_result(InferenceLease(None, request, result))
                return InferenceAdmission(self, pending, result)

            can_start_now = not self._pending and self._eligible(request)
            queued_for_user = self._queued_by_user[user_id]
            if queued_for_user >= self.config.per_user_queue_limit and not can_start_now:
                return self._rejected_admission(pending, "per_user_queue_limit", 429)
            if len(self._pending) >= self.config.queue_capacity and not can_start_now:
                return self._rejected_admission(pending, "queue_full", 429)

            pending.queue_depth_at_entry = len(self._pending)
            self._pending.append(pending)
            self._queued_by_user[user_id] += 1
            await self._dispatch_locked()
            queued = not future.done()
            result = self._result(
                request,
                admitted=not queued,
                queued=queued,
                queue_position=self._queue_position(pending) if queued else None,
                queue_depth=pending.queue_depth_at_entry,
            )
            return InferenceAdmission(self, pending, result)

    def record_result(self, instrumentation, result: QueueAdmissionResult) -> None:
        if instrumentation is None:
            return
        instrumentation.record_metric("inference_queue_enabled", self.config.enabled)
        instrumentation.record_metric("inference_queue_admitted", result.admitted)
        instrumentation.record_metric("inference_queue_bypassed", not self.config.enabled)
        instrumentation.record_metric("inference_queue_rejected", result.rejected)
        instrumentation.record_metric(
            "inference_queue_rejection_reason", result.rejection_reason
        )
        instrumentation.record_metric("inference_queue_priority", result.priority)
        instrumentation.record_metric("inference_queue_position", result.queue_position)
        instrumentation.record_metric("inference_queue_wait_ms", result.wait_duration_ms)
        instrumentation.record_metric(
            "inference_queue_depth_at_entry", result.queue_depth_at_entry
        )
        if result.rejection_reason == "queue_wait_timeout":
            instrumentation.record_metric("inference_timed_out", True)
        if result.rejection_reason == "request_cancelled":
            instrumentation.record_metric("inference_cancelled", True)

    def record_lease(self, instrumentation, lease: InferenceLease) -> None:
        self.record_result(instrumentation, lease.result)
        if instrumentation is None:
            return
        instrumentation.record_metric("inference_active_global", lease.active_global)
        instrumentation.record_metric(
            "inference_active_for_model", lease.active_for_model
        )
        instrumentation.record_metric(
            "inference_model_limit", self.config.model_limit(lease.model_name)
        )
        instrumentation.record_metric(
            "inference_user_active_count", lease.user_active_count
        )

    async def _dispatch_locked(self) -> None:
        self._purge_expired_locked()
        while len(self._active) < self.config.global_concurrency:
            eligible = [item for item in self._pending if self._eligible(item.request)]
            if not eligible:
                break
            pending = self._select_fair(eligible)
            request = pending.request
            self._pending.remove(pending)
            self._queued_by_user[request.user_id] -= 1
            await self._global_semaphore.acquire()
            model_semaphore = self._model_semaphores.setdefault(
                request.model_name,
                asyncio.Semaphore(self.config.model_limit(request.model_name)),
            )
            await model_semaphore.acquire()
            self._active[request.request_id] = request
            self._active_by_model[request.model_name] += 1
            self._active_by_user[request.user_id] += 1
            self._active_by_priority[request.priority] += 1
            self._active_zero.clear()
            waited_ms = max((monotonic() - request.enqueued_at) * 1000, 0.0)
            self._wait_total_ms += waited_ms
            self._admitted_count += 1
            result = self._result(
                request,
                admitted=True,
                queued=waited_ms >= 1.0,
                wait_ms=waited_ms,
                queue_depth=pending.queue_depth_at_entry,
            )
            lease = InferenceLease(
                self,
                request,
                result,
                active_global=len(self._active),
                active_for_model=self._active_by_model[request.model_name],
                user_active_count=self._active_by_user[request.user_id],
            )
            if not pending.future.done():
                pending.future.set_result(lease)

    def _eligible(self, request: InferenceRequest) -> bool:
        return (
            len(self._active) < self.config.global_concurrency
            and self._active_by_model[request.model_name]
            < self.config.model_limit(request.model_name)
            and self._active_by_user[request.user_id]
            < self.config.per_user_active_limit
        )

    def _effective_rank(self, request: InferenceRequest) -> int:
        waited = max(monotonic() - request.enqueued_at, 0.0)
        aged_levels = int(waited / self.config.aging_seconds)
        return max(PRIORITY_RANK[request.priority] - aged_levels, 0)

    def _select_fair(self, eligible: list[_PendingRequest]) -> _PendingRequest:
        best_rank = min(self._effective_rank(item.request) for item in eligible)
        ranked = [
            item for item in eligible if self._effective_rank(item.request) == best_rank
        ]
        ranked.sort(key=lambda item: item.request.enqueued_at)
        users = list(dict.fromkeys(item.request.user_id for item in ranked))
        last_user = self._last_user_by_rank.get(best_rank)
        if last_user in users and len(users) > 1:
            start = (users.index(last_user) + 1) % len(users)
            users = users[start:] + users[:start]
        selected_user = users[0]
        self._last_user_by_rank[best_rank] = selected_user
        return next(item for item in ranked if item.request.user_id == selected_user)

    def _queue_position(self, target: _PendingRequest) -> int:
        ordered = sorted(
            self._pending,
            key=lambda item: (
                self._effective_rank(item.request),
                item.request.enqueued_at,
            ),
        )
        return ordered.index(target) + 1

    def _result(
        self,
        request: InferenceRequest,
        *,
        admitted: bool = False,
        queued: bool = False,
        rejected: bool = False,
        queue_position: int | None = None,
        rejection_reason: str | None = None,
        wait_ms: float = 0.0,
        queue_depth: int = 0,
    ) -> QueueAdmissionResult:
        return QueueAdmissionResult(
            admitted=admitted,
            queued=queued,
            rejected=rejected,
            queue_position=queue_position,
            estimated_wait_seconds=(
                self._estimated_wait_seconds(queue_position)
                if queue_position is not None
                else None
            ),
            rejection_reason=rejection_reason,
            priority=request.priority,
            model_name=request.model_name,
            wait_duration_ms=round(wait_ms, 3),
            queue_depth_at_entry=queue_depth,
        )

    def _rejected_admission(
        self,
        pending: _PendingRequest,
        reason: str,
        status_code: int,
    ) -> InferenceAdmission:
        request = pending.request
        self._recent_rejections[reason] += 1
        result = self._result(
            request,
            rejected=True,
            rejection_reason=reason,
            queue_depth=len(self._pending),
        )
        pending.future.set_exception(
            InferenceQueueError(
                reason,
                status_code=status_code,
                retry_after_seconds=self._retry_after_seconds(),
                result=result,
            )
        )
        return InferenceAdmission(self, pending, result)

    def _retry_after_seconds(self) -> int:
        average_seconds = self._estimated_wait_seconds(1)
        return max(1, min(round(average_seconds), 30))

    def _estimated_wait_seconds(self, queue_position: int) -> float:
        average_lease_seconds = (
            self._lease_total_ms / self._completed_count / 1000
            if self._completed_count
            else min(self.config.default_timeout_seconds, 30.0)
        )
        waves = max(math.ceil(queue_position / self.config.global_concurrency), 1)
        return round(
            min(average_lease_seconds * waves, self.config.queue_wait_timeout_seconds),
            3,
        )

    def _purge_expired_locked(self) -> None:
        now = monotonic()
        for pending in list(self._pending):
            if pending.request.deadline_at > now:
                continue
            self._pending.remove(pending)
            self._queued_by_user[pending.request.user_id] -= 1
            self._recent_timeouts += 1
            result = self._result(
                pending.request,
                rejected=True,
                rejection_reason="queue_wait_timeout",
                wait_ms=(now - pending.request.enqueued_at) * 1000,
                queue_depth=pending.queue_depth_at_entry,
            )
            if not pending.future.done():
                pending.future.set_exception(
                    InferenceQueueError(
                        "queue_wait_timeout",
                        status_code=503,
                        retry_after_seconds=self._retry_after_seconds(),
                        result=result,
                    )
                )

    async def _expire(self, pending: _PendingRequest) -> None:
        async with self._lock:
            self._purge_expired_locked()
            await self._dispatch_locked()

    async def _cancel(self, pending: _PendingRequest) -> None:
        lease: InferenceLease | None = None
        async with self._lock:
            if pending in self._pending:
                self._pending.remove(pending)
                self._queued_by_user[pending.request.user_id] -= 1
                self._recent_cancellations += 1
                if not pending.future.done():
                    pending.future.cancel()
                await self._dispatch_locked()
                return
            if pending.future.done() and not pending.future.cancelled():
                try:
                    lease = pending.future.result()
                except InferenceQueueError:
                    return
        if lease is not None:
            await lease.release(cancelled=True)

    async def _release(
        self,
        lease: InferenceLease,
        duration_ms: float,
        *,
        cancelled: bool,
    ) -> None:
        async with self._lock:
            request = self._active.pop(lease.request_id, None)
            if request is None:
                return
            self._active_by_model[request.model_name] -= 1
            self._active_by_user[request.user_id] -= 1
            self._active_by_priority[request.priority] -= 1
            self._global_semaphore.release()
            self._model_semaphores[request.model_name].release()
            self._completed_count += 1
            self._lease_total_ms += duration_ms
            if cancelled:
                self._recent_cancellations += 1
            if not self._active:
                self._active_zero.set()
            await self._dispatch_locked()

    async def shutdown(self, grace_seconds: float | None = None) -> None:
        async with self._lock:
            self._accepting = False
            self._draining = True
            for pending in list(self._pending):
                self._pending.remove(pending)
                self._queued_by_user[pending.request.user_id] -= 1
                self._recent_rejections["service_shutting_down"] += 1
                self._recent_cancellations += 1
                result = self._result(
                    pending.request,
                    rejected=True,
                    rejection_reason="service_shutting_down",
                    queue_depth=pending.queue_depth_at_entry,
                )
                if not pending.future.done():
                    pending.future.set_exception(
                        InferenceQueueError(
                            "service_shutting_down",
                            status_code=503,
                            retry_after_seconds=1,
                            result=result,
                        )
                    )
            active_tasks = {
                request.owner_task
                for request in self._active.values()
                if request.owner_task is not None
            }
        grace = self.config.shutdown_grace_seconds if grace_seconds is None else grace_seconds
        try:
            await asyncio.wait_for(self._active_zero.wait(), timeout=max(grace, 0.0))
        except TimeoutError:
            current_task = asyncio.current_task()
            for task in active_tasks:
                if task is not current_task and not task.done():
                    task.cancel()

    async def status(self) -> dict[str, object]:
        async with self._lock:
            self._purge_expired_locked()
            now = monotonic()
            queued_by_priority = Counter(
                item.request.priority for item in self._pending
            )
            oldest = max(
                (now - item.request.enqueued_at for item in self._pending),
                default=0.0,
            )
            model_names = (
                set(self.config.model_limits)
                | set(self._active_by_model)
                | {item.request.model_name for item in self._pending}
            )
            return {
                "queue_enabled": self.config.enabled,
                "accepting_requests": self._accepting,
                "active_global": len(self._active),
                "global_limit": self.config.global_concurrency,
                "queued_total": len(self._pending),
                "queue_capacity": self.config.queue_capacity,
                "active_by_model": dict(self._active_by_model),
                "limits_by_model": {
                    model_name: self.config.model_limit(model_name)
                    for model_name in sorted(model_names)
                },
                "queued_by_priority": {
                    priority: queued_by_priority[priority]
                    for priority in PRIORITY_ORDER
                },
                "active_by_priority": {
                    priority: self._active_by_priority[priority]
                    for priority in PRIORITY_ORDER
                },
                "oldest_wait_seconds": round(oldest, 3),
                "average_wait_ms": round(
                    self._wait_total_ms / self._admitted_count
                    if self._admitted_count
                    else 0.0,
                    3,
                ),
                "recent_rejections": dict(self._recent_rejections),
                "recent_timeouts": self._recent_timeouts,
                "recent_cancellations": self._recent_cancellations,
                "completed_count": self._completed_count,
                "cache_bypass_count": self._cache_bypass_count,
            }


inference_queue = InferenceQueueService()
