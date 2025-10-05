import os
import re
import shutil
import requests
import zipfile
import json
import traceback
import argparse
from collections import deque
from datetime import datetime

# === CONFIG ===
MODRINTH_API = "https://api.modrinth.com/v2"

MOD_ID_OVERRIDES = {
    "voicechat": "simple-voice-chat",
    "voicechat-fabric": "simple-voice-chat",
}

# Auto-detect .minecraft directory
try:
    MINECRAFT_DIR = os.path.join(os.environ["APPDATA"], ".minecraft")
except KeyError:
    MINECRAFT_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "minecraft")
    if not os.path.exists(MINECRAFT_DIR):
        MINECRAFT_DIR = os.path.join(os.path.expanduser("~"), ".minecraft")
MODS_DIR = os.path.join(MINECRAFT_DIR, "mods")

# === FUNCTIONS ===

def log_crash(exception):
    """Logs unhandled exceptions to a debug.txt file."""
    log_file = "debug.txt"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"--- CRASH LOG: {now} ---\n")
        f.write(traceback.format_exc())
        f.write("\n--- END OF LOG ---\n\n")
    print(f"\n[CRITICAL] An unexpected error occurred! A crash report has been saved to '{log_file}'.")

def get_project_from_id(project_id):
    """Fetches a project's details using its slug or ID."""
    if not project_id: return None
    url = f"{MODRINTH_API}/project/{project_id}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None

def search_project_by_name(query):
    """Searches for a project by name, returning the best match."""
    if not query: return None
    url = f"{MODRINTH_API}/search"
    params = {"query": query, "limit": 1}
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        return hits[0] if hits else None
    except requests.RequestException:
        return None

def find_modrinth_project(jar_path, filename):
    """A robust, multi-step process to find a mod's project page."""
    mod_id = None
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            meta_path = 'fabric.mod.json'
            if meta_path in jar.namelist():
                with jar.open(meta_path) as meta_file:
                    data = json.load(meta_file)
                    mod_id = data.get('custom', {}).get('modrinth') or data.get('id')
    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError, FileNotFoundError):
        pass

    if not mod_id:
        mod_id = re.sub(r'[-_.]?(fabric|forge|quilt|neo\w*)[-_.]?', '', filename.lower().removesuffix(".jar"))
        mod_id = re.split(r'[-_.]?\d', mod_id, 1)[0].strip("-_.")

    if mod_id in MOD_ID_OVERRIDES:
        mod_id = MOD_ID_OVERRIDES[mod_id]

    project = get_project_from_id(mod_id)
    if project: return project
    return search_project_by_name(mod_id)

def get_mod_versions(project_id):
    """Gets all available versions for a project."""
    url = f"{MODRINTH_API}/project/{project_id}/version"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def filter_versions(versions, game_version, loader):
    """Filters versions, prioritizing 'release' type."""
    candidates = [v for v in versions if game_version in v.get("game_versions", []) and loader in v.get("loaders", [])]
    if not candidates: return []
    release_versions = [v for v in candidates if v.get("version_type") == "release"]
    return release_versions if release_versions else candidates

def download_version(version_info, dry_run=False):
    """Downloads the primary file for a given version object, or simulates it."""
    primary_file = next((f for f in version_info.get("files", []) if f.get("primary")), None)
    if not primary_file:
        print("  [ERROR] No primary file found for this version.")
        return
    
    fname = primary_file.get("filename")
    if dry_run:
        print(f"  [DRY RUN] Would download {fname}")
        return

    outpath = os.path.join(MODS_DIR, fname)
    print(f"  [DOWNLOAD] Starting download of {fname}...")
    with requests.get(primary_file.get("url"), stream=True) as r:
        r.raise_for_status()
        with open(outpath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"  [SAVED] Successfully saved to {outpath}")

# === MAIN ===

