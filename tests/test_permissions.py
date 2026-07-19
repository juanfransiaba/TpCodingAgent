import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.security.permissions import check_permissions, requires_approval


class PermissionTests(unittest.TestCase):
    def test_blocks_denied_paths_and_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            config = {
                "workspace": str(workspace),
                "permissions": {
                    "read": {"deny": [".env", "**/*.pem", "secrets/**"]},
                    "write": {"deny": ["data/raw/**"]},
                },
                "commands": {
                    "deny": ["rm -rf"],
                    "require_approval": ["npm install"],
                },
            }

            self.assertFalse(
                check_permissions("read_file", {"path": ".env"}, config)[0]
            )
            self.assertFalse(
                check_permissions("write_file", {"path": "data/raw/a.csv"}, config)[0]
            )
            self.assertFalse(
                check_permissions("run_command", {"command": "rm -rf data"}, config)[0]
            )

            outside_path = workspace.parent / "outside.txt"
            self.assertFalse(
                check_permissions("read_file", {"path": str(outside_path)}, config)[0]
            )
            self.assertTrue(
                requires_approval("run_command", {"command": "npm install"}, config)
            )


if __name__ == "__main__":
    unittest.main()
