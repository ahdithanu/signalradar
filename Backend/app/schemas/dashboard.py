import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardSignal(BaseModel):
    type: str
    description: str
    date: str
    daysAgo: int
    scoreContribution: float
    interpretation: str | None


class DashboardAccount(BaseModel):
    id: uuid.UUID
    name: str
    website: str | None
    industry: str | None
    employeeCount: int | None
    fundingStage: str | None
    status: str
    opportunityScore: float
    opportunityProbability: float
    signals: list[DashboardSignal]
    whyNow: str | None
    recommendedBuyerPersona: list[str]
    suggestedOutreachAngle: str | None
    strategicIntelligence: dict[str, Any] | None
