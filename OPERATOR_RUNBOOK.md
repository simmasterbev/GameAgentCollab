# Game Agent Collaboration Operator Runbook

This is the day-to-day guide for running the Discord coordination system with
`Agent_Bev` on the desktop and `Agent_Salty` on BevBot001.

The system has three layers: Discord is the visible conversation and intervention
layer; `collabctl.py` converts Discord traffic to and from the JSON protocol; and
Codex runs locally on each machine against that machine's assigned checkout.

The coordination repository is not the Unity game repository. Each agent uses a
separate Unity branch/worktree. The current agent worktrees are aligned to
`b8e68abdd7226980c27b67d3445bf12d3b388a4b` as of 2026-08-12.

## 1. One-time setup

Install and authenticate Python, Git, and Codex on each machine:

```powershell
python --version
git --version
codex --version
```

Clone the collaboration repository if needed:

```powershell
git clone https://github.com/simmasterbev/GameAgentCollab.git
cd .\GameAgentCollab
python -B .\collabctl.py self-test
```

The Discord bot needs permission to view history, read messages, send messages,
create Forum posts/threads when used, and use the `MESSAGE_CONTENT` privileged
intent. Keep the bot token out of Git, Discord, screenshots, and messages.

## 2. Machine-specific paths

| Agent | Collaboration repo | Unity worktree | State file |
|---|---|---|---|
| `Agent_Bev` | `F:\GameAgentCollab` | `F:\GameAgentWorktrees\Agent_Bev` | `state\AGENT-BEV-LIVE.json` |
| `Agent_Salty` | `C:\Users\bevadmin\GameAgentCollab` | `C:\Users\bevadmin\GameAgentWorktrees\Agent_Salty` | `state\AGENT-SALTY-LIVE.json` |

Use the Unity worktree when asking an agent to read or modify game files. The
collaboration repository contains the coordination tool, not the game.

## 3. Set the environment in each worker window

Run these commands in the same PowerShell window that will launch the worker.
Variables set in another window or a previous SSH session are not inherited.

### Desktop / Agent_Bev

```powershell
cd F:\GameAgentCollab
$env:DISCORD_BOT_TOKEN = 'paste-token-locally-only'
$env:DISCORD_CHANNEL_ID = 'paste-thread-channel-id'
$env:COLLAB_AGENT_ID = 'Agent_Bev'
```

If the normal `codex` command reports that `codex-windows-sandbox-setup.exe`
is missing, set `CODEX_BIN` to the matching packaged `bin\codex.exe`:

```powershell
$env:CODEX_BIN = 'C:\Users\bevin\.codex\packages\standalone\releases\0.145.0-x86_64-pc-windows-msvc\bin\codex.exe'
& $env:CODEX_BIN --version
```

### BevBot001 / Agent_Salty

```powershell
cd C:\Users\bevadmin\GameAgentCollab
$env:DISCORD_BOT_TOKEN = 'paste-token-locally-only'
$env:DISCORD_CHANNEL_ID = 'paste-thread-channel-id'
$env:COLLAB_AGENT_ID = 'Agent_Salty'
$env:CODEX_BIN = 'C:\Users\bevadmin\.codex\packages\standalone\releases\0.146.0-x86_64-pc-windows-msvc\bin\codex.exe'
& $env:CODEX_BIN --version
```

The channel ID should normally be the Discord Forum thread/post channel ID,
not the parent `#tasks` Forum channel ID. For a normal text channel, use that
text channel's ID.

## 4. Start each worker

Start one worker per machine and keep each PowerShell window open.

### Agent_Bev

```powershell
python -B .\collabctl.py worker `
  --agent-id 'Agent_Bev' `
  --channel-id $env:DISCORD_CHANNEL_ID `
  --state-file '.\state\AGENT-BEV-LIVE.json' `
  --natural-language `
  --handler python .\codex_runtime.py `
    --workdir 'F:\GameAgentWorktrees\Agent_Bev' `
    --sandbox read-only `
    --reply-target 'Agent_Salty'
```

### Agent_Salty

```powershell
python -B .\collabctl.py worker `
  --agent-id 'Agent_Salty' `
  --channel-id $env:DISCORD_CHANNEL_ID `
  --state-file '.\state\AGENT-SALTY-LIVE.json' `
  --natural-language `
  --handler python .\codex_runtime.py `
    --workdir 'C:\Users\bevadmin\GameAgentWorktrees\Agent_Salty' `
    --sandbox read-only `
    --reply-target 'Agent_Bev'
```

The worker polls Discord every five seconds. Stop it with `Ctrl+C`. Use `--once`
before the continuous run for one safe cycle. Keep the state file so processed
messages are not replayed, and use a different state file for each agent.

## 5. Run a basic interaction test

With both workers running, send this as a normal Discord message:

```text
Agent_Salty, confirm you are online and report your current workdir. Do not ask Agent_Bev a question.
```

Expected result: Agent_Salty acknowledges and posts a readable response with a
JSON audit payload. It should report the Unity worktree, not `GameAgentCollab`.

