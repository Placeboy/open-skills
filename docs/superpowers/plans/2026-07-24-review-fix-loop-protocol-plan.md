# Review Fix Loop Cross-Runtime Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Codex and Claude Code Reviewer/Fixer tasks use one protocol directory, one record schema, and independently verifiable heartbeat listeners.

**Architecture:** Store source instructions and a standard-library Python listener under `skills/review-fix-loop`. Both runtimes use `<project_root>/.review-loop`, plain-text protocol headers, and listener JSON state whose fresh heartbeat is the liveness proof. Version the Claude command alongside the Codex skill, then synchronize those sources into the local runtime installations.

**Tech Stack:** Markdown skill/command files, Python 3 standard library, `unittest`, subprocess-based integration tests.

## Global Constraints

- Use absolute `REVIEW_LOOP_DIR` when set; otherwise use `<project_root>/.review-loop`.
- Do not use `ps`, PID visibility, or a self-asserted `RUNNING` field as peer liveness proof.
- Default maximum heartbeat age is five seconds.
- Reviewer alone writes `review.md`; Fixer alone writes `feedback.md`.
- Reviewer listener watches `feedback.md`; Fixer listener watches `review.md`.
- Keep listener copies byte-identical across Codex and Claude installations.
- Do not add third-party runtime dependencies.

---

### Task 1: Lock the shared instruction contract

**Files:**
- Create: `skills/review-fix-loop/tests/test_review_loop_protocol.py`
- Modify: `skills/review-fix-loop/SKILL.md`
- Create: `skills/review-fix-loop/claude/review-fix-loop.md`

**Interfaces:**
- Consumes: the approved design at `docs/superpowers/specs/2026-07-24-review-fix-loop-protocol-design.md`
- Produces: `PROTOCOL_HEADER`, `PATH_CONTRACT`, and ownership wording shared by both runtime instruction files

- [ ] **Step 1: Write the failing instruction contract test**

Create a `unittest.TestCase` that loads the Codex and Claude instruction files and checks the exact shared fragments:

```python
from pathlib import Path
import unittest

SKILL_DIR = Path(__file__).resolve().parents[1]
CODEX_TEXT = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
CLAUDE_PATH = SKILL_DIR / "claude" / "review-fix-loop.md"

PATH_CONTRACT = """1. Use the absolute `REVIEW_LOOP_DIR` value when set.
2. Otherwise use `<project_root>/.review-loop`."""

PROTOCOL_HEADER = """SESSION_ID: <uuid>
ROUND: <non-negative integer>
STATUS: <status>
ROLE: <REVIEWER|FIXER>
LISTENER_STATE: <absolute listener JSON path>
TIMESTAMP: <ISO-8601 UTC>"""


class InstructionContractTests(unittest.TestCase):
    def test_claude_command_is_versioned(self):
        self.assertTrue(CLAUDE_PATH.is_file())

    def test_both_runtimes_use_same_path_and_header_contract(self):
        claude_text = CLAUDE_PATH.read_text(encoding="utf-8")
        for text in (CODEX_TEXT, claude_text):
            self.assertIn(PATH_CONTRACT, text)
            self.assertIn(PROTOCOL_HEADER, text)

    def test_ownership_is_explicit(self):
        claude_text = CLAUDE_PATH.read_text(encoding="utf-8")
        required = (
            "Reviewer alone writes `review.md`",
            "Fixer alone writes `feedback.md`",
            "Fixer must never create, initialize, truncate, or overwrite `review.md`",
        )
        for text in (CODEX_TEXT, claude_text):
            for fragment in required:
                self.assertIn(fragment, text)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m unittest skills/review-fix-loop/tests/test_review_loop_protocol.py -v
```

Expected: failures because the Claude source command does not exist and the Codex skill lacks the shared path/header contract.

- [ ] **Step 3: Write the minimal shared instructions**

Rewrite both instruction files around the exact same sections:

