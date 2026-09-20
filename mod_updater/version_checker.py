"""Version comparison and update decision logic."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .inspector import LocalMod


class UpdateStatus:
    UP_TO_DATE = "Up to date"
    UPDATE_AVAILABLE = "Update available"
    NO_COMPATIBLE = "No compatible version"
    NOT_FOUND = "Not found on Modrinth"
    ERROR = "Check failed"


@dataclass
class ModUpdateInfo:
    """Detailed update state for a specific mod."""
    local_mod: LocalMod
    project_id: Optional[str] = None
    project_title: str = ""
    installed_version: str = "Unknown"
    target_version: Optional[str] = None
    target_file_url: Optional[str] = None
    target_filename: Optional[str] = None
    status: str = UpdateStatus.NOT_FOUND
    is_update_available: bool = False
    dependencies: list[str] = field(default_factory=list)


def parse_version_tuple(version_str: str) -> tuple[list[int], str]:
    """
    Parses a version string into a comparable tuple of integers and suffix.
    E.g. '0.161.0+26.3' -> ([0, 161, 0], '+26.3')
    """
    if not version_str:
        return ([], "")
    
    # Extract leading numbers separated by dots or dashes
    numbers: list[int] = []
    rest = version_str
    
    match = re.match(r"^(\d+(?:\.\d+)*)(.*)$", version_str.strip("vV"))
    if match:
        num_part, rest = match.groups()
        try:
            numbers = [int(n) for n in num_part.split(".")]
        except ValueError:
            numbers = []
    return (numbers, rest)


def is_candidate_newer(
    installed_version: Optional[str],
    candidate_version: Optional[str],
    installed_date: Optional[str] = None,
    candidate_date: Optional[str] = None
) -> bool:
    """
    Determines if candidate_version is newer than installed_version.
    Returns False if they are identical or candidate is older.
    """
    if not candidate_version:
        return False
    if not installed_version or installed_version.lower() == "unknown":
        return True
    
    if installed_version.strip() == candidate_version.strip():
        return False

    inst_nums, inst_rest = parse_version_tuple(installed_version)
    cand_nums, cand_rest = parse_version_tuple(candidate_version)

    if inst_nums and cand_nums:
        # Compare numeric prefixes
        max_len = max(len(inst_nums), len(cand_nums))
        inst_padded = inst_nums + [0] * (max_len - len(inst_nums))
        cand_padded = cand_nums + [0] * (max_len - len(cand_nums))

        if cand_padded > inst_padded:
            return True
        if cand_padded < inst_padded:
            return False

    # If numeric parts are equal, fall back to publish date comparison if available
    if installed_date and candidate_date:
        try:
            inst_dt = datetime.fromisoformat(installed_date.replace("Z", "+00:00"))
            cand_dt = datetime.fromisoformat(candidate_date.replace("Z", "+00:00"))
            return cand_dt > inst_dt
        except Exception:
            pass

    # If different strings and no other distinction, consider candidate as update
    return installed_version.strip() != candidate_version.strip()


def select_best_version(
    versions: list[dict[str, Any]],
    game_version: str,
    loader: str
) -> Optional[dict[str, Any]]:
    """
    Filters versions by game_version and loader, preferring release channel.
    Returns the newest compatible version object.
    """
    candidates = []
    for v in versions:
        g_vers = v.get("game_versions", [])
        loaders = [l.lower() for l in v.get("loaders", [])]
        
        # Check game version match
        if game_version not in g_vers:
            continue
            
        # Check loader match
        # If loader is fabric, quilt is often also accepted or vice-versa
        loader_lower = loader.lower()
        if loader_lower in loaders:
            candidates.append(v)
        elif loader_lower == "fabric" and "quilt" in loaders:
            candidates.append(v)
        elif loader_lower == "quilt" and "fabric" in loaders:
            candidates.append(v)

    if not candidates:
        return None

    # Sort/filter: prioritize 'release' versions, then 'beta', then 'alpha'
    releases = [c for c in candidates if c.get("version_type") == "release"]
    if releases:
        return releases[0]
    betas = [c for c in candidates if c.get("version_type") == "beta"]
    if betas:
        return betas[0]
    return candidates[0]
