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


def send(body: str):
    sig = sign(body)

    return requests.post(
        f"{BASE_URL}/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": sig,
        },
        data=body,
    )


def test_messages_pagination_and_filters():
    bodies = [
        '{"message_id":"m10","from":"+911111111111","to":"+14155550100","ts":"2025-01-15T09:00:00Z","text":"Earlier"}',
        '{"message_id":"m11","from":"+922222222222","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}',
        '{"message_id":"m12","from":"+911111111111","to":"+14155550100","ts":"2025-01-15T11:00:00Z","text":"Later"}',
    ]

    for b in bodies:
        send(b)

    # basic list
    r = requests.get(f"{BASE_URL}/messages")
    data = r.json()

    assert data["total"] >= 3

    # limit/offset
    r2 = requests.get(f"{BASE_URL}/messages?limit=2&offset=0")
    assert len(r2.json()["data"]) == 2

    # from filter (raw + sign)
    r3 = requests.get(f"{BASE_URL}/messages?from=+911111111111")
    assert r3.json()["total"] >= 2

    # since filter
    r4 = requests.get(
        f"{BASE_URL}/messages?since=2025-01-15T10:00:00Z"
    )

    for row in r4.json()["data"]:
        assert row["ts"] >= "2025-01-15T10:00:00Z"

    # text search
    r5 = requests.get(f"{BASE_URL}/messages?q=Hello")
    assert any("Hello" in (m["text"] or "") for m in r5.json()["data"])