1. Role validation.
2. Shared path resolution.
3. Listener startup using the adjacent `scripts/review_loop_listener.py` for Codex or `review-fix-loop/review_loop_listener.py` for Claude.
4. Exact protocol header.
5. Ownership/state-machine rules.
6. Heartbeat verification before binding.
7. Review/fix round rules.
8. Listener shutdown and confirmed `STOPPED`.

Use `$review-fix-loop` only in the Codex invocation line and `/review-fix-loop` only in the Claude invocation line. Keep all protocol wording otherwise equivalent.

- [ ] **Step 4: Run the instruction tests and verify GREEN**

Run the Task 1 unittest command.

Expected: all `InstructionContractTests` pass.

- [ ] **Step 5: Commit the instruction contract**

```bash
git add skills/review-fix-loop/SKILL.md \
  skills/review-fix-loop/claude/review-fix-loop.md \
  skills/review-fix-loop/tests/test_review_loop_protocol.py
git commit -m "fix: unify review loop protocol contract"
```

### Task 2: Implement and verify the heartbeat listener

**Files:**
- Create: `skills/review-fix-loop/scripts/review_loop_listener.py`
- Modify: `skills/review-fix-loop/tests/test_review_loop_protocol.py`

**Interfaces:**
- Produces CLI:
  - `listen --role {reviewer,fixer} --watch ABS_PATH --state ABS_PATH --listener-id ID --interval SECONDS`
  - `verify --state ABS_PATH --role {reviewer,fixer} --watch ABS_PATH --max-age SECONDS`
- Produces JSON state fields: `schema_version`, `listener_id`, `role`, `watched_path`, `status`, `activated_at`, `heartbeat_at`, `initial_hash`, `initial_snapshot`, `dedupe_key`, and `pid`

- [ ] **Step 1: Add failing listener integration tests**

Add subprocess tests that:

- start `listen` against a temporary protocol file;
- wait conditionally for the state JSON;
- assert the initial empty snapshot and SHA-256 hash;
- run `verify` successfully with the expected role/path;
- reject wrong role and wrong path;
- change the watched protocol file twice with identical content and assert only one unique scan event;
- send `SIGINT`, wait for process exit, and assert `STOPPED`;
- replace `heartbeat_at` with an old timestamp and assert `verify` exits nonzero with `stale heartbeat`.

Use a polling helper with a deadline:

```python
def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("condition not met before timeout")
```

- [ ] **Step 2: Run the listener tests and verify RED**

Run:

```bash
python3 -m unittest \
  skills.review-fix-loop.tests.test_review_loop_protocol.ListenerCliTests -v
```

Expected: failure because `scripts/review_loop_listener.py` does not exist.

- [ ] **Step 3: Implement the minimal listener CLI**

Implement these focused functions with the exact signatures and return contracts:

- `utc_now() -> str`: return an aware UTC ISO-8601 timestamp.
- `atomic_write_json(path: Path, payload: dict) -> None`: write one complete JSON object with `os.replace`.
- `read_snapshot(path: Path) -> tuple[str, str, dict[str, str]]`: return content, SHA-256 digest, and parsed protocol fields.
- `dedupe_key(fields: dict[str, str], digest: str) -> tuple[str, str, str, str]`: return session, status, round, and digest.
- `listen(args: argparse.Namespace) -> int`: run until signalled, then record `STOPPED` and return 0.
- `verify(args: argparse.Namespace) -> int`: return 0 for valid live state and 1 with a stderr reason otherwise.
- `build_parser() -> argparse.ArgumentParser`: expose the exact `listen` and `verify` CLI defined above.
- `main() -> int`: parse arguments and dispatch the selected subcommand.

Implementation requirements:

