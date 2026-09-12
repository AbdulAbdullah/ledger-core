import hashlib
import json
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Account, IdempotencyRecord, LedgerEntry, LedgerTransaction
from app.schemas import AccountResponse, TransferRequest, TransferResponse


def request_hash(payload: TransferRequest) -> str:
    encoded = json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def account_balance(session: Session, account_id: UUID) -> int:
    entries = session.scalars(select(LedgerEntry).where(LedgerEntry.account_id == account_id)).all()
    return sum((int(entry.amount_minor) if entry.direction == "credit" else -int(entry.amount_minor)) for entry in entries)


def create_account(session: Session, currency: str) -> AccountResponse:
    account = Account(currency=currency)
    session.add(account)
    session.commit()
    session.refresh(account)
    return AccountResponse(id=account.id, currency=account.currency, balance_minor=0, version=account.version)


def transfer(session: Session, key: str, payload: TransferRequest) -> TransferResponse:
    if payload.source_account_id == payload.destination_account_id:
        raise HTTPException(status_code=400, detail="source and destination accounts must differ")

    digest = request_hash(payload)
    record = session.get(IdempotencyRecord, key, with_for_update=True)
    if record:
        if record.request_hash != digest:
            raise HTTPException(status_code=409, detail="idempotency key was used for another request")
        if record.response_body is None:
            raise HTTPException(status_code=409, detail="request with this idempotency key is in progress")
        return TransferResponse.model_validate_json(record.response_body)

    record = IdempotencyRecord(key=key, request_hash=digest)
    session.add(record)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        record = session.get(IdempotencyRecord, key)
        if record is None or record.request_hash != digest:
            raise HTTPException(status_code=409, detail="idempotency key was used for another request")
        if record.response_body is None:
            raise HTTPException(status_code=409, detail="request with this idempotency key is in progress")
        return TransferResponse.model_validate_json(record.response_body)

    account_ids = sorted([payload.source_account_id, payload.destination_account_id], key=str)
    accounts = session.scalars(
        select(Account).where(Account.id.in_(account_ids)).with_for_update()
    ).all()
    accounts_by_id = {account.id: account for account in accounts}
    source = accounts_by_id.get(payload.source_account_id)
    destination = accounts_by_id.get(payload.destination_account_id)
    if source is None or destination is None:
        raise HTTPException(status_code=404, detail="account not found")
    if source.currency != payload.currency or destination.currency != payload.currency:
        raise HTTPException(status_code=400, detail="currency does not match both accounts")

    balance = account_balance(session, source.id)
    if balance < payload.amount_minor:
        raise HTTPException(status_code=409, detail="insufficient funds")

    transaction = LedgerTransaction(reference=payload.reference)
    session.add(transaction)
    session.flush()
    amount = Decimal(payload.amount_minor)
    session.add_all(
        [
            LedgerEntry(transaction_id=transaction.id, account_id=source.id, amount_minor=amount, direction="debit"),
            LedgerEntry(transaction_id=transaction.id, account_id=destination.id, amount_minor=amount, direction="credit"),
        ]
    )
    for account in (source, destination):
        result = session.execute(
            update(Account)
            .where(Account.id == account.id, Account.version == account.version)
            .values(version=Account.version + 1)
        )
        if result.rowcount != 1:
            raise HTTPException(status_code=409, detail="account changed during transfer; retry")
    response = TransferResponse(
        transaction_id=transaction.id,
        status="committed",
        amount_minor=payload.amount_minor,
        currency=payload.currency,
    )
    record.transaction_id = transaction.id
    record.status_code = status.HTTP_201_CREATED
    record.response_body = response.model_dump_json()
    session.commit()
    return response
