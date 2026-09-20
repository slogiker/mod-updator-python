"""Modrinth API client with batch hash queries, version lookups, and downloads."""

import json
from pathlib import Path
from typing import Any, Optional
import requests

MODRINTH_API_URL = "https://api.modrinth.com/v2"
USER_AGENT = "slogiker/mod-updater/2.0.0 (https://github.com/slogiker/mod-updator-python)"


class ModrinthClient:
    """Client for Modrinth v2 REST API."""

    def __init__(self, base_url: str = MODRINTH_API_URL, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        })

    def get_version_files_by_hashes(self, hashes: list[str], algorithm: str = "sha1") -> dict[str, Any]:
        """
        Batch look up version info for a list of file hashes.
        Returns a dict mapping hash -> version data.
        """
        if not hashes:
            return {}
        url = f"{self.base_url}/version_files"
        try:
            resp = self.session.post(
                url,
                json={"hashes": hashes, "algorithm": algorithm},
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return {}

    def get_updates_by_hashes(
        self,
        hashes: list[str],
        loaders: list[str],
        game_versions: list[str],
        algorithm: str = "sha1"
    ) -> dict[str, Any]:
        """
        Batch check latest updates directly via Modrinth's /version_files/update endpoint.
        Returns a dict mapping original_hash -> latest version data.
        """
        if not hashes:
            return {}
        url = f"{self.base_url}/version_files/update"
        payload = {
            "hashes": hashes,
            "algorithm": algorithm,
            "loaders": loaders,
            "game_versions": game_versions,
        }
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return {}

    def get_project(self, project_id_or_slug: str) -> Optional[dict[str, Any]]:
        """Fetches project details by slug or ID."""
        if not project_id_or_slug:
            return None
        url = f"{self.base_url}/project/{project_id_or_slug}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return None

    def search_project(self, query: str) -> Optional[dict[str, Any]]:
        """Searches for a project by text query and returns top hit."""
        if not query:
            return None
        url = f"{self.base_url}/search"
        try:
            resp = self.session.get(url, params={"query": query, "limit": 1}, timeout=self.timeout)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            return hits[0] if hits else None
        except requests.RequestException:
            return None

    def get_project_versions(
        self,
        project_id_or_slug: str,
        loaders: Optional[list[str]] = None,
        game_versions: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """Fetches all versions for a project, optionally filtered by loader and game version."""
        if not project_id_or_slug:
            return []
        url = f"{self.base_url}/project/{project_id_or_slug}/version"
        params: dict[str, Any] = {}
        if loaders:
            params["loaders"] = json.dumps(loaders)
        if game_versions:
            params["game_versions"] = json.dumps(game_versions)

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return []

    def download_file(self, url: str, destination: Path, chunk_size: int = 65536) -> None:
        """Downloads a file from url to destination path."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_dest = destination.with_suffix(destination.suffix + ".part")
        try:
            with self.session.get(url, stream=True, timeout=self.timeout * 2) as resp:
                resp.raise_for_status()
                with open(temp_dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
            temp_dest.replace(destination)
        except Exception:
            if temp_dest.exists():
                temp_dest.unlink(missing_ok=True)
            raise
