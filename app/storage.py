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

async def list_messages(
    db_path: str,
    limit: int,
    offset: int,
    from_filter: str | None,
    since: str | None,
    q: str | None,
):
    async with aiosqlite.connect(db_path) as db:
        base = "FROM messages WHERE 1=1"
        params = []

        if from_filter:
            base += " AND from_msisdn = ?"
            params.append(from_filter)

        if since:
            base += " AND ts >= ?"
            params.append(since)

        if q:
            base += " AND lower(text) LIKE ?"
            params.append(f"%{q.lower()}%")

        # total count
        cur = await db.execute(f"SELECT COUNT(*) {base}", params)
        total = (await cur.fetchone())[0]

        # data query
        query = f"""
            SELECT message_id, from_msisdn, to_msisdn, ts, text
            {base}
            ORDER BY ts ASC, message_id ASC
            LIMIT ? OFFSET ?
        """

        cur = await db.execute(query, params + [limit, offset])
        rows = await cur.fetchall()

        data = [
            {
                "message_id": r[0],
                "from": r[1],
                "to": r[2],
                "ts": r[3],
                "text": r[4],
            }
            for r in rows
        ]

        return data, total

async def get_stats(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        # total messages
        cur = await db.execute("SELECT COUNT(*) FROM messages")
        total_messages = (await cur.fetchone())[0]

        # unique senders
        cur = await db.execute(
            "SELECT COUNT(DISTINCT from_msisdn) FROM messages"
        )
        senders_count = (await cur.fetchone())[0]

        # top senders
        cur = await db.execute(
            """
            SELECT from_msisdn, COUNT(*) as cnt
            FROM messages
            GROUP BY from_msisdn
            ORDER BY cnt DESC
            LIMIT 10
            """
        )
        rows = await cur.fetchall()

        messages_per_sender = [
            {"from": r[0], "count": r[1]} for r in rows
        ]

        # first / last timestamps
        cur = await db.execute("SELECT MIN(ts), MAX(ts) FROM messages")
        first_ts, last_ts = await cur.fetchone()

        return {
            "total_messages": total_messages,
            "senders_count": senders_count,
            "messages_per_sender": messages_per_sender,
            "first_message_ts": first_ts,
            "last_message_ts": last_ts,
        }
