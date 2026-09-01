import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("medical_chat")


class RequestContext:
    def __init__(self, session_id: str = ""):
        self.request_id = str(uuid.uuid4())[:8]
        self.session_id = session_id
        self.start_time = time.time()
        self.tools_used: list[str] = []
        self.timings: dict[str, float] = {}

    @contextmanager
    def time(self, label: str):
        t = time.time()
        yield
        self.timings[label] = round((time.time() - t) * 1000)

    def log_complete(self):
        total_ms = round((time.time() - self.start_time) * 1000)
        entry = {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "tools_used": self.tools_used,
            "total_ms": total_ms,
            **{f"{k}_ms": v for k, v in self.timings.items()},
        }
        logger.info(json.dumps(entry))
