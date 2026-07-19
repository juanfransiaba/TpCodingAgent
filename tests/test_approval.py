import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.security.approval import is_approved


class ApprovalTests(unittest.TestCase):
    def test_accepts_common_spanish_and_english_approvals(self):
        for response in ("s", "si", "sí", "SÍ", "y", "yes", "ok", "dale"):
            self.assertTrue(is_approved(response))

    def test_rejects_negative_or_empty_responses(self):
        for response in ("", "n", "no", "cancelar"):
            self.assertFalse(is_approved(response))


if __name__ == "__main__":
    unittest.main()
