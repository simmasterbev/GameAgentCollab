# Salty Handoff: Agent B Setup

This guide sets up Salty's machine as `agent-b` in the shared Discord
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

The Codex CLI must also be installed and authenticated because the worker
invokes `codex exec`:

```powershell
codex --version
```

## 3. Configure Agent B locally

Use the same Coordination Bot token as Agent A, but keep the token local to
this machine. Never commit it or paste it into Discord or GitHub.

Use the Discord thread's channel ID. Use the thread ID, not the parent
`#tasks` Forum channel ID.

```powershell
$repo = (Get-Location).Path
$env:DISCORD_BOT_TOKEN = 'paste-the-token-locally-only'
$env:DISCORD_CHANNEL_ID = 'paste-the-discord-thread-id'
$env:COLLAB_AGENT_ID = 'agent-b'
```

The worker's state file is local and must not be shared with Agent A:

```text
.\state\AGENT-B-LIVE.json
```

## 4. Start the worker

First run one cycle:

```powershell
python -B .\collabctl.py worker `
  --agent-id agent-b `
  --channel-id $env:DISCORD_CHANNEL_ID `
  --state-file '.\state\AGENT-B-LIVE.json' `
  --natural-language `
  --once `
  --handler python .\codex_runtime.py `
    --workdir $repo `
    --sandbox read-only `
    --reply-target agent-a
```

Then start the continuous worker:

```powershell
python -B .\collabctl.py worker `
  --agent-id agent-b `
  --channel-id $env:DISCORD_CHANNEL_ID `
  --state-file '.\state\AGENT-B-LIVE.json' `
  --natural-language `
  --handler python .\codex_runtime.py `
    --workdir $repo `
    --sandbox read-only `
    --reply-target agent-a
```

Leave this PowerShell window running. Stop it with `Ctrl+C`; restart it with
the same command. Keep the state file so already-processed messages are not
replayed.

## 5. Run the first test

In the Discord thread, Bevin can send:

```text
Agent B, confirm you are online and give me a concise status update. Do not ask Agent A a question.
```

Agent B should answer in readable language and include the protocol JSON audit
payload underneath. A human message without an explicit agent name can be
routed to both agents, so use `Agent B` when only Salty's worker should act.

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
git switch -c agent-b/<short-task-name>
```

Agent B should work only in its own branch/worktree, commit there, and push
that branch for review. Never share one live Unity checkout with Agent A.

## Troubleshooting

- PowerShell line continuation uses the backtick `` ` ``, not a backslash.
- If human messages are invisible to the worker, enable Discord's privileged
  Message Content Intent for the Coordination Bot.
- Plain English does not need JSON fences. Manually entered JSON must be inside
  a literal fenced block beginning with ````json````.
- If there is no response, confirm the worker process is still running, the
  message says `Agent B`, and the bot can view history and send messages in the
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
- [ ] Agent B token and thread ID are set locally
- [ ] One-shot worker cycle completes
- [ ] Continuous worker is running
- [ ] Discord test receives an Agent B response
- [ ] Unity work uses a separate branch/worktree