- Resolve `watch` and `state` to absolute paths.
- Atomically write JSON through a same-directory temporary file and `os.replace`.
- Parse only the first occurrence of `SESSION_ID`, `STATUS`, and `ROUND`.
- Emit `ACTIVATED`, then route the immediate scan and later scans through one in-memory dedupe set.
- Refresh `heartbeat_at` every interval even when content is unchanged.
- Catch `SIGINT` and `SIGTERM`, write `STOPPED`, emit `STOPPED`, and exit zero.
- In `verify`, require schema version 1, exact role/path, `RUNNING`, and an aware ISO-8601 heartbeat no older than `--max-age`.
- Print one concise error to stderr and exit 1 for malformed, mismatched, stale, or stopped state.

- [ ] **Step 4: Run listener tests and verify GREEN**

Run the complete unittest file.

Expected: all instruction and listener tests pass with no warnings.

- [ ] **Step 5: Commit the listener**

```bash
git add skills/review-fix-loop/scripts/review_loop_listener.py \
  skills/review-fix-loop/tests/test_review_loop_protocol.py
git commit -m "feat: add verifiable review loop listener"
```

### Task 3: Synchronize local runtimes and validate distribution

**Files:**
- Modify: `/Users/reus/.codex/skills/review-fix-loop/SKILL.md`
- Create: `/Users/reus/.codex/skills/review-fix-loop/scripts/review_loop_listener.py`
- Modify: `/Users/reus/.claude/commands/review-fix-loop.md`
- Create: `/Users/reus/.claude/commands/review-fix-loop/review_loop_listener.py`
- Verify: `skills/review-fix-loop/agents/openai.yaml`

**Interfaces:**
- Consumes: the tested source files from Tasks 1 and 2
- Produces: byte-identical installed instructions/scripts where invocation syntax permits

- [ ] **Step 1: Add distribution assertions**

Extend the test module with a source-tree assertion that the Claude command points to `~/.claude/commands/review-fix-loop/review_loop_listener.py`, the Codex skill points to `scripts/review_loop_listener.py`, and both instruct the peer to run `verify`.

- [ ] **Step 2: Run the distribution assertions and verify RED**

Run the complete unittest file.

Expected: failure until the instruction references are exact.

- [ ] **Step 3: Make the source references exact and verify GREEN**

Update only the mismatched instruction references, then rerun the complete unittest file.

Expected: all tests pass.

- [ ] **Step 4: Copy tested sources into both local runtimes**

Copy:

```text
skills/review-fix-loop/SKILL.md
  -> /Users/reus/.codex/skills/review-fix-loop/SKILL.md
skills/review-fix-loop/scripts/review_loop_listener.py
  -> /Users/reus/.codex/skills/review-fix-loop/scripts/review_loop_listener.py
skills/review-fix-loop/claude/review-fix-loop.md
  -> /Users/reus/.claude/commands/review-fix-loop.md
skills/review-fix-loop/scripts/review_loop_listener.py
  -> /Users/reus/.claude/commands/review-fix-loop/review_loop_listener.py
```

- [ ] **Step 5: Run final verification**

Run:

```bash
python3 -m unittest skills/review-fix-loop/tests/test_review_loop_protocol.py -v
python3 /Users/reus/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/review-fix-loop
cmp skills/review-fix-loop/SKILL.md \
  /Users/reus/.codex/skills/review-fix-loop/SKILL.md
cmp skills/review-fix-loop/claude/review-fix-loop.md \
  /Users/reus/.claude/commands/review-fix-loop.md
cmp skills/review-fix-loop/scripts/review_loop_listener.py \
  /Users/reus/.codex/skills/review-fix-loop/scripts/review_loop_listener.py
cmp skills/review-fix-loop/scripts/review_loop_listener.py \
  /Users/reus/.claude/commands/review-fix-loop/review_loop_listener.py
```

Expected: unittest reports all tests passing, validator prints `Skill is valid!`, and every `cmp` exits 0.

- [ ] **Step 6: Commit the final source adjustments**

```bash
git add skills/review-fix-loop
git commit -m "test: cover review loop runtime distribution"
```
