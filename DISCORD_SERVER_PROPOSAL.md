# Discord server proposal

Version: 0.1
Status: proposed

This is the smallest useful server shape for two coding agents, Bevin, and
Salty. It is a collaboration and observation surface for the separate Game
Agent Collaboration system; it is not a place to store game secrets or the
source of truth for code.

## Roles

- `Owner` - Bevin; full server and project-control authority.
- `Collaborator` - Salty; can assign, review, pause, and discuss work.
- `Agent_Bev` - first agent identity.
- `Agent_Salty` - second agent identity.
- `Coordination Bot` - routes and records structured task events.
- `Observer` - optional read-only access for future participants.

Do not grant the bot or agents `Administrator`.

## Channels

Create one category named `COLLABORATION` with these channels:

### `#welcome-and-rules`

Pinned reference channel. Humans post the charter, message schema, ownership
rules, and current repository links here. No secrets or private transcripts.

### `#control-room`

Human-visible task assignment and control actions:

- create or reprioritize a task;
- pause, resume, reassign, or cancel work;
- approve a scope overlap or risky action;
- request a status summary.

### `#tasks`

One Discord thread per task. The opening post contains the task ID, objective,
acceptance gates, target agent, and relevant links. Claims, progress, questions,
assist requests, and decisions stay in that task's thread.

### `#handoffs`

Completion and review messages only. Each handoff names the task, branch,
commit, changed files, validation, risks, and next actions.

### `#alerts`

Blockers, overlapping claims, stale leases, failed validation, bot failures, and
human-action-required events. Keep this channel low-volume and actionable.

## Permission model

Set these at the `COLLABORATION` category level, then sync the child channels:

| Permission | @everyone | Owner | Collaborator | Agent_Bev/Agent_Salty | Coordination Bot | Observer |
|---|---:|---:|---:|---:|---:|---:|
| View Channel | deny | allow | allow | allow | allow | allow |
| Read Message History | deny | allow | allow | allow | allow | allow |
| Send Messages | deny | allow | allow | allow | allow | deny |
| Send Messages in Threads | deny | allow | allow | allow | allow | deny |
| Create Public Threads/Posts | deny | allow | allow | allow | allow | deny |
| Create Private Threads | deny | allow | deny | deny | deny | deny |
| Add Reactions | deny | allow | allow | allow | allow | deny |
| Embed Links | deny | allow | allow | allow | allow | deny |
| Attach Files | deny | allow | allow | allow | allow | deny |
| Use Application Commands | deny | allow | allow | allow | allow | deny |
| Manage Threads | deny | allow | allow | deny | only if required | deny |
| Manage Messages | deny | allow | allow | deny | deny initially | deny |
| Manage Channels | deny | no extra grant | deny | deny | deny | deny |
| Manage Permissions | deny | no extra grant | deny | deny | deny | deny |
| Manage Server/Administrator | deny | owner only | deny | deny | deny | deny |
| Mention @everyone/@here/all roles | deny | deny initially | deny | deny | deny | deny |

The server owner already has owner authority. Do not grant `Administrator` to a
bot or agent. If the bot must archive or lock completed task threads, grant it
`Manage Threads` only; do not grant `Manage Messages` or `Manage Channels`.

## Channel-specific overrides

- `#welcome-and-rules`: agents, bot, and observers can read only. Owner and
  Collaborator can post, attach, pin, and maintain reference messages.
- `#control-room`: Owner, Collaborator, and bot can post. Agents can read but
  should request control actions through task threads until command handling is
  implemented.
- `#tasks`: agents can create public posts/threads and reply. Humans can manage
  threads. Use one task post/thread per task.
- `#handoffs`: agents and bot can post; humans can review and manage threads.
- `#alerts`: agents and bot can post actionable blockers; humans can review and
  manage threads. Keep casual discussion elsewhere.

Humans should be able to read every agent conversation. Do not create hidden
agent channels in the first version; transparency is more valuable than
simulating private agent memory.

## Message conventions

Readable text comes first, followed by the structured envelope or embed.

Examples:

```text
TASK GAME-2026-001 - Add scenario preview validation
CLAIM GAME-2026-001 - Agent_Bev owns Simulation/** on Agent_Bev/scenario-preview
ASSIST GAME-2026-001 - Agent_Bev requests Agent_Salty take child GAME-2026-001-B
ACCEPT GAME-2026-001-B - Agent_Salty accepts Presentation/**
BLOCK GAME-2026-001 - Unity compile is blocked by an unrelated dirty file
HANDOFF GAME-2026-001-B - commit abc1234, tests 4/4, ready for integration
APPROVE GAME-2026-001 - Bevin accepts the handoff for merge/review
```

The bot should assign or preserve a stable `message_id`, `task_id`, and
`correlation_id` for every machine-relevant event. Human conversation can remain
natural inside the task thread.

## First supervised exercise

Before connecting real agent runtimes:

1. Create `GAME-TEST-001` in `#tasks`.
2. Have Agent_Bev claim a narrow fake scope.
3. Have Agent_Bev request child task `GAME-TEST-001-B` from Agent_Salty.
4. Have Agent_Salty accept, post progress, and hand off.
5. Have Bevin or Salty approve the handoff.
6. Test a conflicting claim, a rejected delegation, a pause, and an expired
   claim.
7. Record the result in `#handoffs` and the companion repository.

Do not grant repository write automation until this supervised exercise works.

## Deliberate omissions

- No general-purpose bot commands beyond task/control needs.
- No private secret channel; secrets belong in an approved secret store.
- No automatic conflict resolution.
- No automatic agent-to-agent reply loop.
- No Discord-to-Unity direct mutation path.
