from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ClaimedJob:
    id: UUID
    job_type: str
    payload: dict
    attempt_number: int
    max_attempts: int
    lease_token: UUID


class JobHandler(Protocol):
    def __call__(self, job: ClaimedJob) -> dict: ...


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: str, handler: JobHandler) -> None:
        normalized = job_type.strip()
        if not normalized or normalized in self._handlers:
            raise ValueError(f"Invalid or duplicate job type: {normalized!r}")
        self._handlers[normalized] = handler

    def get(self, job_type: str) -> JobHandler | None:
        return self._handlers.get(job_type)
