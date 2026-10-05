from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UserContext:
    uid: int
    company_id: int
    company_ids: tuple[int, ...]
    lang: str
    tz: str
    groups: tuple[int, ...] = ()


@dataclass(frozen=True)
class PermissionContext:
    user_id: int
    company_id: int
    company_ids: tuple[int, ...]
    lang: str
    tz: str
    groups: tuple[int, ...] = ()
    allowed_models: tuple[str, ...] = ()
    allowed_fields: dict[str, tuple[str, ...]] = field(default_factory=dict)
    allowed_relation_paths: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class AuthorizedField:
    model: str
    field_name: str
    field_type: str
    readable: bool
    searchable: bool
    reason: str | None = None


@dataclass(frozen=True)
class PathCheck:
    resource: str
    path: tuple[dict[str, Any], ...]
    authorized: bool
    blocked_at: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class SearchRequest:
    raw_query: str = ""
    parsed_conditions: tuple[dict[str, Any], ...] = ()
    refinement_conditions: tuple[dict[str, Any], ...] = ()
    resource_scope: tuple[str, ...] = ()
    offset: int = 0
    limit: int = 50
    cursor: str | None = None


@dataclass
class ResourceOutcome:
    resource: str
    status: str
    results: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    error: dict[str, Any] | None = None
    latency: float = 0.0


@dataclass
class SearchResponse:
    status: str
    request_id: str
    results: list[dict[str, Any]]
    counts: dict[str, Any]
    errors: list[dict[str, Any]]
    meta: dict[str, Any]
