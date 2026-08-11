# Task lifecycle

Version: 0.2
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

## Mid-task split and pivot

The parent task does not have to stay linear. An agent may discover that a
different part of the feature should be handled by the other agent.

1. **Request assistance** - The current owner posts an `assist_request` naming
   the parent task, proposed child task, remaining work, scope, dependency, and
   reason. The parent owner keeps responsibility while waiting.
2. **Accept or decline** - The target agent explicitly accepts or rejects the
   child task. Silence is not acceptance.
3. **Run in parallel or sequence** - After acceptance, the child task gets its
   own claim, branch/worktree, and acceptance gates. The parent task records the
   dependency and may continue on disjoint work.
4. **Integrate** - The child owner posts a handoff with commit and validation.
   The parent owner integrates or requests review, then closes the child task.
5. **Transfer if needed** - If the whole remaining task should change owners,
   the current owner posts a pivot/transfer proposal. Ownership changes only
   after explicit acceptance or human approval.

This records a pivot as a state transition rather than burying it in chat.

## No silent takeover

An agent must not infer ownership from a message, branch name, or inactivity.
Expired claims become `expired` and require a new claim. A human may force a
release or reassignment, which the bot records as a control event.

## Accountability rule

Splitting work creates a parent/child task relationship. The parent owner stays
accountable for the parent task's final integration unless a full transfer is
accepted. A collaborator can own a child task without owning the feature.

## Minimum completion record

Every completed implementation task must identify:

- task ID and owner;
- branch/worktree and base/current commit;
- changed files;
- validation commands and results;
- known risks or unverified checks;
- review decision and next action.
