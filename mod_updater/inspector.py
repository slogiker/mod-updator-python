"""Local JAR inspection and metadata extraction."""

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

MOD_ID_OVERRIDES: dict[str, str] = {
    "voicechat": "simple-voice-chat",
    "voicechat-fabric": "simple-voice-chat",
    "jei": "jei",
    "rei": "roughly-enough-items",
    "emi": "emi",
}


@dataclass
class LocalMod:
    """Represents a locally installed Minecraft mod JAR file."""
    file_path: Path
    filename: str
    sha1: str
    mod_id: Optional[str] = None
    mod_name: Optional[str] = None
    installed_version: Optional[str] = None
    mc_version: Optional[str] = None
    loaders: list[str] = field(default_factory=list)


def compute_file_sha1(file_path: Path) -> str:
    """Computes the SHA1 hash of a file efficiently in 64KB chunks."""
    hasher = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _parse_fabric_meta(jar: zipfile.ZipFile) -> tuple[Optional[str], Optional[str], Optional[str], list[str]]:
    """Extracts mod info from fabric.mod.json."""
    try:
        with jar.open("fabric.mod.json") as f:
            data = json.load(f)
            mod_id = data.get("custom", {}).get("modrinth") or data.get("id")
            name = data.get("name") or mod_id
            version = data.get("version")
            return mod_id, name, version, ["fabric"]
    except Exception:
        return None, None, None, []


def _parse_quilt_meta(jar: zipfile.ZipFile) -> tuple[Optional[str], Optional[str], Optional[str], list[str]]:
    """Extracts mod info from quilt.mod.json."""
    try:
        with jar.open("quilt.mod.json") as f:
            data = json.load(f)
            q_loader = data.get("quilt_loader", {})
            mod_id = q_loader.get("id")
            version = q_loader.get("version")
            metadata = q_loader.get("metadata", {})
            name = metadata.get("name") or mod_id
            return mod_id, name, version, ["quilt", "fabric"]
    except Exception:
        return None, None, None, []


def _parse_toml_simple(content: str) -> dict[str, str]:
    """Lightweight regex-based parser for basic TOML mod files (mods.toml)."""
    result: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"\'')
            if key in ("modId", "version", "displayName") and key not in result:
                result[key] = val
    return result


def _parse_forge_meta(jar: zipfile.ZipFile) -> tuple[Optional[str], Optional[str], Optional[str], list[str]]:
    """Extracts mod info from META-INF/mods.toml or META-INF/neoforge.mods.toml."""
    loaders = []
    names = jar.namelist()
    target_files = []
    if "META-INF/neoforge.mods.toml" in names:
        target_files.append("META-INF/neoforge.mods.toml")
        loaders.append("neoforge")
    if "META-INF/mods.toml" in names:
        target_files.append("META-INF/mods.toml")
        loaders.append("forge")

    for file_path in target_files:
        try:
            with jar.open(file_path) as f:
                content = f.read().decode("utf-8", errors="ignore")
                parsed = _parse_toml_simple(content)
                mod_id = parsed.get("modId")
                name = parsed.get("displayName") or mod_id
                version = parsed.get("version")
                if version == "${file.jarVersion}":
                    version = None
                if mod_id:
                    return mod_id, name, version, loaders
        except Exception:
            continue
    return None, None, None, loaders


def _fallback_from_filename(filename: str) -> tuple[str, Optional[str]]:
    """Heuristic fallback to extract mod identifier and version from filename."""
    base = filename
    if base.lower().endswith(".jar"):
        base = base[:-4]

    # Remove known loader tags
    clean_name = re.sub(r"[-_.]?(fabric|forge|quilt|neoforge)[-_.]?", "-", base, flags=re.IGNORECASE)
    clean_name = clean_name.strip("-_.")

    # Strip Minecraft version tags like -1.21.1- or -mc1.20.4- if embedded between name and mod version
    mc_ver_match = re.search(r"[-_.](?:mc)?1\.\d+(?:\.\d+)?[-_.]", clean_name, flags=re.IGNORECASE)
    if mc_ver_match:
        # e.g., jei-1.21.1-19.1.0 -> jei-19.1.0
        clean_name = clean_name[:mc_ver_match.start()] + "-" + clean_name[mc_ver_match.end():]
        clean_name = clean_name.strip("-_.")

    # Try to separate mod name from version pattern (e.g., sodium-0.5.8+mc1.20.4 -> sodium and 0.5.8+mc1.20.4)
    match = re.search(r"^(.*?)[-_](\d+[\.\d\w\+\-]+)$", clean_name)
    if match:
        mod_slug = match.group(1).strip("-_.").lower()
        version = match.group(2).strip("-_.")
        return mod_slug, version

    # Fallback to splitting at first digit
    parts = re.split(r"[-_.]?\d", clean_name, 1)
    mod_slug = parts[0].strip("-_.").lower() if parts else clean_name.lower()
    return mod_slug, None


def inspect_jar(file_path: Path) -> LocalMod:
    """Inspects a JAR file and returns a LocalMod with detected metadata and SHA1."""
    filename = file_path.name
    sha1 = compute_file_sha1(file_path)

    mod_id: Optional[str] = None
    mod_name: Optional[str] = None
    version: Optional[str] = None
    loaders: list[str] = []

    try:
        with zipfile.ZipFile(file_path, "r") as jar:
            namelist = jar.namelist()
            if "fabric.mod.json" in namelist:
                mod_id, mod_name, version, loaders = _parse_fabric_meta(jar)
            elif "quilt.mod.json" in namelist:
                mod_id, mod_name, version, loaders = _parse_quilt_meta(jar)
            elif "META-INF/neoforge.mods.toml" in namelist or "META-INF/mods.toml" in namelist:
                mod_id, mod_name, version, loaders = _parse_forge_meta(jar)
    except (zipfile.BadZipFile, OSError):
        pass

    fallback_slug, fallback_ver = _fallback_from_filename(filename)
    if not mod_id:
        mod_id = fallback_slug
    if not mod_name:
        mod_name = mod_id.replace("-", " ").title() if mod_id else filename
    if not version and fallback_ver:
        version = fallback_ver

    # Apply override mapping
    if mod_id and mod_id in MOD_ID_OVERRIDES:
        mod_id = MOD_ID_OVERRIDES[mod_id]

    return LocalMod(
        file_path=file_path,
        filename=filename,
        sha1=sha1,
        mod_id=mod_id,
        mod_name=mod_name,
        installed_version=version,
        loaders=loaders,
    )
