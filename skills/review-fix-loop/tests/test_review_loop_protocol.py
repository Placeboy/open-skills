import datetime
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
CODEX_TEXT = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
CLAUDE_PATH = SKILL_DIR / "claude" / "review-fix-loop.md"
LISTENER_PATH = SKILL_DIR / "scripts" / "review_loop_listener.py"

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


def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("condition not met before timeout")


class ListenerScriptPresenceTests(unittest.TestCase):
    def test_listener_script_is_versioned(self):
        self.assertTrue(LISTENER_PATH.is_file())


@unittest.skipUnless(LISTENER_PATH.is_file(), "listener script not implemented")
class ListenerCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.watch_path = (root / "review.md").resolve()
        self.state_path = (root / "listener.json").resolve()
        self.output_path = root / "listener.jsonl"
        self.output_stream = self.output_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(LISTENER_PATH),
                "listen",
                "--role",
                "fixer",
                "--watch",
                str(self.watch_path),
                "--state",
                str(self.state_path),
                "--listener-id",
                "test-listener",
                "--interval",
                "0.05",
            ],
            stdout=self.output_stream,
            stderr=subprocess.PIPE,
            text=True,
        )
        wait_until(lambda: self._state_if_running())

    def tearDown(self):
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
        self.process.communicate(timeout=5)
        self.output_stream.close()
        self.temp_dir.cleanup()

    def _read_state(self):
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _state_if_running(self):
        state = self._read_state()
        return state if state and state.get("status") == "RUNNING" else None

    def _verify(self, role="fixer", watch_path=None, state_path=None):
        return subprocess.run(
            [
                sys.executable,
                str(LISTENER_PATH),
                "verify",
                "--state",
                str(state_path or self.state_path),
                "--role",
                role,
                "--watch",
                str(watch_path or self.watch_path),
                "--max-age",
                "5",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_initial_scan_and_live_verification(self):
        state = self._read_state()
        self.assertEqual("", state["initial_snapshot"])
        self.assertEqual(hashlib.sha256(b"").hexdigest(), state["initial_hash"])
        self.assertEqual(str(self.watch_path), state["watched_path"])
        self.assertEqual("fixer", state["role"])
        self.assertEqual(0, self._verify().returncode)

    def test_verify_rejects_wrong_role_and_path(self):
        wrong_role = self._verify(role="reviewer")
        self.assertEqual(1, wrong_role.returncode)
        self.assertIn("role mismatch", wrong_role.stderr)

        wrong_path = self._verify(watch_path=self.watch_path.with_name("feedback.md"))
        self.assertEqual(1, wrong_path.returncode)
        self.assertIn("watched path mismatch", wrong_path.stderr)

    def test_scan_deduplicates_identical_protocol_record(self):
        first = "SESSION_ID: s1\nSTATUS: REVIEWER_READY\nROUND: 0\n"
        first_hash = hashlib.sha256(first.encode()).hexdigest()
        second = "SESSION_ID: s1\nSTATUS: ISSUES_FOUND\nROUND: 0\n"
        second_hash = hashlib.sha256(second.encode()).hexdigest()

        self.watch_path.write_text(first, encoding="utf-8")
        wait_until(lambda: first_hash in self.output_path.read_text(encoding="utf-8"))
        previous_heartbeat = self._read_state()["heartbeat_at"]
        self.watch_path.write_text(first, encoding="utf-8")
        wait_until(lambda: self._read_state()["heartbeat_at"] != previous_heartbeat)
        self.watch_path.write_text(second, encoding="utf-8")
        wait_until(lambda: second_hash in self.output_path.read_text(encoding="utf-8"))

        self.process.send_signal(signal.SIGINT)
        self.process.wait(timeout=5)
        self.output_stream.flush()
        events = [
            json.loads(line)
            for line in self.output_path.read_text(encoding="utf-8").splitlines()
        ]
        scan_hashes = [
            event["content_hash"] for event in events if event["event"] == "SCAN"
        ]
        self.assertEqual(1, scan_hashes.count(first_hash))
        self.assertEqual(1, scan_hashes.count(second_hash))

    def test_signal_records_stopped(self):
        self.process.send_signal(signal.SIGINT)
        self.process.wait(timeout=5)
        wait_until(lambda: self._read_state()["status"] == "STOPPED")
        self.assertEqual("STOPPED", self._read_state()["status"])

    def test_verify_rejects_stale_heartbeat(self):
        stale_state = self._read_state()
        stale_state["heartbeat_at"] = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)
        ).isoformat()
        stale_path = self.state_path.with_name("stale.json")
        stale_path.write_text(json.dumps(stale_state), encoding="utf-8")

        result = self._verify(state_path=stale_path)
        self.assertEqual(1, result.returncode)
        self.assertIn("stale heartbeat", result.stderr)


if __name__ == "__main__":
    unittest.main()
