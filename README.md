# Game Agent Collaboration

Siloed collaboration control-plane design for two coding agents working on the
cellular-automata game with human observation and intervention through Discord.

This repository is intentionally separate from the Unity game repository at
`F:\CellularAutomataGameDev`. It contains no Unity code, assets, package files,
Discord credentials, bot tokens, or private conversation transcripts.

## Current status

Documentation plus a dependency-free HTTPS messaging CLI and an optional local
Codex runtime bridge. No always-on Discord Gateway runtime or repository write
automation has been built yet.

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
must return one validated `ack` envelope as JSON on stdout, with `sender`
matching the selected agent and `ack_for` matching the incoming payload's
`message_id`. Only after the acknowledgement posts successfully does the
selected agent's delivery become `acked`; messages addressed to both agents
track each agent's acknowledgement independently. Handler failures remain
retryable:

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
payload and collaboration rules, and requires a schema-constrained JSON ack:

```powershell
python .\collabctl.py dispatch --agent-id agent-b `
  --channel-id <thread-channel-id> `
  --state-file '.\state\GAME-TEST-001.json' `
  --handler python .\codex_runtime.py `
    --workdir F:\GameAgentCollab `
    --sandbox read-only
```

The handler receives `COLLAB_AGENT_ID` from the dispatcher. Use the Unity
checkout as `--workdir` only after a separate branch/worktree and edit policy
are ready. `workspace-write` is supported but intentionally not the default.

## Core boundary

Discord is the visible coordination room. Git branches/worktrees, repository
state, tests, builds, and human review remain authoritative for implementation.
An agent must not modify the Unity checkout merely because it received a Discord
message.
