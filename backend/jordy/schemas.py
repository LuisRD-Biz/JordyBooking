from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Name = Annotated[str, Field(min_length=1, max_length=200)]
Code = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CustomerInput(Input):
    name: Name
    contact: Annotated[str, Field(min_length=1, max_length=300)]


class ResourceInput(Input):
    name: Name
    kind: Literal["staff", "equipment"]
    capabilities: Annotated[list[Code], Field(min_length=1, max_length=20)]

    @field_validator("capabilities")
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Capacidades duplicadas")
        return value


class Requirement(Input):
    capability: Code
    quantity: Annotated[int, Field(ge=1, le=50)]


class PackageInput(Input):
    name: Name
    kind: Literal["session", "event"]
    price: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] = "MXN"
    terms: Annotated[str, Field(max_length=4000)] = ""
    duration_minutes: Annotated[int, Field(ge=1, le=10080)]
    buffer_minutes: Annotated[int, Field(ge=0, le=1440)] = 0
    preparation_minutes: Annotated[int, Field(ge=0, le=1440)] = 0
    requirements: Annotated[list[Requirement], Field(min_length=1, max_length=20)]

    @field_validator("requirements")
    @classmethod
    def unique(cls, value):
        if len({r.capability for r in value}) != len(value):
            raise ValueError("Requisitos duplicados")
        if sum(r.quantity for r in value) > 100:
            raise ValueError("Máximo 100 recursos por paquete")
        return value


class AvailabilityInput(Input):
    package_id: int = Field(gt=0)
    starts_at: AwareDatetime


class BookingInput(AvailabilityInput):
    customer_id: int = Field(gt=0)
    location: Annotated[str | None, Field(min_length=1, max_length=500)] = None


class ApprovalInput(Input):
    location: Annotated[str, Field(min_length=1, max_length=500)]


class ContractInput(Input):
    reference: Annotated[str, Field(min_length=1, max_length=300)]
    signed_at: AwareDatetime


class BlockInput(Input):
    resource_id: int = Field(gt=0)
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    reason: Annotated[str, Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def valid_range(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("El final debe ser posterior al inicio")
        return self


class RescheduleInput(ApprovalInput):
    starts_at: AwareDatetime


class BookingOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    package_id: int
    kind: str
    starts_at: datetime
    ends_at: datetime
    location: str | None
    status: str
    snapshot: dict
    approved_at: datetime | None
