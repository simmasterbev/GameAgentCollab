# Message schema

Version: 0.1
Status: draft

Messages are human-readable Discord posts with a structured envelope. The
coordination bot should validate the envelope before routing or recording it.

## Required envelope

```yaml
schema_version: 0.1
message_id: UUID created by the sender
correlation_id: UUID shared by related messages
task_id: stable task identifier
kind: task | claim | progress | question | blocker | handoff | review | control
sender: agent-a | agent-b | human-owner | human-collaborator | coordination-bot
target: agent-a | agent-b | humans | both-agents | all
created_at: ISO-8601 UTC timestamp
status: proposed | claimed | active | blocked | review | accepted | rejected | released
summary: short human-readable message
```

## Implementation fields

Implementation messages also include:

```yaml
repository: stable repository name or approved URL
branch: branch name or none
worktree: descriptive worktree identity or none
base_commit: commit from which the task started
scope:
  - repository-relative path or declared path pattern
changed_files: []
validation: []
risks: []
next_actions: []
context_links: []
claim_expires_at: ISO-8601 UTC timestamp or none
human_action_required: true | false
```

## Example claim

```json
{
  "schema_version": "0.1",
  "message_id": "00000000-0000-4000-8000-000000000001",
  "correlation_id": "00000000-0000-4000-8000-000000000010",
  "task_id": "GAME-2026-001",
  "kind": "claim",
  "sender": "agent-a",
  "target": "humans",
  "created_at": "2026-08-11T18:00:00Z",
  "status": "claimed",
  "summary": "Claiming the scenario-data validation task.",
  "repository": "cellular-automata-game",
  "branch": "agent-a/scenario-data-validation",
  "worktree": "agent-a-local",
  "base_commit": "0000000",
  "scope": ["LearningIndieDev/Assets/Scripts/Game/Simulation/**"],
  "changed_files": [],
  "validation": [],
  "risks": ["May overlap with the simulation-preview work."],
  "next_actions": ["Run the ownership preflight before editing."],
  "context_links": [],
  "claim_expires_at": "2026-08-11T20:00:00Z",
  "human_action_required": false
}
```

## Validation rules

- Reject unknown enum values, malformed timestamps, invalid UUIDs, missing task
  IDs, and absolute paths in `scope` or `changed_files`.
- Reject duplicate `message_id` values.
- Do not treat a message as authoritative until the sender identity and
  repository provenance have been checked.
- Bound message size and field lengths; link to files or logs instead of
  copying large output into Discord.
- Machine-control fields and human-readable summaries must describe the same
  event. If they disagree, stop and request human review.
