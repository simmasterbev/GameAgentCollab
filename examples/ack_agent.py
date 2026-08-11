#!/usr/bin/env python3
"""Example handler for the GameAgentCollab dispatch contract."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone


payload = json.load(sys.stdin)
agent_id = os.environ.get("COLLAB_AGENT_ID", "agent-b")
ack = {
    "schema_version": "0.2",
    "message_id": str(uuid.uuid4()),
    "correlation_id": payload["correlation_id"],
    "task_id": payload["task_id"],
    "kind": "ack",
    "sender": agent_id,
    "target": "coordination-bot",
    "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "status": "accepted",
    "summary": f"{agent_id} acknowledged delivery of {payload['kind']}.",
    "ack_for": payload["message_id"],
}
print(json.dumps(ack))
