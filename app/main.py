from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.accounts import router as accounts_router
from app.api.transactions import router as transactions_router
from app.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Idempotent Transaction Ledger", version="1.0.0", lifespan=lifespan)
app.include_router(accounts_router)
app.include_router(transactions_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
