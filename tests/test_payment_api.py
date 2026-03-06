"""
Tests for the Venmo-style payment_api.py

Each test uses a fresh in-memory SQLite database so tests are fully isolated.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Point to an in-memory SQLite database before importing the app
os.environ["PAYMENT_DATABASE_URL"] = "sqlite://"
os.environ["PAYMENT_SECRET_KEY"] = "test-secret-key-for-unit-tests-only"

from payment_api import app, Base, get_db  # noqa: E402


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database for every test function.

    StaticPool ensures all connections share the same in-memory SQLite instance
    so that tables created by create_all are visible to every session.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal()
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    return TestClient(app)


def _register(client, username="alice", email="alice@example.com", password="password123"):
    return client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })


def _auth_headers(client, username="alice", password="password123"):
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/payment/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "Payment API running"


# ---------------------------------------------------------------------------
# Registration & Login
# ---------------------------------------------------------------------------

def test_register_success(client):
    resp = _register(client)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_username(client):
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409
    assert "Username already taken" in resp.json()["detail"]


def test_register_duplicate_email(client):
    _register(client, username="alice")
    resp = _register(client, username="alice2")  # same email, different username
    assert resp.status_code == 409


def test_register_short_password(client):
    resp = client.post("/auth/register", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "short",
    })
    assert resp.status_code == 422


def test_login_success(client):
    _register(client)
    resp = client.post("/auth/login", data={"username": "alice", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_email_as_username(client):
    _register(client)
    resp = client.post("/auth/login", data={"username": "alice@example.com", "password": "password123"})
    assert resp.status_code == 200


def test_login_wrong_password(client):
    _register(client)
    resp = client.post("/auth/login", data={"username": "alice", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/auth/login", data={"username": "ghost", "password": "whatever"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# User profile & search
# ---------------------------------------------------------------------------

def test_get_me(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"


def test_get_me_unauthenticated(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_search_users(client):
    _register(client, username="alice", email="alice@example.com")
    _register(client, username="alicia", email="alicia@example.com")
    _register(client, username="bob", email="bob@example.com")
    headers = _auth_headers(client)
    resp = client.get("/users/search?q=alic", headers=headers)
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "alicia" in usernames
    # alice should not appear (searching as alice)
    assert "alice" not in usernames


# ---------------------------------------------------------------------------
# Debit card management
# ---------------------------------------------------------------------------

# A valid Visa test card (passes Luhn)
VALID_VISA = "4532015112830366"
VALID_VISA_LAST4 = "0366"


def test_add_card(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.post("/cards", json={
        "card_number": VALID_VISA,
        "expiry_month": 12,
        "expiry_year": 2030,
        "cvv": "123",
        "card_holder_name": "Alice Smith",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["card_last_four"] == VALID_VISA_LAST4
    assert data["card_brand"] == "Visa"
    assert data["is_active"] is True
    # Full PAN must not be present in the response
    assert VALID_VISA not in str(data)


def test_add_card_invalid_luhn(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.post("/cards", json={
        "card_number": "1234567890123456",  # fails Luhn
        "expiry_month": 12,
        "expiry_year": 2030,
        "cvv": "123",
        "card_holder_name": "Alice",
    }, headers=headers)
    assert resp.status_code == 422


def test_add_card_duplicate(client):
    _register(client)
    headers = _auth_headers(client)
    payload = {
        "card_number": VALID_VISA,
        "expiry_month": 12,
        "expiry_year": 2030,
        "cvv": "123",
        "card_holder_name": "Alice",
    }
    client.post("/cards", json=payload, headers=headers)
    resp = client.post("/cards", json=payload, headers=headers)
    assert resp.status_code == 409


def test_list_cards(client):
    _register(client)
    headers = _auth_headers(client)
    client.post("/cards", json={
        "card_number": VALID_VISA,
        "expiry_month": 12,
        "expiry_year": 2030,
        "cvv": "123",
        "card_holder_name": "Alice",
    }, headers=headers)
    resp = client.get("/cards", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_remove_card(client):
    _register(client)
    headers = _auth_headers(client)
    add_resp = client.post("/cards", json={
        "card_number": VALID_VISA,
        "expiry_month": 12,
        "expiry_year": 2030,
        "cvv": "123",
        "card_holder_name": "Alice",
    }, headers=headers)
    card_id = add_resp.json()["id"]
    del_resp = client.delete(f"/cards/{card_id}", headers=headers)
    assert del_resp.status_code == 204
    # Removed card should no longer appear in list
    list_resp = client.get("/cards", headers=headers)
    assert len(list_resp.json()) == 0


# ---------------------------------------------------------------------------
# Balance & funding
# ---------------------------------------------------------------------------

def test_initial_balance_zero(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.get("/balance", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["balance_cents"] == 0


def test_fund_wallet(client):
    _register(client)
    headers = _auth_headers(client)
    card_resp = client.post("/cards", json={
        "card_number": VALID_VISA,
        "expiry_month": 12,
        "expiry_year": 2030,
        "cvv": "123",
        "card_holder_name": "Alice",
    }, headers=headers)
    card_id = card_resp.json()["id"]
    fund_resp = client.post("/balance/fund", json={"card_id": card_id, "amount": 50.00}, headers=headers)
    assert fund_resp.status_code == 200
    assert fund_resp.json()["balance_cents"] == 5000


def test_fund_wallet_invalid_card(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.post("/balance/fund", json={"card_id": "nonexistent", "amount": 10}, headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Send money
# ---------------------------------------------------------------------------

def _setup_two_users(client, fund_alice=True):
    """Register alice and bob; optionally fund alice's wallet."""
    _register(client, username="alice", email="alice@example.com")
    _register(client, username="bob", email="bob@example.com")
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")

    if fund_alice:
        card_resp = client.post("/cards", json={
            "card_number": VALID_VISA,
            "expiry_month": 12,
            "expiry_year": 2030,
            "cvv": "123",
            "card_holder_name": "Alice",
        }, headers=alice_headers)
        card_id = card_resp.json()["id"]
        client.post("/balance/fund", json={"card_id": card_id, "amount": 100.00}, headers=alice_headers)
        return alice_headers, bob_headers, card_id

    return alice_headers, bob_headers, None


