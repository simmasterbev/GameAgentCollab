# Salty Handoff: Agent_Salty Setup

This guide sets up Salty's machine as `Agent_Salty` in the shared Discord
collaboration system.

## 1. Accept GitHub access

Accept the `simmasterbev/GameAgentCollab` collaborator invitation. The
repository is public, so cloning works immediately; accepting the invitation
is required before pushing changes.

## 2. Clone the collaboration tool

In PowerShell:

```powershell
git clone https://github.com/simmasterbev/GameAgentCollab.git
cd .\GameAgentCollab
```

Run the local check:

```powershell
python -B .\collabctl.py self-test
```

This release names the backend identities `Agent_Bev` and `Agent_Salty`. If
you are upgrading an older checkout, pull this commit, stop the old worker,
and use a fresh state file. Do not reuse a state file created for `agent-b`.

The Codex CLI must also be installed and authenticated because the worker
invokes `codex exec`:

```powershell
codex --version
```

## 3. Configure Agent_Salty locally

Use the same Coordination Bot token as Agent_Bev, but keep the token local to
this machine. Never commit it or paste it into Discord or GitHub.

Use the Discord thread's channel ID. Use the thread ID, not the parent
`#tasks` Forum channel ID.

```powershell
$repo = (Get-Location).Path
$env:DISCORD_BOT_TOKEN = 'paste-the-token-locally-only'
$env:DISCORD_CHANNEL_ID = 'paste-the-discord-thread-id'
$env:COLLAB_AGENT_ID = 'Agent_Salty'
```

The worker's state file is local and must not be shared with Agent_Bev:

```text
.\state\AGENT-B-LIVE.json
```

## 4. Start the worker

First run one cycle:

```powershell
python -B .\collabctl.py worker `
  --agent-id Agent_Salty `
  --channel-id $env:DISCORD_CHANNEL_ID `
  --state-file '.\state\AGENT-B-LIVE.json' `
  --natural-language `
  --once `
  --handler python .\codex_runtime.py `
    --workdir $repo `
    --sandbox read-only `
    --reply-target Agent_Bev
```

Then start the continuous worker:

```powershell
python -B .\collabctl.py worker `
  --agent-id Agent_Salty `
  --channel-id $env:DISCORD_CHANNEL_ID `
  --state-file '.\state\AGENT-B-LIVE.json' `
  --natural-language `
  --handler python .\codex_runtime.py `
    --workdir $repo `
    --sandbox read-only `
    --reply-target Agent_Bev
```

Leave this PowerShell window running. Stop it with `Ctrl+C`; restart it with
the same command. Keep the state file so already-processed messages are not
replayed.

## 5. Run the first test

In the Discord thread, Bevin can send:

```text
Agent_Salty, confirm you are online and give me a concise status update. Do not ask Agent_Bev a question.
```

Agent_Salty should answer in readable language and include the protocol JSON audit
payload underneath. A human message without an explicit agent name can be
routed to both agents, so use `Agent_Salty` when only Salty's worker should act.

Peer delegation is supported with patterns such as:

```text
Agent_Salty, tell Agent_Bev a joke.
Agent_Salty, ask Agent_Bev to inspect the worker.
Agent_Salty, send Agent_Bev the current status.
Agent_Salty, delegate the validation task to Agent_Bev.
```

The first named agent acts, the second receives the peer message, and the
recipient worker can answer through the same Discord thread. Mentioning both
agents without a delegation verb still broadcasts the task to both workers.

The current runtime is read-only and inspect-only. It can answer, report
status, and coordinate work, but it should not edit the Unity project yet.

## 6. Git boundary for game work

The collaboration repository is only the coordination tool. Do not use it as
the Unity game checkout. For game changes, use a separate local clone or
worktree:

```powershell
git clone https://github.com/Saltylanguage/GameDev.git
cd .\GameDev
git fetch origin
git switch --track origin/SaltysFirstBranch
git switch -c Agent_Salty/<short-task-name>
```

Agent_Salty should work only in its own branch/worktree, commit there, and push
that branch for review. Never share one live Unity checkout with Agent_Bev.

## Troubleshooting

- PowerShell line continuation uses the backtick `` ` ``, not a backslash.
- If human messages are invisible to the worker, enable Discord's privileged
  Message Content Intent for the Coordination Bot.
- Plain English does not need JSON fences. Manually entered JSON must be inside
  a literal fenced block beginning with ````json````.
- If there is no response, confirm the worker process is still running, the
  message says `Agent_Salty`, and the bot can view history and send messages in the
  thread.
- For a clean first run, use a new Discord thread. A new empty state file on an
  old thread can replay historical messages.
- State files, `.env` files, tokens, and logs are ignored by Git. Do not force
  add them.

## Ready checklist

- [ ] GitHub collaborator invitation accepted
- [ ] `collabctl.py self-test` passes
- [ ] Codex CLI is authenticated
- [ ] `MESSAGE_CONTENT` intent is enabled
- [ ] Agent_Salty token and thread ID are set locally
- [ ] One-shot worker cycle completes
- [ ] Continuous worker is running
- [ ] Discord test receives an Agent_Salty response
- [ ] Unity work uses a separate branch/worktree
