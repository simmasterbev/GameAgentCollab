#!/usr/bin/env python3
"""Small, dependency-free Discord transport for the collaboration test."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

API = "https://discord.com/api/v10"
MESSAGE_LIMIT = 2000
KINDS = {
    "task",
    "claim",
    "progress",
    "question",
    "assist_request",
    "delegation",
    "pivot",
    "blocker",
    "handoff",
    "review",
    "control",
    "ack",
}
SENDERS = {"agent-a", "agent-b", "human-owner", "human-collaborator", "coordination-bot"}
TARGETS = {"agent-a", "agent-b", "humans", "coordination-bot", "both-agents", "all"}
STATUSES = {"proposed", "claimed", "active", "blocked", "review", "accepted", "rejected", "released"}
TRANSITIONS = {
    "request_assistance",
    "split_subtask",
    "delegate_subtask",
    "transfer_ownership",
    "accept_delegation",
    "reject_delegation",
    "integrate_subtask",
}
STATE_VERSION = 1
SEEN_MESSAGE_LIMIT = 512


def fail(message: str) -> None:
    raise ValueError(message)


def relative_paths(value: Any, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        fail(f"{field} must be a list of non-empty strings")
    for item in value:
        posix = PurePosixPath(item)
        windows = PureWindowsPath(item)
        if windows.is_absolute() or posix.is_absolute() or windows.drive or ".." in posix.parts or ".." in windows.parts:
            fail(f"{field} must contain repository-relative paths: {item}")


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "message_id",
        "correlation_id",
        "task_id",
        "kind",
        "sender",
        "target",
        "created_at",
        "status",
        "summary",
    }
    missing = sorted(required - payload.keys())
    if missing:
        fail(f"missing required fields: {', '.join(missing)}")
    if payload["schema_version"] not in {"0.1", "0.2"}:
        fail("unsupported schema_version")
    for field in ("message_id", "correlation_id"):
        try:
            uuid.UUID(str(payload[field]))
        except (ValueError, AttributeError, TypeError):
            fail(f"{field} must be a UUID")
    for field, values in (("kind", KINDS), ("sender", SENDERS), ("target", TARGETS), ("status", STATUSES)):
        if payload[field] not in values:
            fail(f"invalid {field}: {payload[field]}")
    try:
        datetime.fromisoformat(str(payload["created_at"]).replace("Z", "+00:00"))
    except ValueError:
        fail("created_at must be an ISO-8601 timestamp")
    if not isinstance(payload["task_id"], str) or not payload["task_id"].strip():
        fail("task_id must be a non-empty string")
    if not isinstance(payload["summary"], str) or not payload["summary"].strip():
        fail("summary must be a non-empty string")
    relative_paths(payload.get("scope"), "scope")
    relative_paths(payload.get("changed_files"), "changed_files")
    transition = payload.get("transition")
    if payload["kind"] in {"assist_request", "delegation", "pivot"} and not isinstance(transition, dict):
        fail(f"{payload['kind']} requires a transition object")
    if transition is not None:
        if not isinstance(transition, dict) or transition.get("action") not in TRANSITIONS:
            fail("transition.action is invalid")
        if not transition.get("parent_task_id"):
            fail("transition.parent_task_id is required")
    if payload["kind"] == "ack":
        try:
            uuid.UUID(str(payload.get("ack_for")))
        except (ValueError, AttributeError, TypeError):
            fail("ack messages require ack_for as a UUID")
    if "reply_to" in payload:
        try:
            uuid.UUID(str(payload["reply_to"]))
        except (ValueError, AttributeError, TypeError):
            fail("reply_to must be a UUID")
    return payload


def load_payload(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        fail("payload must be a JSON object")
    return validate(payload)


def token() -> str:
    value = os.environ.get("DISCORD_BOT_TOKEN")
    if not value:
        fail("DISCORD_BOT_TOKEN is not set")
    return value


def channel_id(argument: str | None) -> str:
    value = argument or os.environ.get("DISCORD_CHANNEL_ID")
    if not value or not value.isdigit():
        fail("supply a numeric channel ID with --channel-id or DISCORD_CHANNEL_ID")
    return value


def request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request_object = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token()}",
            "Content-Type": "application/json",
            "User-Agent": "GameAgentCollab/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request_object, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        fail(f"Discord API returned HTTP {error.code}: {detail[:500]}")
    except urllib.error.URLError as error:
        fail(f"Discord request failed: {error.reason}")
    return json.loads(raw) if raw else None


def discord_content(payload: dict[str, Any]) -> str:
    content = "```json\n" + json.dumps(payload, indent=2) + "\n```"
    if len(content) > MESSAGE_LIMIT:
        fail("Discord message exceeds 2000 characters")
    return content


def send_payload(payload: dict[str, Any], target_channel: str, dry_run: bool) -> None:
    if dry_run:
        print(json.dumps({"mode": "send", "dry_run": True, "channel_id": target_channel, "payload": payload}, indent=2))
        return
    print(json.dumps(post_payload(payload, target_channel, False), indent=2))


def create_forum_thread(payload: dict[str, Any], forum_channel: str, dry_run: bool) -> str | None:
    content = discord_content(payload)
    body = {
        "name": payload["task_id"],
        "auto_archive_duration": 1440,
        "message": {"content": content, "allowed_mentions": {"parse": []}},
    }
    if dry_run:
        print(json.dumps({"mode": "create-thread", "dry_run": True, "channel_id": forum_channel, "payload": payload}, indent=2))
        return None
    response = request("POST", f"/channels/{forum_channel}/threads", body)
    print(json.dumps(response, indent=2))
    return str(response["id"])


def read_messages(target_channel: str, after: str | None, dry_run: bool) -> None:
    if after is not None and not after.isdigit():
        fail("--after must be a numeric Discord message ID")
    query = {"limit": "100"}
    if after:
        query["after"] = after
    path = f"/channels/{target_channel}/messages?{urllib.parse.urlencode(query)}"
    if dry_run:
        print(json.dumps({"mode": "read", "dry_run": True, "channel_id": target_channel, "after": after}, indent=2))
        return
    print(json.dumps(request("GET", path), indent=2))


def empty_state() -> dict[str, Any]:
    return {"version": STATE_VERSION, "channels": {}}


def load_state(path: str) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        return empty_state()
    try:
        with state_path.open(encoding="utf-8") as handle:
            state = json.load(handle)
    except json.JSONDecodeError as error:
        fail(f"state file is not valid JSON: {error}")
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION:
        fail(f"state file must use version {STATE_VERSION}")
    if not isinstance(state.get("channels"), dict):
        fail("state file channels must be an object")
    return state


def save_state(path: str, state: dict[str, Any]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{state_path.name}.", suffix=".tmp", dir=state_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2)
            handle.write("\n")
        os.replace(temporary_name, state_path)
    except OSError:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def message_number(message_id: str) -> int:
    if not str(message_id).isdigit():
        fail(f"Discord message ID is not numeric: {message_id}")
    return int(message_id)


def parse_structured_message(message: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    content = message.get("content")
    if not isinstance(content, str):
        return None, None
    match = re.fullmatch(r"\s*```json\s*(.*?)\s*```\s*", content, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None, None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        return None, f"invalid JSON: {error.msg}"
    if not isinstance(payload, dict):
        return None, "payload must be a JSON object"
    try:
        return validate(payload), None
    except ValueError as error:
        return None, str(error)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def inbox_entry(
    discord_message_id: str,
    channel_id_value: str,
    author: dict[str, Any],
    message: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    targets = payload.get("target")
    delivery_agents = {targets} if targets in {"agent-a", "agent-b"} else {"agent-a", "agent-b"}
    return {
        "discord_message_id": discord_message_id,
        "channel_id": channel_id_value,
        "author_id": str(author.get("id", "")),
        "author_bot": bool(author.get("bot", False)),
        "created_at": message.get("timestamp"),
        "payload": payload,
        "deliveries": {
            agent_id: {
                "status": "pending",
                "attempts": 0,
                "last_attempt_at": None,
            "last_error": None,
            "ack_message_id": None,
            "runtime_response": None,
            "outbound_message_ids": [],
            }
            for agent_id in sorted(delivery_agents)
        },
    }


def consume_messages(
    target_channel: str, raw_messages: list[dict[str, Any]], state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    channel_state = state["channels"].setdefault(
        target_channel, {"last_message_id": None, "seen_message_ids": [], "inbox": []}
    )
    if not isinstance(channel_state, dict):
        fail(f"state for channel {target_channel} must be an object")
    channel_state.setdefault("inbox", [])
    if not isinstance(channel_state["inbox"], list):
        fail(f"state inbox for channel {target_channel} must be a list")
    seen = {str(item) for item in channel_state.get("seen_message_ids", [])}
    last_message_id = channel_state.get("last_message_id")
    if last_message_id is not None:
        message_number(str(last_message_id))
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    newest = message_number(str(last_message_id)) if last_message_id is not None else None

    ordered = sorted(raw_messages, key=lambda item: message_number(str(item.get("id", ""))))
    for message in ordered:
        message_id = str(message.get("id", ""))
        current_number = message_number(message_id)
        if message_id in seen or (newest is not None and current_number <= newest):
            continue
        seen.add(message_id)
        newest = max(newest or current_number, current_number)
        payload, error = parse_structured_message(message)
        if error:
            rejected.append({"discord_message_id": message_id, "error": error})
            continue
        if payload is None:
            continue
        author = message.get("author") if isinstance(message.get("author"), dict) else {}
        record = inbox_entry(message_id, str(message.get("channel_id", target_channel)), author, message, payload)
        accepted.append({key: value for key, value in record.items() if key != "deliveries"})
        channel_state["inbox"].append(record)

    seen_ids = sorted(seen, key=message_number)[-SEEN_MESSAGE_LIMIT:]
    channel_state["seen_message_ids"] = seen_ids
    if newest is not None:
        channel_state["last_message_id"] = str(newest)
    result = {
        "channel_id": target_channel,
        "after": str(last_message_id) if last_message_id is not None else None,
        "messages": accepted,
        "rejected": rejected,
    }
    return result, state


def fetch_and_store_messages(target_channel: str, state_path: str, limit: int, dry_run: bool) -> dict[str, Any]:
    if not 1 <= limit <= 100:
        fail("--limit must be between 1 and 100")
    state = load_state(state_path)
    channel_state = state["channels"].get(target_channel, {})
    after = channel_state.get("last_message_id") if isinstance(channel_state, dict) else None
    query = {"limit": str(limit)}
    if after:
        query["after"] = str(after)
    path = f"/channels/{target_channel}/messages?{urllib.parse.urlencode(query)}"
    if dry_run:
        return {"mode": "poll", "dry_run": True, "channel_id": target_channel, "after": after}
    raw_messages = request("GET", path)
    if not isinstance(raw_messages, list) or any(not isinstance(item, dict) for item in raw_messages):
        fail("Discord messages response must be a list of objects")
    result, updated_state = consume_messages(target_channel, raw_messages, state)
    save_state(state_path, updated_state)
    return result


def poll_messages(target_channel: str, state_path: str, limit: int, dry_run: bool) -> None:
    result = fetch_and_store_messages(target_channel, state_path, limit, dry_run)
    print(json.dumps(result, indent=2))


def agent_target(payload: dict[str, Any], agent_id: str) -> bool:
    return payload.get("target") in {agent_id, "both-agents", "all"} and payload.get("sender") != agent_id


def pending_for_agent(channel_state: dict[str, Any], agent_id: str) -> list[dict[str, Any]]:
    inbox = channel_state.get("inbox", [])
    return [
        item for item in inbox
        if isinstance(item, dict)
        and isinstance(item.get("payload"), dict)
        and item["payload"].get("kind") != "ack"
        and isinstance(item.get("deliveries"), dict)
        and isinstance(item["deliveries"].get(agent_id), dict)
        and item["deliveries"][agent_id].get("status") == "pending"
        and agent_target(item["payload"], agent_id)
    ]


def validate_runtime_response(
    response: dict[str, Any], agent_id: str, incoming_payload: dict[str, Any]
) -> dict[str, Any]:
    if "ack" not in response:
        response = {"ack": response, "messages": []}
    if set(response) != {"ack", "messages"}:
        fail("runtime response must contain only ack and messages")
    ack = response["ack"]
    messages = response["messages"]
    if not isinstance(ack, dict):
        fail("runtime response ack must be an object")
    validate(ack)
    if ack.get("sender") != agent_id:
        fail("runtime acknowledgement sender does not match --agent-id")
    if ack.get("kind") != "ack":
        fail("runtime acknowledgement must have kind ack")
    if ack.get("ack_for") != incoming_payload.get("message_id"):
        fail("runtime acknowledgement ack_for does not match the dispatched payload")
    if not isinstance(messages, list) or len(messages) > 3:
        fail("runtime messages must be a list with at most 3 items")
    for message in messages:
        if not isinstance(message, dict):
            fail("runtime outbound message must be an object")
        validate(message)
        if message.get("sender") != agent_id:
            fail("runtime outbound sender does not match --agent-id")
        if message.get("kind") == "ack":
            fail("runtime outbound messages cannot be ack messages")
        if message.get("reply_to") != incoming_payload.get("message_id"):
            fail("runtime outbound reply_to does not match the dispatched payload")
        if message.get("target") == "coordination-bot":
            fail("runtime outbound messages must target an agent or human")
    return {"ack": ack, "messages": messages}


def dispatch_messages(
    target_channel: str,
    agent_id: str,
    state_path: str,
    limit: int,
    handler: list[str] | None,
    timeout: int,
    dry_run: bool,
) -> None:
    if agent_id not in {"agent-a", "agent-b"}:
        fail("--agent-id must be agent-a or agent-b")
    if not 1 <= limit <= 100:
        fail("--limit must be between 1 and 100")
    if timeout < 1:
        fail("--timeout must be positive")
    fetch_result = fetch_and_store_messages(target_channel, state_path, limit=100, dry_run=dry_run)
    state = load_state(state_path)
    channel_state = state["channels"].get(target_channel)
    if not isinstance(channel_state, dict):
        fail(f"no state exists for channel {target_channel}")
    selected = pending_for_agent(channel_state, agent_id)[:limit]
    dispatched: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for item in selected:
        delivery = item["deliveries"][agent_id]
        delivery["attempts"] = int(delivery.get("attempts", 0)) + 1
        delivery["last_attempt_at"] = now_utc()
        delivery["last_error"] = None
        if handler is None or dry_run:
            dispatched.append(item)
            continue
        try:
            runtime_response = delivery.get("runtime_response")
            if runtime_response is None:
                handler_environment = os.environ.copy()
                handler_environment["COLLAB_AGENT_ID"] = agent_id
                completed = subprocess.run(
                    handler,
                    input=json.dumps(item["payload"]) + "\n",
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    env=handler_environment,
                )
                if completed.returncode != 0:
                    fail(f"handler exited with code {completed.returncode}: {completed.stderr.strip()[:300]}")
                response_payload = json.loads(completed.stdout)
                if not isinstance(response_payload, dict):
                    fail("handler output must be a JSON object")
                runtime_response = validate_runtime_response(response_payload, agent_id, item["payload"])
                delivery["runtime_response"] = runtime_response
                save_state(state_path, state)
            outbound_ids = delivery.setdefault("outbound_message_ids", [])
            for index, message in enumerate(runtime_response["messages"]):
                if index < len(outbound_ids):
                    continue
                response = post_payload(message, target_channel, False)
                if not isinstance(response, dict) or not response.get("id"):
                    fail("Discord did not return an outbound response message")
                outbound_ids.append(str(response["id"]))
                save_state(state_path, state)
            if not delivery.get("ack_message_id"):
                response = post_payload(runtime_response["ack"], target_channel, False)
                if not isinstance(response, dict) or not response.get("id"):
                    fail("Discord did not return an acknowledgement message")
                delivery["ack_message_id"] = str(response["id"])
                save_state(state_path, state)
            delivery["status"] = "acked"
            save_state(state_path, state)
            dispatched.append(item)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
            delivery["last_error"] = str(error)
            failures.append({"discord_message_id": item["discord_message_id"], "error": str(error)})
            save_state(state_path, state)
    if not dry_run:
        save_state(state_path, state)
    print(json.dumps({
        "mode": "dispatch",
        "agent_id": agent_id,
        "poll": fetch_result,
        "messages": dispatched,
        "failures": failures,
    }, indent=2))


def post_payload(payload: dict[str, Any], target_channel: str, dry_run: bool) -> dict[str, Any] | None:
    content = discord_content(payload)
    body = {"content": content, "allowed_mentions": {"parse": []}}
    if dry_run:
        return None
    response = request("POST", f"/channels/{target_channel}/messages", body)
    return response if isinstance(response, dict) else None


def build_ack(payload: dict[str, Any], agent_id: str) -> dict[str, Any]:
    if agent_id not in {"agent-a", "agent-b"}:
        fail("agent ID must be agent-a or agent-b")
    ack = {
        "schema_version": "0.2",
        "message_id": str(uuid.uuid4()),
        "correlation_id": payload["correlation_id"],
        "task_id": payload["task_id"],
        "kind": "ack",
        "sender": agent_id,
        "target": "coordination-bot",
        "created_at": now_utc(),
        "status": "accepted",
        "summary": f"{agent_id} acknowledged delivery of {payload['kind']}.",
        "ack_for": payload["message_id"],
    }
    return validate(ack)


def acknowledge_message(
    target_channel: str,
    discord_message_id: str,
    agent_id: str,
    state_path: str,
    dry_run: bool,
) -> None:
    state = load_state(state_path)
    channel_state = state["channels"].get(target_channel)
    if not isinstance(channel_state, dict) or not isinstance(channel_state.get("inbox"), list):
        fail(f"no inbox exists for channel {target_channel}")
    record = next(
        (item for item in channel_state["inbox"]
         if isinstance(item, dict) and item.get("discord_message_id") == discord_message_id),
        None,
    )
    if record is None:
        fail(f"no queued message found for Discord message ID {discord_message_id}")
    deliveries = record.get("deliveries")
    if not isinstance(deliveries, dict) or not isinstance(deliveries.get(agent_id), dict):
        fail(f"message {discord_message_id} is not addressed to {agent_id}")
    delivery = deliveries[agent_id]
    if delivery.get("status") == "acked":
        print(json.dumps({"mode": "ack", "already_acked": True, "record": record}, indent=2))
        return
    payload = record.get("payload")
    if not isinstance(payload, dict):
        fail("queued message payload is invalid")
    ack = build_ack(payload, agent_id)
    if dry_run:
        print(json.dumps({"mode": "ack", "dry_run": True, "channel_id": target_channel, "payload": ack}, indent=2))
        return
    response = post_payload(ack, target_channel, False)
    if not isinstance(response, dict) or not response.get("id"):
        fail("Discord did not return an acknowledgement message")
    delivery["status"] = "acked"
    delivery["ack_message_id"] = str(response["id"])
    delivery["last_error"] = None
    save_state(state_path, state)
    print(json.dumps({"mode": "ack", "message": response, "record": record}, indent=2))


def sample_payload(kind: str, sender: str, target: str, status: str, summary: str, task_id: str) -> dict[str, Any]:
    correlation = str(uuid.uuid4())
    return {
        "schema_version": "0.2",
        "message_id": str(uuid.uuid4()),
        "correlation_id": correlation,
        "task_id": task_id,
        "kind": kind,
        "sender": sender,
        "target": target,
        "created_at": "2026-08-11T00:00:00Z",
        "status": status,
        "summary": summary,
    }


def self_test() -> None:
    valid = sample_payload("progress", "agent-a", "humans", "active", "Working on the test task.", "GAME-TEST-001")
    validate(valid)
    invalid = dict(valid, kind="assist_request")
    try:
        validate(invalid)
    except ValueError:
        pass
    else:
        fail("self-test accepted assist_request without transition")
    with tempfile.TemporaryDirectory() as directory:
        state_path = str(Path(directory) / "state.json")
        state = empty_state()
        message = {
            "id": "100",
            "channel_id": "123",
            "author": {"id": "456", "bot": True},
            "timestamp": "2026-08-11T00:00:00Z",
            "content": discord_content(valid),
        }
        duplicate = dict(message)
        invalid = dict(message, id="101", content="```json\n{not-json}\n```")
        result, state = consume_messages("123", [duplicate, invalid, message], state)
        if len(result["messages"]) != 1 or len(result["rejected"]) != 1:
            fail("self-test did not separate accepted, duplicate, and rejected messages")
        if state["channels"]["123"]["last_message_id"] != "101":
            fail("self-test did not advance the cursor")
        save_state(state_path, state)
        restored = load_state(state_path)
        if restored["channels"]["123"]["last_message_id"] != "101":
            fail("self-test did not persist the cursor")
        if len(state["channels"]["123"]["inbox"]) != 1:
            fail("self-test did not queue the accepted message")
        ack = build_ack(valid, "agent-b")
        if ack["kind"] != "ack" or ack["ack_for"] != valid["message_id"]:
            fail("self-test did not build a matching acknowledgement")
        outbound = sample_payload("question", "agent-b", "agent-a", "active", "Can Agent A confirm the next step?", valid["task_id"])
        outbound["correlation_id"] = valid["correlation_id"]
        outbound["reply_to"] = valid["message_id"]
        runtime_response = validate_runtime_response({"ack": ack, "messages": [outbound]}, "agent-b", valid)
        if runtime_response["messages"][0]["reply_to"] != valid["message_id"]:
            fail("self-test did not validate the outbound reply link")
        handler = Path(__file__).parent / "examples" / "ack_agent.py"
        completed = subprocess.run(
            [sys.executable, str(handler)],
            input=json.dumps(valid) + "\n",
            capture_output=True,
            text=True,
            env={**os.environ, "COLLAB_AGENT_ID": "agent-b"},
            check=False,
        )
        if completed.returncode != 0:
            fail(f"self-test handler failed: {completed.stderr.strip()}")
        handler_ack = json.loads(completed.stdout)
        validate(handler_ack)
        if handler_ack["sender"] != "agent-b" or handler_ack["ack_for"] != valid["message_id"]:
            fail("self-test handler returned the wrong acknowledgement")
        targeted = sample_payload("question", "agent-a", "agent-b", "active", "Can Agent B review this?", "GAME-TEST-002")
        targeted_message = {
            "id": "102",
            "channel_id": "123",
            "author": {"id": "456", "bot": True},
            "timestamp": "2026-08-11T00:00:00Z",
            "content": discord_content(targeted),
        }
        dispatch_state = empty_state()
        consume_messages("123", [targeted_message], dispatch_state)
        pending = pending_for_agent(dispatch_state["channels"]["123"], "agent-b")
        if len(pending) != 1 or pending[0]["payload"]["message_id"] != targeted["message_id"]:
            fail("self-test did not select a targeted pending message")
        broadcast = sample_payload("task", "human-owner", "both-agents", "proposed", "Both agents should see this.", "GAME-TEST-003")
        broadcast_message = dict(targeted_message, id="103", content=discord_content(broadcast))
        consume_messages("123", [broadcast_message], dispatch_state)
        broadcast_record = dispatch_state["channels"]["123"]["inbox"][-1]
        broadcast_record["deliveries"]["agent-b"]["status"] = "acked"
        if len(pending_for_agent(dispatch_state["channels"]["123"], "agent-a")) != 1:
            fail("self-test suppressed Agent A after only Agent B acknowledged")
    print("self-test passed")


def test_sequence(
    dry_run: bool, target_channel: str | None, create_thread: bool, task_id: str
) -> None:
    if not task_id.strip():
        fail("--task-id must not be empty")
    task = task_id
    correlation_id = str(uuid.uuid4())
    messages = [
        sample_payload("task", "human-owner", "both-agents", "proposed", "Run the supervised collaboration test.", task),
        sample_payload("claim", "agent-a", "humans", "claimed", "Agent A claims the fake task.", task),
        sample_payload("assist_request", "agent-a", "agent-b", "active", "Agent A requests a child subtask from Agent B.", task),
        sample_payload("delegation", "agent-b", "humans", "accepted", "Agent B accepts the child subtask.", task),
        sample_payload("handoff", "agent-b", "humans", "review", "Agent B hands off the child subtask.", task),
    ]
    for message in messages:
        message["correlation_id"] = correlation_id
    messages[2]["transition"] = {
        "action": "split_subtask",
        "parent_task_id": task,
        "child_task_id": f"{task}-B",
        "from_owner": "agent-a",
        "proposed_owner": "agent-b",
        "completed_work": ["Fake setup"],
        "remaining_work": ["Fake child task"],
        "scope_delta": ["Test-only scope"],
        "dependencies": [],
        "decision_reason": "Testing mid-task delegation",
        "requires_ack": True,
        "ack_message_id": None,
    }
    messages[3]["transition"] = {
        "action": "accept_delegation",
        "parent_task_id": task,
        "child_task_id": f"{task}-B",
        "from_owner": "agent-a",
        "proposed_owner": "agent-b",
        "completed_work": [],
        "remaining_work": ["Fake child task"],
        "scope_delta": ["Test-only scope"],
        "dependencies": [],
        "decision_reason": "Accepted for supervised test",
        "requires_ack": False,
        "ack_message_id": messages[2]["message_id"],
    }
    for message in messages:
        validate(message)
        print(json.dumps(message, indent=2))
    if dry_run:
        for message in messages:
            print(json.dumps({"mode": "send", "dry_run": True, "payload": message}, indent=2))
        return
    destination = channel_id(target_channel)
    if create_thread:
        destination = create_forum_thread(messages[0], destination, False) or destination
        messages = messages[1:]
    for message in messages:
        send_payload(message, destination, False)


def create_task(
    dry_run: bool,
    target_channel: str | None,
    create_thread: bool,
    task_id: str,
    summary: str,
) -> None:
    if not task_id.strip() or not summary.strip():
        fail("--task-id and --summary must not be empty")
    task = sample_payload("task", "human-owner", "both-agents", "proposed", summary, task_id)
    validate(task)
    if dry_run:
        print(json.dumps(task, indent=2))
        return
    destination = channel_id(target_channel)
    if create_thread:
        create_forum_thread(task, destination, False)
    else:
        send_payload(task, destination, False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("payload")

    send_parser = subparsers.add_parser("send")
    send_parser.add_argument("payload")
    send_parser.add_argument("--channel-id")
    send_parser.add_argument("--dry-run", action="store_true")

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("--channel-id")
    read_parser.add_argument("--after")
    read_parser.add_argument("--dry-run", action="store_true")

    poll_parser = subparsers.add_parser("poll")
    poll_parser.add_argument("--channel-id")
    poll_parser.add_argument("--state-file", default=".collabctl-state.json")
    poll_parser.add_argument("--limit", type=int, default=100)
    poll_parser.add_argument("--dry-run", action="store_true")

    dispatch_parser = subparsers.add_parser("dispatch")
    dispatch_parser.add_argument("--agent-id", required=True)
    dispatch_parser.add_argument("--channel-id")
    dispatch_parser.add_argument("--state-file", default=".collabctl-state.json")
    dispatch_parser.add_argument("--limit", type=int, default=1)
    dispatch_parser.add_argument("--timeout", type=int, default=60)
    dispatch_parser.add_argument("--handler", nargs=argparse.REMAINDER, help="agent command and arguments; place this option last")
    dispatch_parser.add_argument("--dry-run", action="store_true")

    ack_parser = subparsers.add_parser("ack")
    ack_parser.add_argument("discord_message_id")
    ack_parser.add_argument("--agent-id", required=True)
    ack_parser.add_argument("--channel-id")
    ack_parser.add_argument("--state-file", default=".collabctl-state.json")
    ack_parser.add_argument("--dry-run", action="store_true")

    sequence_parser = subparsers.add_parser("test-sequence")
    sequence_parser.add_argument("--live", action="store_true")
    sequence_parser.add_argument("--channel-id")
    sequence_parser.add_argument("--create-thread", action="store_true", help="create the first message as a Forum post")
    sequence_parser.add_argument("--task-id", default="GAME-TEST-001")

    task_parser = subparsers.add_parser("create-task")
    task_parser.add_argument("--live", action="store_true")
    task_parser.add_argument("--channel-id")
    task_parser.add_argument("--create-thread", action="store_true")
    task_parser.add_argument("--task-id", required=True)
    task_parser.add_argument("--summary", required=True)

    subparsers.add_parser("self-test")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate(load_payload(args.payload))
            print("payload valid")
        elif args.command == "send":
            send_payload(load_payload(args.payload), channel_id(args.channel_id), args.dry_run)
        elif args.command == "read":
            read_messages(channel_id(args.channel_id), args.after, args.dry_run)
        elif args.command == "poll":
            poll_messages(channel_id(args.channel_id), args.state_file, args.limit, args.dry_run)
        elif args.command == "dispatch":
            dispatch_messages(
                channel_id(args.channel_id),
                args.agent_id,
                args.state_file,
                args.limit,
                args.handler,
                args.timeout,
                args.dry_run,
            )
        elif args.command == "ack":
            acknowledge_message(
                channel_id(args.channel_id),
                args.discord_message_id,
                args.agent_id,
                args.state_file,
                args.dry_run,
            )
        elif args.command == "test-sequence":
            test_sequence(not args.live, args.channel_id, args.create_thread, args.task_id)
        elif args.command == "create-task":
            create_task(not args.live, args.channel_id, args.create_thread, args.task_id, args.summary)
        else:
            self_test()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
