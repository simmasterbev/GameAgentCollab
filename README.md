# Game Agent Collaboration

Siloed collaboration control-plane design for two coding agents working on the
cellular-automata game with human observation and intervention through Discord.

This repository is intentionally separate from the Unity game repository at
`F:\CellularAutomataGameDev`. It contains no Unity code, assets, package files,
Discord credentials, bot tokens, or private conversation transcripts.

## Current status

Documentation plus a dependency-free HTTPS messaging CLI, a local Codex runtime
bridge, and an optional polling worker. The worker can keep a local agent awake
by polling Discord and dispatching addressed messages; it is not a Discord
Gateway service and repository writes remain explicitly controlled.

## Read in order

1. `COLLABORATION_CHARTER.md`
2. `MESSAGE_SCHEMA.md`
3. `TASK_LIFECYCLE.md`
4. `OWNERSHIP_RULES.md`
5. `ACCEPTANCE_GATES.md`

## Local messaging check

```powershell
python .\collabctl.py self-test
python .\collabctl.py test-sequence
```

The second command validates and prints the supervised `GAME-TEST-001` message
sequence without contacting Discord. For a live send, set
`DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID`, then use:

```powershell
python .\collabctl.py test-sequence --live
```

If `#tasks` is a Discord Forum channel, use its channel ID and let the CLI
create the task post/thread:

```powershell
python .\collabctl.py test-sequence --live --channel-id <tasks-channel-id> --create-thread
```

Use `--task-id` to create a fresh supervised thread for a new acceptance run:

```powershell
python .\collabctl.py test-sequence --live `
  --channel-id <tasks-channel-id> `
  --create-thread `
  --task-id CROSS-MACHINE-001
```

For a clean conversation test with only one initial task, create a single
Forum post instead of the full demo sequence:

```powershell
python .\collabctl.py create-task --live `
  --channel-id <tasks-channel-id> `
  --create-thread `
  --task-id CROSS-MACHINE-001 `
  --summary "Desktop Agent A and BevBot001 Agent B should confirm a Discord conversation."
```

The live mode currently posts messages to the configured channel, and the
connector can create the first Forum task post when requested. The `poll`
command reads structured Discord messages, rejects malformed envelopes, removes
duplicates by Discord message ID, and persists a per-channel cursor in the
ignored `.collabctl-state.json` file:

```powershell
python .\collabctl.py poll --channel-id <channel-id>
```

Use `--dry-run` to inspect the poll request without contacting Discord. Polling
alone is a receive-and-record boundary; `dispatch` is the explicit step that
hands a queued message to an agent runtime.

## Agent dispatch and acknowledgements

The next boundary is a small subprocess adapter. `dispatch` polls, queues, and
delivers pending messages addressed to one agent. Without a handler it prints
the pending JSON job for an external runtime:

```powershell
python .\collabctl.py dispatch --agent-id agent-b `
  --channel-id <thread-channel-id> `
  --state-file '.\state\GAME-TEST-001.json'
```

With `--handler`, the adapter sends one payload as JSON on stdin. The handler
may return a raw validated `ack` for compatibility, or a response object with
an `ack` plus reply-linked outbound messages. Each outbound message must use
`reply_to` to reference the delivered payload. Outbound messages post first and
the acknowledgement posts last; only then does the selected agent's delivery
become `acked`. Messages addressed to both agents track each acknowledgement
independently. Handler failures remain retryable.

```powershell
python .\collabctl.py dispatch --agent-id agent-b `
  --channel-id <thread-channel-id> `
  --state-file '.\state\GAME-TEST-001.json' `
  --handler python .\examples\ack_agent.py
```

An agent can acknowledge a queued message directly with its Discord message
ID:

```powershell
python .\collabctl.py ack <discord-message-id> `
  --agent-id agent-b `
  --channel-id <thread-channel-id> `
  --state-file '.\state\GAME-TEST-001.json'
```

This is a delivery acknowledgement, not task completion or review approval.
The repository now includes a real local Codex handler. It invokes the
authenticated `codex exec` CLI in read-only mode, supplies the delivered
payload and collaboration rules, and requires a schema-constrained response:

```powershell
python .\collabctl.py dispatch --agent-id agent-b `
  --channel-id <thread-channel-id> `
  --state-file '.\state\GAME-TEST-001.json' `
  --handler python .\codex_runtime.py `
    --workdir F:\GameAgentCollab `
    --sandbox read-only `
    --reply-target agent-a
```

The handler receives `COLLAB_AGENT_ID` from the dispatcher. Use the Unity
checkout as `--workdir` only after a separate branch/worktree and edit policy
are ready. `workspace-write` is supported but intentionally not the default.

## Always-on agent worker

Run the worker on the machine hosting the agent. It polls the thread every five
seconds, wakes the local handler for each addressed message, posts the handler's
reply and acknowledgement, and keeps retryable failures in the state file:

```powershell
python .\collabctl.py worker `
  --agent-id agent-b `
  --channel-id <thread-channel-id> `
  --state-file '.\state\CROSS-MACHINE-B.json' `
  --handler python .\codex_runtime.py `
    --workdir C:\Users\bevadmin\GameAgentCollab `
    --sandbox read-only `
    --reply-target agent-a
```

Use `--once` for a single poll/dispatch cycle. Stop the continuous worker with
Ctrl+C. This is polling-based rather than Gateway-based, so wake-up latency is
the configured interval and the process must remain running.

## Core boundary

Discord is the visible coordination room. Git branches/worktrees, repository
state, tests, builds, and human review remain authoritative for implementation.
An agent must not modify the Unity checkout merely because it received a Discord
message.
