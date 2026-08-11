# Acceptance gates

Version: 0.1
Status: draft

The system is not ready for unattended repository writes until the gates below
pass in order.

## Gate 0 - Silo and safety

- This repository remains outside the Unity checkout.
- No Unity assets, packages, source files, bot tokens, or private transcripts
  are stored here.
- The repository has its own Git history and ignore rules.

## Gate 1 - Protocol

- The message envelope validates required fields, enums, IDs, timestamps, path
  rules, size limits, and sender/target values.
- Duplicate messages are rejected.
- Human-readable and machine-control content cannot silently disagree.

## Gate 2 - Coordination bot

- A restricted Discord server and test channels exist.
- The bot can post and read structured messages with least-privilege access.
- Human control events, bot errors, and message routing are observable.
- Missing credentials disable the integration without affecting the game.

## Gate 3 - Agent connectors

- Both agents can receive only messages addressed to them or both agents.
- Agents ignore their own messages and unknown/invalid messages.
- A cursor or equivalent prevents repeated processing after restart.

## Gate 4 - Ownership

- Claims record task, agent, branch/worktree, base commit, scope, and expiry.
- Overlapping active claims are blocked or escalated to a human.
- Repository preflight detects wrong branch, unexpected dirty files, and stale
  base commits before editing.

## Gate 5 - Supervised end-to-end task

Prove one real task from proposal through claim, progress, question, blocker or
review, completion, human approval, and release. Record the Discord message IDs,
Git commits, validation output, and any unverified behavior.

## Gate 6 - Optional unattended operation

Only consider this after Gate 5 passes repeatedly. Add bounded leases, explicit
stop conditions, rate-limit/retry behavior, crash recovery, human pause, and a
clear audit trail before allowing overnight or autonomous work.
