# Idempotent Transaction Ledger

A small FastAPI + SQLAlchemy service for immutable, idempotent account transfers.

## Guarantees

- Every transfer writes one debit and one credit in the same database transaction.
- `Idempotency-Key` replays the original response and cannot be reused with another payload.
- Account rows are locked in deterministic order during a transfer to avoid deadlocks.
- Account versions use compare-and-swap updates as an optimistic concurrency guard.
- PostgreSQL connections use `SERIALIZABLE` isolation by default.
- Balances are derived from ledger entries; there is no mutable balance column.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

The default database is `ledger.db` in the project directory. Set `DATABASE_URL` in `.env` for PostgreSQL, for example:

```text
DATABASE_URL=postgresql+psycopg://ledger:ledger@localhost:5432/ledger
```

## API flow

Create two accounts:

```http
POST /v1/accounts
Content-Type: application/json

{"currency":"USD"}
```

Transfers require a unique idempotency key per logical request:

```http
POST /v1/transactions
Idempotency-Key: invoice-42-attempt-1
Content-Type: application/json

{
  "source_account_id": "<uuid>",
  "destination_account_id": "<uuid>",
  "amount_minor": 250,
  "currency": "USD",
  "reference": "invoice-42"
}
```

`GET /v1/accounts/{account_id}` returns the balance calculated from ledger entries. The test suite seeds initial funds directly because production funding should be a separately authorized operation.

## Tests

```bash
.venv/bin/python -m pytest -q
```
