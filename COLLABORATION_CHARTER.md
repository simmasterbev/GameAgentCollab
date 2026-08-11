# Collaboration charter

Version: 0.1
Status: draft

## Purpose

Provide a visible, human-observable coordination room for two coding agents
working on the same game project. Agents may exchange questions, task claims,
progress, blockers, review requests, and handoffs through a dedicated Discord
server. The human owner and human collaborator may observe, assign, pause,
approve, reject, or reassign work.

## Roles

- `human-owner`: controls project direction, permissions, approvals, and stops.
- `human-collaborator`: observes, discusses, reviews, and may be granted task
  assignment or approval authority by the owner.
- `agent-a` and `agent-b`: perform bounded work through separate branches or
  worktrees and report their state in Discord.
- `coordination-bot`: routes and records collaboration messages. It is not the
  source of truth for code and does not silently resolve conflicts.

## Non-negotiable rules

1. Never put tokens, passwords, private credentials, or full private transcripts
   in Discord or this repository.
2. Every implementation task has one stable task ID, one current owner, one
   declared branch/worktree, and one explicit file/scope claim.
3. An agent must announce its claim before editing and release or renew it when
   the task changes state.
4. Agents do not edit another agent's claimed scope without an explicit handoff
   or human-approved overlap.
5. Discord coordinates. Git, checked-in project files, validation output, and
   human review determine what is actually true.
6. Ambiguous ownership, stale repository state, failed validation, or unclear
   message provenance means stop and ask for clarification.
7. Human stop, pause, or reassignment instructions override agent plans.

## Operating style

The system should prefer small, reviewable tasks, explicit acceptance gates, and
durable summaries over long conversation replay. Agents should communicate the
next action and evidence needed, not dump hidden reasoning or entire tool logs.
