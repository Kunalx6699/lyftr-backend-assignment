import aiosqlite
from datetime import datetime, timezone
from typing import Optional

async def insert_message(db_path: str, msg: dict) -> bool:
    """
    Returns True if inserted, False if duplicate.
    """
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT INTO messages
                (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    msg["message_id"],
                    msg["from"],
                    msg["to"],
                    msg["ts"],
                    msg.get("text"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False
