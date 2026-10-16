from copy import deepcopy
from dataclasses import dataclass

from profile_card.cache import LocCache
from profile_card.github import GitHubClient


@dataclass(frozen=True)
class CodeStats:
    additions: int
    deletions: int

    @property
    def net(self) -> int:
        return self.additions - self.deletions


def calculate_code_stats(
    client: GitHubClient,
    username: str,
    repositories: list[dict],
    cache: LocCache,
    *,
    include_forks: bool = False,
    excluded_repositories: set[str] | None = None,
) -> CodeStats:
    excluded = {name.casefold() for name in (excluded_repositories or set())}
    excluded.add(f"{username}/{username}".casefold())
    seen_repositories: set[str] = set()
    counted_shas: set[str] = set()
    known_stats = {}
    total_additions = total_deletions = 0
    # Do not prune or persist anything unless the entire calculation succeeds.
    working = deepcopy(cache)

    for repository in repositories:
        full_name = repository["full_name"].casefold()
        if full_name in excluded or full_name in seen_repositories:
            continue
        if repository.get("fork", False) and not include_forks:
            continue
        seen_repositories.add(full_name)
        owner = repository["owner"]["login"]
        repository_name = repository["name"]
        print(f"Calculating LOC for {full_name}...")
        commits = client.get_repository_commits(
            owner=owner, repository=repository_name, author=username,
        )
        active_shas = set()
        for commit in commits:
            # Missing parent data is an API failure, not proof of a non-merge.
            if not isinstance(commit["parents"], list):
                raise ValueError("Invalid commit parents")
            if len(commit["parents"]) > 1:
                continue
            sha = commit["sha"]
            if sha in active_shas:
                continue
            active_shas.add(sha)
            cached = working.get(full_name, sha)
            if cached is not None:
                additions, deletions = cached.additions, cached.deletions
            elif sha in known_stats:
                additions, deletions = known_stats[sha]
            else:
                additions, deletions = client.get_commit_stats(
                    owner=owner, repository=repository_name, sha=sha,
                )
            working.set(full_name, sha, additions, deletions)
            known_stats[sha] = additions, deletions
            # Shared history (including opt-in forks) counts only once globally.
            if sha not in counted_shas:
                total_additions += additions
                total_deletions += deletions
                counted_shas.add(sha)
        working.prune_repository(full_name, active_shas)

    working.data["repositories"] = {
        name: data for name, data in working.data["repositories"].items()
        if name in seen_repositories
    }
    working.save()
    cache.data = working.data
    return CodeStats(additions=total_additions, deletions=total_deletions)
