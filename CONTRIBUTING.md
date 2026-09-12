# Contributing

Thanks for helping improve Ledger Core.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest -q
```

For PostgreSQL-backed development:

```bash
docker compose up -d postgres
DATABASE_URL=postgresql+psycopg://ledger:ledger@localhost:5432/ledger .venv/bin/alembic upgrade head
```

## Pull requests

- Keep ledger writes append-only.
- Add or update tests for behavior changes.
- Add a new Alembic revision for schema changes; do not edit an applied revision.
- Run the test suite before opening a pull request.
- Explain concurrency or transaction-isolation changes clearly.
