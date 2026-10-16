from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


CACHE_VERSION = 1


@dataclass(frozen=True)
class CachedCommitStats:
    additions: int
    deletions: int


class LocCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = self._load()

    @staticmethod
    def _empty() -> dict:
        return {"version": CACHE_VERSION, "repositories": {}}

    @staticmethod
    def _validated(data: object) -> dict:
        if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != CACHE_VERSION:
            raise ValueError("Unsupported cache version")
        repositories = data.get("repositories")
        if not isinstance(repositories, dict):
            raise ValueError("Invalid cache repositories")
        clean = LocCache._empty()
        for name, repository in repositories.items():
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
                raise ValueError("Invalid repository name")
            if not isinstance(repository, dict) or not isinstance(repository.get("commits"), dict):
                raise ValueError("Invalid cache commits")
            commits = clean["repositories"].setdefault(name.casefold(), {"commits": {}})["commits"]
            for sha, stats in repository["commits"].items():
                if not re.fullmatch(r"[0-9a-f]{6,64}", sha) or not isinstance(stats, dict):
                    raise ValueError("Invalid commit record")
                if any(type(stats.get(key)) is not int or stats[key] < 0 for key in ("additions", "deletions")):
                    raise ValueError("Invalid commit counts")
                value = {key: stats[key] for key in ("additions", "deletions")}
                if sha in commits and commits[sha] != value:
                    raise ValueError("Conflicting cache records")
                commits[sha] = value
        # Only persist this public-data schema; never preserve arbitrary fields.
        return clean

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return self._validated(data)
        except FileNotFoundError:
            return self._empty()
        except (ValueError, UnicodeError, TypeError):
            print("Warning: invalid or incompatible LOC cache; rebuilding from GitHub.", file=sys.stderr)
            return self._empty()

    def get(self, repository: str, sha: str) -> CachedCommitStats | None:
        commit = self.data["repositories"].get(repository.casefold(), {}).get("commits", {}).get(sha)
        return CachedCommitStats(**commit) if commit is not None else None

    def set(self, repository: str, sha: str, additions: int, deletions: int) -> None:
        commits = self.data["repositories"].setdefault(repository.casefold(), {"commits": {}})["commits"]
        commits[sha] = {"additions": additions, "deletions": deletions}

    def prune_repository(self, repository: str, active_shas: set[str]) -> None:
        repository_data = self.data["repositories"].get(repository.casefold())
        if repository_data is not None:
            repository_data["commits"] = {
                sha: stats for sha, stats in repository_data["commits"].items()
                if sha in active_shas
            }

    def save(self) -> None:
        data = self._validated(self.data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=self.path.name + ".", suffix=".tmp", delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(data, file, indent=2, sort_keys=True)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
