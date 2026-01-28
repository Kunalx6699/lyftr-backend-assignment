import hmac
import hashlib
import os
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SECRET = os.getenv("WEBHOOK_SECRET", "testsecret")


def sign(body: str) -> str:
    return hmac.new(
        SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()


def test_invalid_signature():
    body = '{"message_id":"bad1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'

    r = requests.post(
        f"{BASE_URL}/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": "123",
        },
        data=body,
    )

    assert r.status_code == 401


def test_valid_and_duplicate_insert():
    body = '{"message_id":"dup1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'

    sig = sign(body)

    # first insert
    r1 = requests.post(
        f"{BASE_URL}/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": sig,
        },
        data=body,
    )

    assert r1.status_code == 200

    # duplicate
    r2 = requests.post(
        f"{BASE_URL}/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": sig,
        },
        data=body,
    )

    assert r2.status_code == 200
