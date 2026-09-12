from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.ledger import transfer
from app.database import get_db
from app.schemas import TransferRequest, TransferResponse

router = APIRouter(prefix="/v1/transactions", tags=["transactions"])


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: TransferRequest,
    idempotency_key: str = Header(min_length=1, max_length=255),
    session: Session = Depends(get_db),
) -> TransferResponse:
    return transfer(session, idempotency_key, payload)
