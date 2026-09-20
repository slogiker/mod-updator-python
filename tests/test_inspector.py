import io
import json
import zipfile
import unittest
from pathlib import Path
import tempfile

from mod_updater.inspector import (
    compute_file_sha1,
    inspect_jar,
    _fallback_from_filename,
    MOD_ID_OVERRIDES,
)


class TestInspector(unittest.TestCase):
    def test_compute_sha1(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"MinecraftModContent")
            temp_path = Path(tf.name)
        try:
            sha1 = compute_file_sha1(temp_path)
            # sha1 of b"MinecraftModContent"
            self.assertEqual(sha1, "497c270dfd8498c5381cfa5fedc60e5aefa9ed27")
        finally:
            temp_path.unlink()

    def test_fallback_from_filename(self):
        slug, ver = _fallback_from_filename("sodium-fabric-0.5.8+mc1.20.4.jar")
        self.assertEqual(slug, "sodium")
        self.assertEqual(ver, "0.5.8+mc1.20.4")

        slug2, ver2 = _fallback_from_filename("jei-1.21.1-forge-19.1.0.jar")
        self.assertEqual(slug2, "jei")
        self.assertEqual(ver2, "19.1.0")

    def test_inspect_fabric_jar(self):
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tf:
            temp_path = Path(tf.name)
        
        try:
            with zipfile.ZipFile(temp_path, "w") as zf:
                meta = {
                    "id": "fabric-api",
                    "name": "Fabric API",
                    "version": "0.100.0",
                    "custom": {"modrinth": "fabric-api"}
                }
                zf.writestr("fabric.mod.json", json.dumps(meta))

            mod = inspect_jar(temp_path)
            self.assertEqual(mod.mod_id, "fabric-api")
            self.assertEqual(mod.mod_name, "Fabric API")
            self.assertEqual(mod.installed_version, "0.100.0")
            self.assertIn("fabric", mod.loaders)
        finally:
            temp_path.unlink()

    def test_inspect_forge_jar(self):
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tf:
            temp_path = Path(tf.name)

        try:
            with zipfile.ZipFile(temp_path, "w") as zf:
                toml_content = """
                [[mods]]
                modId = "testmod"
                version = "1.2.3"
                displayName = "Test Forge Mod"
                """
                zf.writestr("META-INF/mods.toml", toml_content)

            mod = inspect_jar(temp_path)
            self.assertEqual(mod.mod_id, "testmod")
            self.assertEqual(mod.mod_name, "Test Forge Mod")
            self.assertEqual(mod.installed_version, "1.2.3")
            self.assertIn("forge", mod.loaders)
        finally:
            temp_path.unlink()

    def test_override_mapping(self):
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tf:
            temp_path = Path(tf.name)

        try:
            with zipfile.ZipFile(temp_path, "w") as zf:
                meta = {"id": "voicechat", "version": "2.4.0"}
                zf.writestr("fabric.mod.json", json.dumps(meta))

            mod = inspect_jar(temp_path)
            self.assertEqual(mod.mod_id, "simple-voice-chat")
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
