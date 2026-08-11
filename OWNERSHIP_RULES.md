# Ownership and conflict rules

Version: 0.1
Status: draft

## Enforcement boundary

Discord claims are coordination records, not filesystem locks. The enforcement
boundary is a separate Git branch or worktree plus a preflight check against the
actual repository state.

## Claim requirements

A claim must name:

- one task ID and owner;
- one repository;
- one branch and worktree;
- one base commit;
- one or more repository-relative path patterns;
- claim expiry or an explicit no-expiry human decision.

## Before editing

The agent must verify:

1. The working tree is the expected worktree.
2. The branch and base commit match the claim.
3. No unowned local changes would be overwritten.
4. No active claim overlaps the intended scope.
5. The task's acceptance gates are understood.

If any check fails, the agent posts a blocker and does not edit.

## Overlap resolution

- Disjoint scopes may proceed independently.
- Shared files require a handoff, a narrower scope, serialized ownership, or
  explicit human approval.
- A task that discovers unexpected overlap pauses before modifying it.
- The coordination bot should warn on obvious pattern overlap, but humans and
  repository checks remain the final authority.

## Human controls

Humans may pause, release, reassign, narrow, or approve an ownership claim. The
bot records the control event with the acting human, timestamp, reason, and task
ID. It must not hide or rewrite the earlier claim.
