import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    domain: str | None
    industry: str | None
    employee_count: int | None
    location: str | None
    created_at: datetime


class AccountDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    domain: str | None
    industry: str | None
    employee_count: int | None
    location: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
