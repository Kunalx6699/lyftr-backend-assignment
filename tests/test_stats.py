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


def test_stats_endpoint():
    bodies = [
        '{"message_id":"s1","from":"+933333333333","to":"+14155550100","ts":"2025-01-15T08:00:00Z","text":"One"}',
        '{"message_id":"s2","from":"+944444444444","to":"+14155550100","ts":"2025-01-15T09:00:00Z","text":"Two"}',
        '{"message_id":"s3","from":"+933333333333","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Three"}',
    ]

    for b in bodies:
        send(b)

    r = requests.get(f"{BASE_URL}/stats")
    stats = r.json()

    assert stats["total_messages"] >= 3
    assert stats["senders_count"] >= 2

    counts = {
        row["from"]: row["count"]
        for row in stats["messages_per_sender"]
    }

    assert counts["+933333333333"] >= 2
