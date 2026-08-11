# Game Agent Collaboration

Siloed collaboration control-plane design for two coding agents working on the
cellular-automata game with human observation and intervention through Discord.

This repository is intentionally separate from the Unity game repository at
`F:\CellularAutomataGameDev`. It contains no Unity code, assets, package files,
Discord credentials, bot tokens, or private conversation transcripts.

## Current status

Documentation plus a dependency-free HTTPS messaging CLI. No always-on Discord
Gateway runtime or repository automation has been built yet.

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

Use `--dry-run` to inspect the poll request without contacting Discord. The
current poll is a receive-and-record boundary: it does not yet wake agent
runtimes, dispatch tasks, or provide an acknowledgement transaction if a
downstream agent fails after polling. Those are later gates.

## Core boundary

Discord is the visible coordination room. Git branches/worktrees, repository
state, tests, builds, and human review remain authoritative for implementation.
An agent must not modify the Unity checkout merely because it received a Discord
message.
