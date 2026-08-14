"""Local RBAC and audit-redaction contract tests."""

import pytest
from app.config import settings
from app.internal.rbac import Role, can
from app.services.audit import redact_metadata
from httpx import AsyncClient


def test_role_matrix_keeps_viewers_read_only() -> None:
    assert can(Role.VIEWER, "traces:read") is True
    assert can(Role.VIEWER, "traces:write") is False
    assert can(Role.INGESTOR, "traces:write") is True
    assert can(Role.ADMIN, "audit:read") is True


def test_audit_redaction_removes_nested_secrets() -> None:
    redacted = redact_metadata(
        {
            "password": "hidden",
            "nested": {"api_key": "hidden", "safe": "kept"},
            "safe": "value",
        }
    )

    assert redacted == {"nested": {"safe": "kept"}, "safe": "value"}


@pytest.mark.asyncio
async def test_offline_admin_can_read_audit_without_exposing_password(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"username": "audit-user", "password": "secret-value"},
    )
    assert response.status_code == 201

    audit = await client.get("/api/audit")
    assert audit.status_code == 200
    assert all("secret-value" not in str(event) for event in audit.json())


@pytest.mark.asyncio
async def test_authenticated_viewer_is_read_only_and_invalid_tokens_fail(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered = await client.post(
        "/api/auth/register", json={"username": "viewer", "password": "password"}
    )
    assert registered.status_code == 201

    token_response = await client.post(
        "/api/auth/token",
        data={"username": "viewer", "password": "password"},
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    assert (await client.get("/api/runs", headers=headers)).status_code == 200
    assert (await client.get("/api/audit", headers=headers)).status_code == 403
    assert (
        await client.post(
            "/api/runs",
            headers=headers,
            json={"name": "blocked", "status": "running"},
        )
    ).status_code == 403

    assert (
        await client.get("/api/audit", headers={"Authorization": "Bearer malformed"})
    ).status_code == 401
