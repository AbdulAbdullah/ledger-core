from uuid import UUID

from app.models import Account, LedgerEntry, LedgerTransaction


def open_account(client, currency="USD"):
    response = client.post("/v1/accounts", json={"currency": currency})
    assert response.status_code == 201
    return response.json()


def fund(client, account_id, amount=1000):
    from app.database import SessionLocal
    from app.models import LedgerEntry, LedgerTransaction

    with SessionLocal() as session:
        transaction = LedgerTransaction(reference="initial-funding")
        session.add(transaction)
        session.flush()
        session.add(
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=UUID(account_id),
                amount_minor=amount,
                direction="credit",
            )
        )
        session.commit()


def transfer_payload(source, destination, amount=250):
    return {
        "source_account_id": source,
        "destination_account_id": destination,
        "amount_minor": amount,
        "currency": "USD",
        "reference": "invoice-42",
    }


def test_transfer_is_idempotent(client, db):
    source = open_account(client)
    destination = open_account(client)
    fund(client, source["id"])
    payload = transfer_payload(source["id"], destination["id"])

    first = client.post("/v1/transactions", json=payload, headers={"Idempotency-Key": "key-1"})
    replay = client.post("/v1/transactions", json=payload, headers={"Idempotency-Key": "key-1"})

    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert db.query(LedgerTransaction).count() == 2
    assert db.query(LedgerEntry).count() == 3
    assert client.get(f"/v1/accounts/{source['id']}").json()["balance_minor"] == 750
    assert client.get(f"/v1/accounts/{destination['id']}").json()["balance_minor"] == 250


def test_idempotency_key_cannot_change_request(client):
    source = open_account(client)
    destination = open_account(client)
    fund(client, source["id"])
    headers = {"Idempotency-Key": "key-2"}

    assert client.post("/v1/transactions", json=transfer_payload(source["id"], destination["id"]), headers=headers).status_code == 201
    changed = client.post("/v1/transactions", json=transfer_payload(source["id"], destination["id"], 251), headers=headers)

    assert changed.status_code == 409
    assert changed.json()["detail"] == "idempotency key was used for another request"


def test_insufficient_funds_does_not_leave_ledger_rows(client, db):
    source = open_account(client)
    destination = open_account(client)
    payload = transfer_payload(source["id"], destination["id"], 1)

    response = client.post("/v1/transactions", json=payload, headers={"Idempotency-Key": "key-3"})

    assert response.status_code == 409
    assert db.query(LedgerTransaction).count() == 0
    assert db.query(LedgerEntry).count() == 0
