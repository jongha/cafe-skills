"""Installation contracts: a link to this clone, safe re-runs, and existing-file protection."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cafe_install", ROOT / "scripts/install.py")
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


def run_installer(*args, cwd=None):
    return subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), *args], cwd=cwd, capture_output=True, text=True)


class InstallTests(unittest.TestCase):
    def test_every_host_links_to_this_clone_and_runs(self):
        with tempfile.TemporaryDirectory(prefix="cafe install ") as temporary:
            for host in INSTALLER.HOST_DIRS:
                with self.subTest(host=host):
                    parent = Path(temporary) / host / "skills"
                    result = run_installer(host, "--skills-dir", str(parent), cwd=temporary)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    destination = parent / "order"
                    self.assertTrue(destination.is_symlink())
                    self.assertEqual(destination.resolve(), INSTALLER.SOURCE)
                    run = subprocess.run(
                        [sys.executable, str(destination / "scripts/cafe.py"), "self-test"],
                        cwd=temporary, capture_output=True, text=True,
                    )
                    self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_running_again_keeps_the_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = run_installer("codex", "--skills-dir", temporary)
            second = run_installer("codex", "--skills-dir", temporary)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Already linked", second.stdout)
            self.assertEqual((Path(temporary) / "order").resolve(), INSTALLER.SOURCE)

    def test_existing_folder_is_not_changed(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "order"
            destination.mkdir()
            (destination / "SKILL.md").write_text("my own skill", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                INSTALLER.install(Path(temporary))
            self.assertFalse(destination.is_symlink())
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "my own skill")

    def test_broken_or_foreign_symlink_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "order"
            missing = Path(temporary) / "missing"
            destination.symlink_to(missing, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                INSTALLER.install(Path(temporary))
            self.assertEqual(destination.readlink(), missing)


if __name__ == "__main__":
    unittest.main()
