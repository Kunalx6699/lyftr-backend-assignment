import aiosqlite

CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    message_ig TEXT PRIMARY KEY,
    from_msisdn TEXT NOT NULL,
    to_msisdn TEXT NOT NULL,
    ts TEXT NOT NULL,
    text TEXT,
    created_at TEXT NOT NULL
);
"""

async def init_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_MESSAGES_TABLE)
        await db.commit()

        