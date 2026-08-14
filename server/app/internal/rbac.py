"""Single-tenant role and permission vocabulary."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    INGESTOR = "ingestor"
    VIEWER = "viewer"


_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.VIEWER: frozenset({"traces:read", "runs:read", "alerts:read", "replay:read"}),
    Role.INGESTOR: frozenset(
        {
            "traces:read",
            "traces:write",
            "runs:read",
            "runs:write",
            "alerts:read",
            "replay:read",
        }
    ),
    Role.ADMIN: frozenset(
        {
            "traces:read",
            "traces:write",
            "runs:read",
            "runs:write",
            "runs:delete",
            "alerts:read",
            "alerts:write",
            "replay:read",
            "users:write",
            "audit:read",
        }
    ),
}


def can(role: Role | str, permission: str) -> bool:
    """Return whether a role grants a named permission."""
    try:
        resolved = Role(role)
    except ValueError:
        return False
    return permission in _PERMISSIONS[resolved]
