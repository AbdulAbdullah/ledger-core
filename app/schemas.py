from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AccountCreate(BaseModel):
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class AccountResponse(BaseModel):
    id: UUID
    currency: str
    balance_minor: int
    version: int


class TransferRequest(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    reference: str = Field(min_length=1, max_length=128)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class TransferResponse(BaseModel):
    transaction_id: UUID
    status: str
    amount_minor: int
    currency: str
