# Message schema

Version: 0.2
Status: draft

Messages are human-readable Discord posts with a structured envelope. The
coordination bot should validate the envelope before routing or recording it.

## Required envelope

```yaml
schema_version: 0.1
message_id: UUID created by the sender
correlation_id: UUID shared by related messages
task_id: stable task identifier
kind: task | claim | progress | question | assist_request | delegation | pivot |
  blocker | handoff | review | control | ack
sender: agent-a | agent-b | human-owner | human-collaborator | coordination-bot
target: agent-a | agent-b | humans | coordination-bot | both-agents | all
created_at: ISO-8601 UTC timestamp
status: proposed | claimed | active | blocked | review | accepted | rejected | released
summary: short human-readable message
ack_for: UUID of the sender message being acknowledged (required for `ack`)
```

## Collaboration transitions

The parent task's primary owner remains accountable unless ownership is
explicitly transferred and accepted. A message that changes task structure or
ownership includes:

```yaml
transition:
  action: request_assistance | split_subtask | delegate_subtask |
    transfer_ownership | accept_delegation | reject_delegation | integrate_subtask
  parent_task_id: stable parent task ID
  child_task_id: stable child task ID or none
  from_owner: agent-a | agent-b | human-owner
  proposed_owner: agent-a | agent-b | human-owner | none
  completed_work: []
  remaining_work: []
  scope_delta: []
  dependencies: []
  decision_reason: short explanation
  requires_ack: true | false
  ack_message_id: UUID or none
```

An assistance request or proposed delegation does not change ownership until
the target agent accepts it. A full transfer also requires an explicit accepted
handoff or human control event.

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

## Example mid-task assistance request

```json
{
  "schema_version": "0.2",
  "message_id": "00000000-0000-4000-8000-000000000020",
  "correlation_id": "00000000-0000-4000-8000-000000000010",
  "task_id": "GAME-2026-001",
  "kind": "assist_request",
  "sender": "agent-a",
  "target": "agent-b",
  "created_at": "2026-08-11T18:35:00Z",
  "status": "active",
  "summary": "Please take the preview validation subtask; I will retain the parent task.",
  "repository": "cellular-automata-game",
  "branch": "agent-a/scenario-data-validation",
  "worktree": "agent-a-local",
  "base_commit": "0000000",
  "scope": ["LearningIndieDev/Assets/Scripts/Game/Presentation/**"],
  "changed_files": [],
  "validation": ["Scenario data tests pass"],
  "risks": ["Preview code may overlap with the existing UI work."],
  "next_actions": ["Wait for Agent B acceptance before treating the subtask as active."],
  "context_links": [],
  "claim_expires_at": "2026-08-11T20:00:00Z",
  "human_action_required": false,
  "transition": {
    "action": "split_subtask",
    "parent_task_id": "GAME-2026-001",
    "child_task_id": "GAME-2026-001-B",
    "from_owner": "agent-a",
    "proposed_owner": "agent-b",
    "completed_work": ["Scenario data model is implemented."],
    "remaining_work": ["Add and validate the preview presentation path."],
    "scope_delta": ["Child task owns presentation scope only."],
    "dependencies": ["Parent task's scenario data API"],
    "decision_reason": "The preview path needs a separate focused change.",
    "requires_ack": true,
    "ack_message_id": null
  }
}
```

## Validation rules

- Reject unknown enum values, malformed timestamps, invalid UUIDs, missing task
  IDs, and absolute paths in `scope` or `changed_files`.
- Require a valid transition block for `assist_request`, `delegation`, `pivot`,
  and ownership-changing `handoff` messages.
- Reject duplicate `message_id` values.
- Do not apply a delegation or transfer until the proposed owner acknowledges
  it with `accept_delegation` or a human approves it.
- Do not treat a message as authoritative until the sender identity and
  repository provenance have been checked.
- An `ack` confirms that the target agent accepted delivery of the referenced
  message. It does not by itself mean the task is complete or the requested
  work passed review. For a message addressed to both agents, each agent must
  acknowledge its own delivery.
- Bound message size and field lengths; link to files or logs instead of
  copying large output into Discord.
- Machine-control fields and human-readable summaries must describe the same
  event. If they disagree, stop and request human review.
