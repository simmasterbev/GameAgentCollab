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


def prompt_for(agent: str, payload: dict[str, object]) -> str:
    return f"""You are {agent}, a coding agent participating in a supervised collaboration system.

Discord has delivered the following structured collaboration message:
```json
{json.dumps(payload, indent=2)}
```

For this runtime integration test, do not edit files, commit changes, send Discord messages, or claim task completion. Inspect only the available context if needed. Return exactly one JSON object and no Markdown or commentary. The object must be a schema_version 0.2 acknowledgement with:
- kind: "ack"
- sender: "{agent}"
- target: "coordination-bot"
- status: "accepted"
- correlation_id and task_id copied from the delivered message
- ack_for copied from the delivered message's message_id
- a short summary saying what was received
- a new UUID message_id and a current UTC created_at timestamp
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--sandbox", choices=("read-only", "workspace-write"), default="read-only")
    parser.add_argument("--codex", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument("--timeout", type=int, default=120)
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
    schema_path = Path(__file__).parent / "schemas" / "codex_ack.schema.json"
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
            prompt_for(agent, payload),
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
