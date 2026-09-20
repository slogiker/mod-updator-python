"""Core updater engine handling mod scanning, update checks, backups, and downloads."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .api import ModrinthClient
from .inspector import LocalMod, inspect_jar
from .ui import Colors, color
from .version_checker import (
    ModUpdateInfo,
    UpdateStatus,
    is_candidate_newer,
    select_best_version,
)


def scan_local_mods(mods_dir: Path) -> list[LocalMod]:
    """Scans all .jar files in the specified mods directory."""
    if not mods_dir.exists() or not mods_dir.is_dir():
        return []
    
    jar_files = sorted(mods_dir.glob("*.jar"))
    mods = []
    for jar in jar_files:
        try:
            mod = inspect_jar(jar)
            mods.append(mod)
        except Exception as err:
            print(color(f"  [WARN] Failed to inspect {jar.name}: {err}", Colors.YELLOW))
    return mods


def check_for_updates(
    local_mods: list[LocalMod],
    game_version: str,
    loader: str,
    client: Optional[ModrinthClient] = None
) -> list[ModUpdateInfo]:
    """
    Checks Modrinth for updates for all local mods.
    Leverages batch hash checking first, followed by metadata and search fallbacks.
    """
    if client is None:
        client = ModrinthClient()

    results: list[ModUpdateInfo] = []
    hashes = [m.sha1 for m in local_mods if m.sha1]

    # 1. Fast Batch Hash Update Check
    batch_updates: dict[str, dict] = {}
    batch_installed_info: dict[str, dict] = {}
    if hashes:
        batch_updates = client.get_updates_by_hashes(
            hashes=hashes,
            loaders=[loader],
            game_versions=[game_version]
        )
        batch_installed_info = client.get_version_files_by_hashes(hashes=hashes)

    processed_mods: set[str] = set()

    for mod in local_mods:
        info = ModUpdateInfo(
            local_mod=mod,
            project_title=mod.mod_name or mod.filename,
            installed_version=mod.installed_version or "Unknown",
        )

        # Check if batch hash matched installed file metadata
        inst_meta = batch_installed_info.get(mod.sha1, {})
        if inst_meta:
            info.project_id = inst_meta.get("project_id")
            if not mod.installed_version or mod.installed_version == "Unknown":
                info.installed_version = inst_meta.get("version_number", "Unknown")

        # Check if batch update found a version for this hash
        cand_update = batch_updates.get(mod.sha1)
        if cand_update:
            info.project_id = cand_update.get("project_id")
            cand_ver = cand_update.get("version_number")
            info.target_version = cand_ver
            cand_files = cand_update.get("files", [])
            primary_file = next((f for f in cand_files if f.get("primary")), cand_files[0] if cand_files else None)
            
            if primary_file:
                info.target_file_url = primary_file.get("url")
                info.target_filename = primary_file.get("filename")
                cand_hash = primary_file.get("hashes", {}).get("sha1")

                # If candidate file is the exact same file hash, it's already up to date!
                if cand_hash and cand_hash.lower() == mod.sha1.lower():
                    info.status = UpdateStatus.UP_TO_DATE
                    info.is_update_available = False
                elif info.installed_version and cand_ver and info.installed_version.strip() == cand_ver.strip():
                    info.status = UpdateStatus.UP_TO_DATE
                    info.is_update_available = False
                else:
                    inst_date = inst_meta.get("date_published")
                    cand_date = cand_update.get("date_published")
                    if is_candidate_newer(info.installed_version, cand_ver, inst_date, cand_date):
                        info.status = UpdateStatus.UPDATE_AVAILABLE
                        info.is_update_available = True
                    else:
                        info.status = UpdateStatus.UP_TO_DATE
                        info.is_update_available = False

            # Collect dependencies
            for dep in cand_update.get("dependencies", []):
                if dep.get("dependency_type") == "required" and dep.get("project_id"):
                    info.dependencies.append(dep["project_id"])

            results.append(info)
            processed_mods.add(mod.filename)
            continue

        # 2. Fallback to Project ID / Slug lookup
        project = None
        if mod.mod_id:
            project = client.get_project(mod.mod_id)
        if not project and mod.mod_name:
            project = client.search_project(mod.mod_name)

        if not project:
            info.status = UpdateStatus.NOT_FOUND
            results.append(info)
            processed_mods.add(mod.filename)
            continue

        proj_id = project.get("id") or project.get("slug")
        info.project_id = proj_id
        info.project_title = project.get("title") or info.project_title

        versions = client.get_project_versions(proj_id, loaders=[loader], game_versions=[game_version])
        best = select_best_version(versions, game_version, loader)

        if not best:
            info.status = UpdateStatus.NO_COMPATIBLE
            results.append(info)
            processed_mods.add(mod.filename)
            continue

        best_ver = best.get("version_number")
        info.target_version = best_ver
        best_files = best.get("files", [])
        primary_file = next((f for f in best_files if f.get("primary")), best_files[0] if best_files else None)

        if primary_file:
            info.target_file_url = primary_file.get("url")
            info.target_filename = primary_file.get("filename")
            best_hash = primary_file.get("hashes", {}).get("sha1")

            if best_hash and best_hash.lower() == mod.sha1.lower():
                info.status = UpdateStatus.UP_TO_DATE
                info.is_update_available = False
            elif info.installed_version and best_ver and info.installed_version.strip() == best_ver.strip():
                info.status = UpdateStatus.UP_TO_DATE
                info.is_update_available = False
            else:
                inst_date = inst_meta.get("date_published")
                cand_date = best.get("date_published")
                if is_candidate_newer(info.installed_version, best_ver, inst_date, cand_date):
                    info.status = UpdateStatus.UPDATE_AVAILABLE
                    info.is_update_available = True
                else:
                    info.status = UpdateStatus.UP_TO_DATE
                    info.is_update_available = False

        for dep in best.get("dependencies", []):
            if dep.get("dependency_type") == "required" and dep.get("project_id"):
                info.dependencies.append(dep["project_id"])

        results.append(info)
        processed_mods.add(mod.filename)

    return results


def create_backup_dir(mods_dir: Path) -> Path:
    """Creates a unique backup directory adjacent to mods directory."""
    parent = mods_dir.parent
    base_name = "old mods"
    backup_path = parent / base_name
    counter = 1
    while backup_path.exists():
        backup_path = parent / f"{base_name}-{counter}"
        counter += 1
    backup_path.mkdir(parents=True, exist_ok=True)
    return backup_path


def apply_mod_updates(
    updates: list[ModUpdateInfo],
    mods_dir: Path,
    backup: bool = True,
    client: Optional[ModrinthClient] = None,
    download_dependencies: bool = True,
    game_version: Optional[str] = None,
    loader: Optional[str] = None
) -> dict[str, int]:
    """
    Applies updates by downloading new versions and replacing old JARs safely.
    Creates backups of replaced files.
    """
    if client is None:
        client = ModrinthClient()

    to_update = [u for u in updates if u.is_update_available and u.target_file_url and u.target_filename]
    if not to_update:
        return {"updated": 0, "errors": 0, "dependencies": 0}

    backup_dir: Optional[Path] = None
    if backup:
        backup_dir = create_backup_dir(mods_dir)
        print(f"\n{color('[BACKUP]', Colors.BRIGHT_CYAN)} Created backup folder: {backup_dir}")

    updated_count = 0
    error_count = 0
    installed_project_ids = {u.project_id for u in updates if u.project_id}
    all_dep_ids: set[str] = set()

    for item in to_update:
        dest_path = mods_dir / item.target_filename
        old_path = item.local_mod.file_path
        print(f"\n>> Updating: {color(item.project_title, Colors.BOLD)} -> {color(item.target_version or '', Colors.GREEN)}")

        # Backup old file
        if backup_dir and old_path.exists():
            backup_dest = backup_dir / old_path.name
            shutil.copy2(old_path, backup_dest)
            print(f"   Backed up: {old_path.name}")

        # Download new file
        try:
            print(f"   Downloading {item.target_filename}...")
            client.download_file(item.target_file_url, dest_path)
            print(f"   {color('Saved', Colors.BRIGHT_GREEN)} -> {dest_path.name}")
            updated_count += 1

            # Remove old jar if different name
            if old_path.exists() and old_path.resolve() != dest_path.resolve():
                old_path.unlink()
                print(f"   Removed old file: {old_path.name}")

            for dep_id in item.dependencies:
                if dep_id not in installed_project_ids:
                    all_dep_ids.add(dep_id)

        except Exception as err:
            print(f"   {color('[ERROR]', Colors.BRIGHT_RED)} Failed to download {item.target_filename}: {err}")
            error_count += 1

    # Handle dependencies
    dep_count = 0
    if download_dependencies and all_dep_ids and game_version and loader:
        print(f"\n{color('[DEPENDENCIES]', Colors.BRIGHT_CYAN)} Checking required dependencies...")
        for dep_id in all_dep_ids:
            proj = client.get_project(dep_id)
            if not proj:
                continue
            dep_title = proj.get("title", dep_id)
            versions = client.get_project_versions(dep_id, loaders=[loader], game_versions=[game_version])
            best = select_best_version(versions, game_version, loader)
            if not best:
                print(f"   {color('[WARN]', Colors.YELLOW)} No compatible version for dependency: {dep_title}")
                continue

            primary_file = next((f for f in best.get("files", []) if f.get("primary")), None)
            if primary_file and primary_file.get("url"):
                dep_filename = primary_file.get("filename")
                dep_dest = mods_dir / dep_filename
                if not dep_dest.exists():
                    print(f"   Downloading required dependency: {color(dep_title, Colors.BOLD)} ({dep_filename})...")
                    try:
                        client.download_file(primary_file["url"], dep_dest)
                        print(f"   {color('Installed dependency', Colors.BRIGHT_GREEN)}: {dep_filename}")
                        dep_count += 1
                    except Exception as err:
                        print(f"   {color('[ERROR]', Colors.BRIGHT_RED)} Failed dependency {dep_title}: {err}")

    return {"updated": updated_count, "errors": error_count, "dependencies": dep_count}
