# Task lifecycle

Version: 0.1
Status: draft

## States

`proposed -> claimed -> active -> review -> accepted -> released`

Alternative terminal or paused states are `blocked`, `rejected`, `abandoned`,
and `expired`.

## Flow

1. **Propose** - A human or agent creates a task with a stable ID, objective,
   target agent, and initial acceptance gates.
2. **Claim** - One agent declares its branch/worktree, base commit, file scope,
   risks, and claim expiry. The bot rejects a conflicting active claim unless a
   human approves the overlap.
3. **Start** - The agent confirms repository status and records the actual base
   commit before editing.
4. **Collaborate** - Agents use questions, progress messages, and blockers.
   Messages reference the task ID and correlation ID rather than relying on
   channel position or conversation memory.
5. **Review** - The agent posts changed files, commit, validation actually run,
   remaining risks, and next actions. A human or the other agent reviews it.
6. **Accept or reject** - Acceptance requires the declared gates to pass. A
   rejection explains what must change and whether the claim remains active.
7. **Release** - The agent releases the scope claim after handoff, merge, or
   explicit abandonment.

## No silent takeover

An agent must not infer ownership from a message, branch name, or inactivity.
Expired claims become `expired` and require a new claim. A human may force a
release or reassignment, which the bot records as a control event.

## Minimum completion record

Every completed implementation task must identify:

- task ID and owner;
- branch/worktree and base/current commit;
- changed files;
- validation commands and results;
- known risks or unverified checks;
- review decision and next action.