def main():
    parser = argparse.ArgumentParser(
        description="A command-line tool to update Minecraft mods from Modrinth.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--test', action='store_true', help="Run in test mode without downloading or deleting any files.")
    parser.add_argument('-v', '--version', type=str, help="Specify the Minecraft version (e.g., -v 1.21.1).")
    parser.add_argument('-p', '--platform', type=str, help="Specify the mod loader (e.g., -p fabric).")
    args = parser.parse_args()
    DRY_RUN = args.test

    print("=========================================")
    print("||                                     ||")
    print("||      MINECRAFT MOD UPDATER          ||")
    print("||                                     ||")
    print("=========================================")
    
    if DRY_RUN:
        print("\n[INFO] DRY RUN enabled. No files will be changed.")

    if not os.path.exists(MODS_DIR): os.makedirs(MODS_DIR)
    local_mods = [f for f in os.listdir(MODS_DIR) if f.endswith(".jar")]
    
    if not local_mods:
        print(f"\n[INFO] No mods found in your mods directory.")
        return

    print(f"\n[INFO] Found {len(local_mods)} mods in your mods folder.")
    
    game_version = args.version or input(">> Enter desired Minecraft version (e.g. 1.21.1): ").strip()
    loader = (args.platform or input(">> Enter loader (fabric / forge / quilt): ").strip()).lower()
    
    if args.version: print(f"[INFO] Using provided Minecraft version: {game_version}")
    if args.platform: print(f"[INFO] Using provided loader: {loader}")

    backup_dir = MODS_DIR
    if not DRY_RUN:
        base_backup_dir = "old mods"
        backup_dir = base_backup_dir
        if os.path.exists(backup_dir):
            i = 1
            while os.path.exists(f"{base_backup_dir}-{i}"): i += 1
            backup_dir = f"{base_backup_dir}-{i}"
        
        print(f"\n[INFO] Backing up {len(local_mods)} mods to '{backup_dir}'...")
        shutil.copytree(MODS_DIR, backup_dir)
        for filename in local_mods:
            os.remove(os.path.join(MODS_DIR, filename))

    summary, mods_to_process, processed_or_queued = {}, deque(), set()

    print("\n[ Step 1: Analyzing Your Existing Mods ]")
    for filename in local_mods:
        jar_path = os.path.join(backup_dir, filename)
        project = find_modrinth_project(jar_path, filename)
        
        if project and project.get("slug"):
            slug, title = project["slug"], project.get("title")
            if slug not in processed_or_queued:
                print(f"  [QUEUED] {title}")
                mods_to_process.append(slug)
                processed_or_queued.add(slug)
                summary[slug] = {"title": title, "status": "Queued", "version": "---"}
        else:
            summary[filename] = {"title": filename, "status": "Not Found", "version": "---"}
            print(f"  [UNKNOWN] Could not identify '{filename}' on Modrinth.")

    print("\n[ Step 2: Checking for Updates and Dependencies ]")
    while mods_to_process:
        slug = mods_to_process.popleft()
        project_title = summary[slug]["title"]
        print(f"\n>> Processing: {project_title}")

        versions = get_mod_versions(slug)
        candidates = filter_versions(versions, game_version, loader)

        if not candidates:
            print("  [INFO] No compatible version found.")
            summary[slug].update({"status": "No Update", "version": "N/A"})
            continue
        
        latest = candidates[0]
        ver_num, ver_type = latest.get("version_number"), latest.get("version_type")
        print(f"  [FOUND] Best version: {ver_num} (Type: {ver_type})")
        download_version(latest, dry_run=DRY_RUN)
        summary[slug].update({"status": "Would Update" if DRY_RUN else "Updated", "version": ver_num})

        for dep in latest.get("dependencies", []):
            if dep.get("dependency_type") == "required":
                dep_slug = dep.get("project_id")
                if dep_slug and dep_slug not in processed_or_queued:
                    dep_details = get_project_from_id(dep_slug)
                    if dep_details:
                        dep_title = dep_details.get("title")
                        print(f"  [DEPENDENCY] Found required mod: '{dep_title}'. Adding to queue.")
                        mods_to_process.append(dep_slug)
                        processed_or_queued.add(dep_slug)
                        summary[dep_slug] = {"title": dep_title, "status": "Queued", "version": "---"}

    print("\n\n+==================================================================+")
    print("|                         UPDATE SUMMARY                         |")
    print("+------------------------------------+-----------------+-------------+")
    print(f"| {'Mod Name':<34} | {'Status':<15} | {'Version':<11} |")
    print("+------------------------------------+-----------------+-------------+")
    for item in summary.values():
        print(f"| {item['title']:<34.34} | {item['status']:<15} | {item['version']:<11.11} |")
    print("+------------------------------------+-----------------+-------------+")

    if not DRY_RUN:
        print(f"\n[DONE] Old mods are safely backed up in: {backup_dir}")
    else:
        print(f"\n[DONE] Dry run complete. No files were changed.")
        
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_crash(e)
        input("\nPress Enter to exit...")