def test_send_money_from_balance(client):
    alice_headers, bob_headers, _ = _setup_two_users(client)
    resp = client.post("/transactions/send", json={
        "recipient_username": "bob",
        "amount": 25.00,
        "note": "dinner",
    }, headers=alice_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["sender_username"] == "alice"
    assert data["recipient_username"] == "bob"
    assert data["amount_dollars"] == 25.0
    assert data["txn_status"] == "COMPLETED"

    # Verify balances updated
    alice_bal = client.get("/balance", headers=alice_headers).json()["balance_cents"]
    bob_bal = client.get("/balance", headers=bob_headers).json()["balance_cents"]
    assert alice_bal == 7500
    assert bob_bal == 2500


def test_send_money_from_card(client):
    alice_headers, bob_headers, card_id = _setup_two_users(client, fund_alice=False)
    # Add card for alice without funding wallet
    card_resp = client.post("/cards", json={
        "card_number": VALID_VISA,
        "expiry_month": 12,
        "expiry_year": 2030,
        "cvv": "123",
        "card_holder_name": "Alice",
    }, headers=alice_headers)
    card_id = card_resp.json()["id"]

    resp = client.post("/transactions/send", json={
        "recipient_username": "bob",
        "amount": 15.00,
        "note": "lunch",
        "card_id": card_id,
    }, headers=alice_headers)
    assert resp.status_code == 201
    assert resp.json()["amount_dollars"] == 15.0

    # Bob should receive funds
    bob_bal = client.get("/balance", headers=bob_headers).json()["balance_cents"]
    assert bob_bal == 1500


def test_send_money_insufficient_balance(client):
    alice_headers, _, _ = _setup_two_users(client, fund_alice=False)
    _register(client, username="carol", email="carol@example.com")
    resp = client.post("/transactions/send", json={
        "recipient_username": "carol",
        "amount": 10.00,
    }, headers=alice_headers)
    assert resp.status_code == 400
    assert "Insufficient balance" in resp.json()["detail"]


def test_send_to_self_rejected(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.post("/transactions/send", json={
        "recipient_username": "alice",
        "amount": 5.00,
    }, headers=headers)
    assert resp.status_code == 400


def test_send_to_unknown_user(client):
    alice_headers, _, _ = _setup_two_users(client)
    resp = client.post("/transactions/send", json={
        "recipient_username": "nobody",
        "amount": 5.00,
    }, headers=alice_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Request money
# ---------------------------------------------------------------------------

def test_request_money(client):
    alice_headers, bob_headers, _ = _setup_two_users(client)
    resp = client.post("/transactions/request", json={
        "target_username": "bob",
        "amount": 20.00,
        "note": "you owe me",
    }, headers=alice_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["req_status"] == "PENDING"
    assert data["amount_dollars"] == 20.0


def test_request_money_accept(client):
    alice_headers, bob_headers, _ = _setup_two_users(client)

    # Fund bob too
    bob_card_resp = client.post("/cards", json={
        "card_number": "5425233430109903",  # valid Mastercard test number
        "expiry_month": 6,
        "expiry_year": 2030,
        "cvv": "456",
        "card_holder_name": "Bob",
    }, headers=bob_headers)
    bob_card_id = bob_card_resp.json()["id"]
    client.post("/balance/fund", json={"card_id": bob_card_id, "amount": 50.00}, headers=bob_headers)

    # Alice requests money from bob
    req_resp = client.post("/transactions/request", json={
        "target_username": "bob",
        "amount": 10.00,
        "note": "coffee",
    }, headers=alice_headers)
    req_id = req_resp.json()["id"]

    # Bob accepts
    resp = client.post(f"/transactions/requests/{req_id}/respond", json={"accept": True}, headers=bob_headers)
    assert resp.status_code == 200
    assert resp.json()["req_status"] == "ACCEPTED"

    alice_bal = client.get("/balance", headers=alice_headers).json()["balance_cents"]
    bob_bal = client.get("/balance", headers=bob_headers).json()["balance_cents"]
    assert alice_bal == 11000  # 100.00 + 10.00
    assert bob_bal == 4000    # 50.00 - 10.00


def test_request_money_decline(client):
    alice_headers, bob_headers, _ = _setup_two_users(client)
    req_resp = client.post("/transactions/request", json={
        "target_username": "bob",
        "amount": 10.00,
        "note": "rent",
    }, headers=alice_headers)
    req_id = req_resp.json()["id"]

    resp = client.post(f"/transactions/requests/{req_id}/respond", json={"accept": False}, headers=bob_headers)
    assert resp.status_code == 200
    assert resp.json()["req_status"] == "DECLINED"


# ---------------------------------------------------------------------------
# Transaction history
# ---------------------------------------------------------------------------

def test_transaction_history(client):
    alice_headers, bob_headers, _ = _setup_two_users(client)
    client.post("/transactions/send", json={
        "recipient_username": "bob", "amount": 5.00, "note": "a"
    }, headers=alice_headers)
    client.post("/transactions/send", json={
        "recipient_username": "bob", "amount": 3.00, "note": "b"
    }, headers=alice_headers)

    resp = client.get("/transactions", headers=alice_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_single_transaction(client):
    alice_headers, _, _ = _setup_two_users(client)
    send_resp = client.post("/transactions/send", json={
        "recipient_username": "bob", "amount": 7.00, "note": "test"
    }, headers=alice_headers)
    txn_id = send_resp.json()["id"]

    resp = client.get(f"/transactions/{txn_id}", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == txn_id


def test_get_transaction_not_found(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.get("/transactions/nonexistent-id", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Friends
# ---------------------------------------------------------------------------

def test_add_and_list_friends(client):
    alice_headers, bob_headers, _ = _setup_two_users(client, fund_alice=False)
    resp = client.post("/friends", json={"username": "bob"}, headers=alice_headers)
    assert resp.status_code == 201
    assert resp.json()["username"] == "bob"

    friends = client.get("/friends", headers=alice_headers).json()
    assert len(friends) == 1
    assert friends[0]["username"] == "bob"


def test_add_self_as_friend(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.post("/friends", json={"username": "alice"}, headers=headers)
    assert resp.status_code == 400


def test_add_duplicate_friend(client):
    alice_headers, _, _ = _setup_two_users(client, fund_alice=False)
    client.post("/friends", json={"username": "bob"}, headers=alice_headers)
    resp = client.post("/friends", json={"username": "bob"}, headers=alice_headers)
    assert resp.status_code == 409


def test_remove_friend(client):
    alice_headers, _, _ = _setup_two_users(client, fund_alice=False)
    client.post("/friends", json={"username": "bob"}, headers=alice_headers)
    resp = client.delete("/friends/bob", headers=alice_headers)
    assert resp.status_code == 204
    friends = client.get("/friends", headers=alice_headers).json()
    assert len(friends) == 0


def test_remove_nonexistent_friend(client):
    _register(client)
    headers = _auth_headers(client)
    resp = client.delete("/friends/nobody", headers=headers)
    assert resp.status_code == 404
