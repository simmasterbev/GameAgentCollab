#!/usr/bin/env python3
"""Run one delivered collaboration message through the local Codex CLI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(message: str) -> None:
    print(f"codex-runtime error: {message}", file=sys.stderr)
    raise SystemExit(1)


def agent_id() -> str:
    value = os.environ.get("COLLAB_AGENT_ID")
    if value not in {"agent-a", "agent-b"}:
        fail("COLLAB_AGENT_ID must be agent-a or agent-b")
    return value


def prompt_for(agent: str, payload: dict[str, object], reply_target: str | None) -> str:
    reply_instruction = "Set messages to an empty array."
    if reply_target:
        reply_instruction = f"Include exactly one outbound message in messages addressed to {reply_target}. Set reply_to to the delivered message_id. If the delivered message is a question or assist_request, answer it with a concise progress message; otherwise ask {reply_target} one concise question needed to continue the supervised conversation."
    return f"""You are {agent}, a coding agent participating in a supervised collaboration system.

Discord has delivered the following structured collaboration message:
```json
{json.dumps(payload, indent=2)}
```

For this runtime integration test, do not edit files, commit changes, send Discord messages, or claim task completion. Inspect only the available context if needed. Return exactly one JSON object and no Markdown or commentary. The object must contain an ack object and a messages array. The ack must use sender "{agent}", target "coordination-bot", status "accepted", copy correlation_id and task_id, set ack_for to the delivered message_id, and include a new UUID message_id and current UTC created_at. {reply_instruction} Every outbound message must use sender "{agent}", a valid collaboration kind, a permitted target, a new UUID message_id, the same correlation_id and task_id, reply_to equal to the delivered message_id, and a concise summary.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--sandbox", choices=("read-only", "workspace-write"), default="read-only")
    parser.add_argument("--codex", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--reply-target", choices=("agent-a", "agent-b", "humans", "both-agents", "all"))
    args = parser.parse_args()
    if args.timeout < 1:
        fail("--timeout must be positive")

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        fail(f"input is not valid JSON: {error}")
    if not isinstance(payload, dict):
        fail("input must be a JSON object")

    agent = agent_id()
    if args.reply_target == agent:
        fail("--reply-target cannot be the same as COLLAB_AGENT_ID")
    schema_path = Path(__file__).parent / "schemas" / "codex_response.schema.json"
    if not schema_path.exists():
        fail(f"missing output schema: {schema_path}")
    workdir = Path(args.workdir).resolve()
    if not workdir.is_dir():
        fail(f"workdir does not exist: {workdir}")

    with tempfile.TemporaryDirectory(prefix="game-agent-codex-") as directory:
        output_path = Path(directory) / "codex-final.json"
        command = [
            args.codex,
            "exec",
            "--ephemeral",
            "--sandbox",
            args.sandbox,
            "--cd",
            str(workdir),
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            prompt_for(agent, payload, args.reply_target),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=args.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            fail(str(error))
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            fail(f"Codex exited with code {completed.returncode}: {detail[-800:]}")
        if not output_path.exists():
            fail("Codex completed without an output message")
        try:
            response = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            fail(f"Codex output is not valid JSON: {error}")
        if not isinstance(response, dict):
            fail("Codex output must be a JSON object")
        print(json.dumps(response, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