For a direct agent-to-agent test:

```text
Agent_Salty, tell Agent_Bev a joke.
```

Expected result: Agent_Salty sends one peer-targeted message, Agent_Bev replies
once, and the exchange stops. Do not manually repost generated JSON.

## 6. Send useful human tasks

Address one agent when only one worker should act:

```text
Agent_Bev, inspect the current terrain system and list the five most relevant files. Do not edit files.
```

```text
Agent_Salty, review the cellular-automata simulation documentation and identify the next bounded read-only task. Keep it under 400 characters.
```

Address both for independent reports:

```text
Agent_Bev and Agent_Salty, independently report your current branch and commit. Do not edit files.
```

Use delegation phrasing for a controlled peer handoff:

```text
Agent_Bev, ask Agent_Salty to inspect the terrain definitions and report any limitations.
```

Peer delegation is intentionally one turn. The recipient replies once and the
transport suppresses an automatic bounce-back. Start a new explicit request for
another turn.

Plain English does not need JSON fences. Manually entered JSON must be inside a
literal fenced block beginning with `json` and ending with a closing fence.
Bot-generated JSON is the audit/backend representation; the readable response is
the operator-facing representation.

## 7. Create a fresh test thread

For a clean supervised test, create a new Forum thread:

```powershell
cd F:\GameAgentCollab
$env:DISCORD_BOT_TOKEN = 'paste-token-locally-only'
$forumChannelId = 'paste-parent-tasks-forum-channel-id'

python -B .\collabctl.py create-task --live `
  --channel-id $forumChannelId `
  --create-thread `
  --task-id CROSS-MACHINE-TEST-003 `
  --summary 'Agent_Bev and Agent_Salty should confirm a supervised Discord conversation.'
```

For `create-task`, use the parent Forum channel ID. After the command creates
the post, use the returned/new thread ID as `DISCORD_CHANNEL_ID` for both
workers. Use a new state file for a genuinely new thread, or retain the existing
state file when continuing an existing thread.

## 8. Check what the transport sees

Read without dispatching:

```powershell
python -B .\collabctl.py read --channel-id $env:DISCORD_CHANNEL_ID
```

Poll and persist a cursor:

```powershell
python -B .\collabctl.py poll `
  --channel-id $env:DISCORD_CHANNEL_ID `
  --state-file '.\state\AGENT-BEV-LIVE.json'
```

Run local protocol checks:

```powershell
python -B .\collabctl.py self-test
python -B .\collabctl.py test-sequence
```

These local tests do not contact Discord. Add `--live` only when you intend to
post to the server.

## 9. Git and editing boundary

Discord coordination does not authorize code changes. The workers currently use
`--sandbox read-only`, so they can inspect and report but cannot edit Unity.

When implementation is intentionally enabled later:

1. Keep agents on separate Unity branches/worktrees.
2. Confirm both worktrees start from the intended commit.
3. Assign a narrow file/task scope in Discord.
4. Require changed files, tests, and commit hash in the response.
5. Review and merge through Git; never share one live Unity checkout.

Check either worktree:

```powershell
git status --short --branch
git rev-parse --short HEAD
git branch --show-current
```

## 10. Troubleshooting

### Worker says no messages

- Confirm the worker is running.
- Confirm the ID is the thread/post ID, not the parent Forum ID.
- Confirm the message names the intended agent.
- Confirm the bot can view history and send in the channel.
- Confirm the workers use different state files.

### Human messages are invisible

Enable the bot's Discord `MESSAGE_CONTENT` privileged intent and restart the
worker. Bot-authored protocol messages may still be readable when human text is
not.

### Sandbox helper is missing

Use the packaged Codex binary through `CODEX_BIN`, matching the installed
release, and verify `& $env:CODEX_BIN --version`.

### Agent reports the wrong files

Check `--workdir`. It must point to that agent's Unity worktree, not
`GameAgentCollab`.

### PowerShell errors on multiline commands

PowerShell uses the backtick `` ` `` for line continuation. A Unix backslash
does not continue a PowerShell command. Tokens and IDs should be quoted strings.

### Agent replies repeatedly

Stop and restart the worker only if needed, then start a new explicit task. Peer
delegations are one-turn guarded, but manually reposting generated messages can
create new tasks.

### Restart procedure

Press `Ctrl+C`, leave the state file in place, set environment variables again if
you opened a new PowerShell window, and run the same worker command.

## Operator checklist

- [ ] Correct collaboration repository
- [ ] Correct agent ID
- [ ] Token set only in the local worker window
- [ ] Correct Discord thread/channel ID
- [ ] Correct Unity worktree in `--workdir`
- [ ] Separate state file per agent
- [ ] `codex --version` or `CODEX_BIN` verified
- [ ] `self-test` passed
- [ ] One-shot worker cycle passed
- [ ] Continuous worker is running
- [ ] Human task response observed
- [ ] No edits enabled until explicitly intended
