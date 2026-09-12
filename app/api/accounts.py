from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.ledger import account_balance, create_account
from app.database import get_db
from app.models import Account
from app.schemas import AccountCreate, AccountResponse

router = APIRouter(prefix="/v1/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def open_account(payload: AccountCreate, session: Session = Depends(get_db)) -> AccountResponse:
    return create_account(session, payload.currency)


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: UUID, session: Session = Depends(get_db)) -> AccountResponse:
    account = session.scalar(select(Account).where(Account.id == account_id))
    if account is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="account not found")
    return AccountResponse(
        id=account.id,
        currency=account.currency,
        balance_minor=account_balance(session, account.id),
        version=account.version,
    )
