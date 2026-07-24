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


if __name__ == "__main__":
    unittest.main()
