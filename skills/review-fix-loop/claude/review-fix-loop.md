---
name: review-fix-loop
description: Use when two manually created Codex or Claude Code tasks must coordinate review and fixes without stale-file races, lost readiness handoffs, or unverifiable peer listeners.
---

# Review Fix Loop

Invoke `/review-fix-loop reviewer` or `/review-fix-loop fixer`. If the role is missing or invalid, ask once for exactly one role and take no workflow action.

## Shared paths

Resolve the project root first, then resolve the protocol directory:

1. Use the absolute `REVIEW_LOOP_DIR` value when set.
2. Otherwise use `<project_root>/.review-loop`.

Create the protocol directory and its `listeners` child when absent. Resolve these absolute paths once:

- `<protocol_dir>/review.md`
- `<protocol_dir>/feedback.md`
- `<protocol_dir>/listeners/<listener_id>.json`

Repository-root `review.md` and `feedback.md` are not protocol files. Never read or write them for this workflow.

## Start the independent listener

Use `~/.claude/commands/review-fix-loop/review_loop_listener.py`. The first workflow action after role validation and path resolution is starting this command in an independent long-running background tool session:

```bash
python3 ~/.claude/commands/review-fix-loop/review_loop_listener.py listen \
  --role <reviewer_or_fixer> \
  --watch <absolute_peer_file> \
  --state <absolute_listener_state_json> \
  --listener-id <unique_listener_id>
```

Reviewer watches `feedback.md`; Fixer watches `review.md`. Record both the background tool-session ID and listener state path. Do not use a foreground polling fallback.

The listener performs an immediate scan and emits later unique scans using this deduplication key:

`(SESSION_ID, STATUS, ROUND, content hash)`

Verify the listener before any protocol write:

```bash
python3 ~/.claude/commands/review-fix-loop/review_loop_listener.py verify \
  --state <absolute_listener_state_json> \
  --role <reviewer_or_fixer> \
  --watch <absolute_peer_file> \
  --max-age 5
```

If listener startup, immediate scan, or verification fails, stop with no review, code change, or protocol write.

## Protocol record

Both protocol files use this exact case-sensitive header followed by a blank line and Markdown body:

```text
SESSION_ID: <uuid>
ROUND: <non-negative integer>
STATUS: <status>
ROLE: <REVIEWER|FIXER>
LISTENER_STATE: <absolute listener JSON path>
TIMESTAMP: <ISO-8601 UTC>
```

Allowed statuses:

- `review.md`: `REVIEWER_READY`, `ISSUES_FOUND`, `LGTM`
- `feedback.md`: `FIXER_READY`, `FIXED`, `PARTIAL`, `FAILED`

Accept a peer record only after parsing every required field and successfully running `verify` on its `LISTENER_STATE` with the peer's expected role and watched path. A written `RUNNING` value, PID, or listener ID alone is not liveness proof.

## File ownership

- Reviewer alone writes `review.md`, creates `SESSION_ID`, and never increments `ROUND`.
- Fixer alone writes `feedback.md` and alone increments `ROUND`.
- Fixer must never create, initialize, truncate, or overwrite `review.md`, including when it is missing.
- Reviewer must never create, initialize, truncate, or overwrite `feedback.md`, including when it is missing.

Treat a missing peer file as an empty initial snapshot and keep waiting through the live listener.

## Cold-start barrier

Before the barrier completes, do not review or modify code. The readiness write owned by the current role is the only permitted protocol write.

### Reviewer

1. After its `feedback.md` listener is live and immediately scanned, create a unique `SESSION_ID`.
2. Write `review.md` with `REVIEWER_READY`, round 0, role `REVIEWER`, and the Reviewer listener state path.
3. Accept only matching-session `FIXER_READY` round 0.
4. Verify that the referenced Fixer listener is live, has role `fixer`, and watches the expected absolute `review.md`.
5. Mark the barrier complete.

### Fixer

1. After its `review.md` listener is live, process the immediate scan through the normal dedupe path.
2. Accept only `REVIEWER_READY` round 0 whose referenced Reviewer listener is live, has role `reviewer`, and watches the expected absolute `feedback.md`.
3. Before binding, treat missing, malformed, stale, stopped, or unverifiable candidates as non-actionable; remain unbound and wait for a fresh valid readiness record.
4. Bind the valid `SESSION_ID`.
5. Write `feedback.md` with `FIXER_READY`, round 0, role `FIXER`, and the Fixer listener state path.

The Fixer never manufactures a bootstrap `REVIEWER_READY` or chooses a session ID.

## Review/fix loop

After the barrier:

1. Reviewer reviews the target changes and overwrites `review.md` at round 0 with either `LGTM` or `ISSUES_FOUND`.
2. Fixer accepts only the bound session and its most recently expected round.
3. On issues, Fixer changes and verifies code, increments the round exactly once immediately before writing `feedback.md`, and reports `FIXED`, `PARTIAL`, or `FAILED`.
4. Reviewer accepts matching-session feedback only when its round is strictly greater than the last reviewed round, reviews the new code, and echoes that round unchanged in `review.md`.
5. Reviewer never increments the round.

Wrong sessions, wrong rounds, malformed records, and duplicate dedupe keys are non-actionable. After binding, terminate if current peer evidence cannot be verified; do not silently rebind.

## Terminal state

A valid matching `LGTM` states the echoed reviewed round. Immediately stop the role's own background listener, then inspect its state JSON and confirm `status` is `STOPPED`. Never modify code or protocol files, restart listening, or reuse that session after `LGTM`.
