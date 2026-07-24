# Review Fix Loop Cross-Runtime Protocol Design

## Goal

Make manually created Codex and Claude Code tasks coordinate reliably through the same `review.md` and `feedback.md` files. A peer must be able to verify that the other role has a live, independent listener without relying on cross-sandbox process inspection.

## Shared paths

Resolve the protocol directory in this order:

1. Use the absolute `REVIEW_LOOP_DIR` value when set.
2. Otherwise use `<project_root>/.review-loop`.

Resolve these paths once and include their absolute values in every readiness record:

- `<protocol_dir>/review.md`
- `<protocol_dir>/feedback.md`
- `<protocol_dir>/listeners/<listener_id>.json`

Codex and Claude Code instructions must use this identical rule. Repository-root `review.md` and `feedback.md` are not protocol files.

## Listener executable

Bundle byte-identical copies of a Python standard-library CLI with the Codex skill and the Claude Code command. Each runtime resolves the script adjacent to its own instruction file.

The CLI provides:

- `listen`: run a foreground, level-triggered polling loop intended for an independent background tool session.
- `verify`: validate schema, role, watched path, `RUNNING` status, and heartbeat freshness without using `ps`. The default maximum heartbeat age is five seconds.

`listen` writes its state atomically once per second and handles `SIGINT` and `SIGTERM` by atomically recording `STOPPED`. State includes:

- schema version
- listener ID and role
- absolute watched path
- `RUNNING` or `STOPPED`
- activation and heartbeat timestamps
- initial content hash and exact initial snapshot
- deduplication key definition
- diagnostic PID

The listener scans immediately after activation. Initial and later scans use the same deduplication key:

`(SESSION_ID, STATUS, ROUND, content hash)`

The CLI prints each unique scan event to stdout so the owning task can consume events from its background tool session. Heartbeat freshness, not PID visibility, is the cross-runtime liveness proof.

## Protocol record

Both files use the same required plain-text header followed by Markdown content:

```text
SESSION_ID: <uuid>
ROUND: <non-negative integer>
STATUS: <status>
ROLE: <REVIEWER|FIXER>
LISTENER_STATE: <absolute listener JSON path>
TIMESTAMP: <ISO-8601 UTC>

<Markdown body>
```

Fields are single-line, case-sensitive, and appear once. Peer acceptance requires parsing every field and running `verify` against `LISTENER_STATE`.

Allowed readiness and loop statuses are:

- `REVIEWER_READY`, `ISSUES_FOUND`, and `LGTM` in `review.md`
- `FIXER_READY`, `FIXED`, `PARTIAL`, and `FAILED` in `feedback.md`

## Ownership and state machine

- Reviewer alone writes `review.md`, creates `SESSION_ID`, and never increments `ROUND`.
- Fixer alone writes `feedback.md` and alone increments `ROUND`.
- Reviewer listener watches `feedback.md`.
- Fixer listener watches `review.md`.
- Fixer must never create, initialize, truncate, or overwrite `review.md`, including when it is missing.
- Reviewer must never create, initialize, truncate, or overwrite `feedback.md`.

Reviewer writes `REVIEWER_READY` at round 0 only after its listener is verified. Fixer binds only after verifying that record and its live Reviewer listener, then writes `FIXER_READY` at round 0. Reviewer verifies the matching live Fixer listener before reviewing.

Stale sessions, stale heartbeats, malformed records, duplicates, wrong roles, and wrong watched paths are non-actionable. Before binding, Fixer continues waiting. After binding, unverifiable peer evidence terminates the workflow.

On matching `LGTM`, each role stops its own listener immediately and confirms the state file says `STOPPED`.

## Distribution

The source of truth lives under `open-skills/skills/review-fix-loop/`:

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/review_loop_listener.py`
- `tests/test_review_loop_protocol.py`

The installed Codex skill is synchronized from that directory. Claude Code receives the equivalent command text at `~/.claude/commands/review-fix-loop.md` and a byte-identical script at `~/.claude/commands/review-fix-loop/review_loop_listener.py`.

## Testing

Regression tests first demonstrate the current failures:

- Codex and Claude resolve different protocol paths.
- They emit incompatible record formats.
- No deterministic listener executable exists.
- Fixer can fabricate `REVIEWER_READY`.

After implementation, tests cover:

1. Both instruction files specify the same path and record contract.
2. Listener activation performs an immediate scan and records a fresh heartbeat.
3. `verify` accepts a live listener with the expected role/path.
4. `verify` rejects stale heartbeat, wrong role, wrong path, and stopped listener.
5. Deduplication suppresses unchanged records.
6. Signal termination records `STOPPED`.
7. Reviewer-first and Fixer-first cold starts converge.
8. Legacy protocol files outside `.review-loop` and stale in-directory files are ignored.
9. Fixer instructions contain no action that writes `review.md`.

## Error handling

The CLI exits nonzero with a concise reason when state is missing, malformed, stale, mismatched, or stopped. The workflow treats verification failures exactly as specified by the pre-bind/post-bind rules and never falls back to self-asserted listener status.
