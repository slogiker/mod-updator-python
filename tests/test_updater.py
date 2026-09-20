import tempfile
import unittest
import zipfile
import json
from pathlib import Path

from mod_updater.updater import scan_local_mods, create_backup_dir
from mod_updater.inspector import LocalMod
from mod_updater.version_checker import ModUpdateInfo, UpdateStatus


class TestUpdater(unittest.TestCase):
    def test_scan_local_mods_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            mods = scan_local_mods(Path(td))
            self.assertEqual(mods, [])

    def test_scan_local_mods_with_jars(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            jar_file = td_path / "testmod-1.0.jar"
            with zipfile.ZipFile(jar_file, "w") as zf:
                meta = {"id": "testmod", "version": "1.0"}
                zf.writestr("fabric.mod.json", json.dumps(meta))

            # Non-jar file should be ignored
            (td_path / "readme.txt").write_text("hello")

            mods = scan_local_mods(td_path)
            self.assertEqual(len(mods), 1)
            self.assertEqual(mods[0].mod_id, "testmod")
            self.assertEqual(mods[0].installed_version, "1.0")

    def test_create_backup_dir(self):
        with tempfile.TemporaryDirectory() as td:
            mods_dir = Path(td) / ".mods"
            mods_dir.mkdir()
            b1 = create_backup_dir(mods_dir)
            self.assertTrue(b1.exists())
            self.assertEqual(b1.name, "old mods")

            # Second call should create unique backup directory
            b2 = create_backup_dir(mods_dir)
            self.assertTrue(b2.exists())
            self.assertEqual(b2.name, "old mods-1")


if __name__ == "__main__":
    unittest.main()
