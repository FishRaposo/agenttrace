"""Budget model for cost threshold monitoring."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Float, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Budget(Base):
    """SQLAlchemy model for storing budget definitions.

    Attributes:
        id: Unique budget identifier.
        name: Human-readable budget name.
        scope: Scope of the budget (global, provider, model, feature, workflow).
        scope_value: Value for scoped budgets (e.g., provider name, model name).
        limit_usd: Maximum allowed cost in USD.
        period: Time period (daily, weekly, monthly).
        alert_threshold_pct: Percentage of limit at which to trigger alerts.
        created_at: When the budget was created.
    """

    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False, default="global")
    scope_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    limit_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    period: Mapped[str] = mapped_column(String(50), nullable=False, default="monthly")
    alert_threshold_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class BudgetCreate(BaseModel):
    """Pydantic schema for creating a budget."""

    name: str = Field(..., description="Budget name")
    scope: str = Field("global", description="Budget scope")
    scope_value: Optional[str] = Field(None, description="Scope value")
    limit_usd: float = Field(..., description="Budget limit in USD")
    period: str = Field("monthly", description="Budget period")
    alert_threshold_pct: int = Field(80, description="Alert threshold percentage")


class BudgetResponse(BaseModel):
    """Pydantic schema for budget API responses."""

    id: str
    name: str
    scope: str
    scope_value: Optional[str] = None
    limit_usd: float
    period: str
    alert_threshold_pct: int
    created_at: datetime


class BudgetStatusResponse(BaseModel):
    """Pydantic schema for budget status check."""

    budget_id: str
    name: str
    limit_usd: float
    current_cost: float
    remaining: float
    percent_used: float
    alert_triggered: bool
    breached: bool
    projected_monthly: Optional[float] = None
