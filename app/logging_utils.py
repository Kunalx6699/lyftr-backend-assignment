import json
import uuid
from datetime import datetime, timezone
import logging

logger = logging.getLogger("lyftr")
logger.setLevel(logging.INFO)

def log_event(**fields):
    base = {
        "ts" : datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    print(json.dumps(base))