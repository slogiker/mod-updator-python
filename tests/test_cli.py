import argparse
import unittest
from pathlib import Path

from mod_updater.cli import run_cli


class TestCLI(unittest.TestCase):
    def test_default_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--path", default=".mods")
        parser.add_argument("-v", "--version")
        parser.add_argument("-l", "--loader")
        parser.add_argument("-c", "--check", action="store_true")
        args = parser.parse_args([])
        self.assertEqual(args.path, ".mods")
        self.assertFalse(args.check)

    def test_custom_path_flag(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--path", default=".mods")
        args = parser.parse_args(["-p", "/custom/mods/folder"])
        self.assertEqual(args.path, "/custom/mods/folder")


if __name__ == "__main__":
    unittest.main()
