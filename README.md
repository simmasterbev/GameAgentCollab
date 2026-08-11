# Game Agent Collaboration

Siloed collaboration control-plane design for two coding agents working on the
cellular-automata game with human observation and intervention through Discord.

This repository is intentionally separate from the Unity game repository at
`F:\CellularAutomataGameDev`. It contains no Unity code, assets, package files,
Discord credentials, bot tokens, or private conversation transcripts.

## Current status

Documentation-only v0.1. No Discord server, bot runtime, agent connector, or
repository automation has been built yet.

## Read in order

1. `COLLABORATION_CHARTER.md`
2. `MESSAGE_SCHEMA.md`
3. `TASK_LIFECYCLE.md`
4. `OWNERSHIP_RULES.md`
5. `ACCEPTANCE_GATES.md`

## Core boundary

Discord is the visible coordination room. Git branches/worktrees, repository
state, tests, builds, and human review remain authoritative for implementation.
An agent must not modify the Unity checkout merely because it received a Discord
message.
