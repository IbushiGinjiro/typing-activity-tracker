import os
import sys
import unittest
from unittest.mock import patch

from app import autostart


class ShortcutPathTest(unittest.TestCase):
    def test_shortcut_path_uses_appdata_startup_folder(self):
        with patch.dict(os.environ, {"APPDATA": r"C:\Users\test\AppData\Roaming"}):
            path = autostart.shortcut_path()
        self.assertTrue(path.endswith(os.path.join("Startup", autostart.SHORTCUT_NAME)))
        self.assertTrue(path.startswith(r"C:\Users\test\AppData\Roaming"))

    def test_is_registered_reflects_file_existence(self):
        with patch.dict(os.environ, {"APPDATA": r"C:\Users\test\AppData\Roaming"}):
            with patch("os.path.exists", return_value=True):
                self.assertTrue(autostart.is_registered())
            with patch("os.path.exists", return_value=False):
                self.assertFalse(autostart.is_registered())


class LaunchTargetTest(unittest.TestCase):
    def test_frozen_targets_the_exe_itself(self):
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "executable", r"C:\dist\typing-activity-tracker.exe"):
                target, arguments, working_dir = autostart._launch_target()
        self.assertEqual(target, r"C:\dist\typing-activity-tracker.exe")
        self.assertEqual(arguments, "")
        self.assertEqual(working_dir, r"C:\dist")

    def test_non_frozen_targets_pythonw_with_run_py(self):
        self.assertFalse(getattr(sys, "frozen", False))
        with patch("os.path.exists", return_value=True):
            target, arguments, working_dir = autostart._launch_target()
        self.assertTrue(target.endswith("pythonw.exe"))
        self.assertIn("run.py", arguments)
        self.assertTrue(working_dir.endswith("typing-activity-tracker"))

    def test_non_frozen_falls_back_to_current_interpreter_if_no_pythonw(self):
        self.assertFalse(getattr(sys, "frozen", False))
        with patch("os.path.exists", return_value=False):
            target, _arguments, _working_dir = autostart._launch_target()
        self.assertEqual(target, sys.executable)


if __name__ == "__main__":
    unittest.main()
