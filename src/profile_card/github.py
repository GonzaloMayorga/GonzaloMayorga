from dataclasses import dataclass
import sys

import httpx

REST_API_URL = "https://api.github.com"
GRAPHQL_API_URL = "https://api.github.com/graphql"
API_VERSION = "2026-03-10"


def error_summary(error: Exception) -> str:
    """Useful diagnostics without logging credentials or remote response bodies."""
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if status == 401:
            return "HTTP 401: GitHub rejected GITHUB_TOKEN; replace it or unset it for public data."
        if status in (403, 429):
            return f"HTTP {status}: check token permissions and GitHub rate limits; retry later."
        return f"HTTP {status}: GitHub request failed."
    if isinstance(error, httpx.RequestError):
        return "Network error while contacting GitHub; check connectivity and retry."
    if isinstance(error, OSError):
        return "Local file/model operation failed; check files, permissions and available disk space."
    return "Invalid or unavailable data; check configuration, GitHub responses and local dependencies."


def _count(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("GitHub returned an invalid count")
    return value


@dataclass(frozen=True)
class GitHubStats:
    repos: int
    followers: int
    stars: int
    commits: int | None
    contributions: int | None


@dataclass(frozen=True)
class GitHubContributionStats:
    commits: int
    total: int


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        token = token.strip() if token else None

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "github-profile-card",
        }

        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.Client(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )

        self.token = token

    def close(self) -> None:
        self._client.close()

    def get_user(self, username: str) -> dict:
        response = self._client.get(
            f"{REST_API_URL}/users/{username}"
        )
        response.raise_for_status()

        return response.json()

    def get_repositories(self, username: str) -> list[dict]:
        repositories: list[dict] = []

        page = 1
        seen = set()

        while True:
            response = self._client.get(
                f"{REST_API_URL}/users/{username}/repos",
                params={
                    "type": "owner",
                    "sort": "full_name",
                    "direction": "asc",
                    "per_page": 100,
                    "page": page,
                },
            )

            response.raise_for_status()

            current_page = response.json()
            if not isinstance(current_page, list):
                raise ValueError("Invalid repository list")

            if not current_page:
                break

            for repository in current_page:
                name = repository["full_name"].casefold()
                if name not in seen:
                    repositories.append(repository)
                    seen.add(name)

            if len(current_page) < 100:
                break

            page += 1

        return repositories

    def get_contributions(
        self,
        username: str,
    ) -> GitHubContributionStats | None:
        if not self.token:
            return None

        query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              totalCommitContributions
              contributionCalendar {
                totalContributions
              }
            }
          }
        }
        """

        response = self._client.post(
            GRAPHQL_API_URL,
            json={
                "query": query,
                "variables": {
                    "login": username,
                },
            },
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("errors"):
            raise RuntimeError(
                "GitHub GraphQL returned errors"
            )

        user = payload.get("data", {}).get("user")

        if user is None:
            raise RuntimeError(
                f"GitHub user not found: {username}"
            )

        contributions_collection = user["contributionsCollection"]

        return GitHubContributionStats(
            commits=_count(contributions_collection[
                "totalCommitContributions"
            ]),
            total=_count(contributions_collection[
                "contributionCalendar"
            ]["totalContributions"]),
        )

    def get_stats(
        self,
        username: str,
        repositories: list[dict] | None = None,
    ) -> GitHubStats:
        user = self.get_user(username)

        if repositories is None:
            repositories = self.get_repositories(username)

        stars = sum(
            _count(repository["stargazers_count"])
            for repository in repositories
        )
        
        try:
            contribution_stats = self.get_contributions(username)
        except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError, AttributeError) as error:
            print(f"Warning: commits/contributions unavailable (--). {error_summary(error)}", file=sys.stderr)
            contribution_stats = None

        return GitHubStats(
            repos=_count(user["public_repos"]),
            followers=_count(user["followers"]),
            stars=stars,
            commits=(
                contribution_stats.commits
                if contribution_stats is not None
                else None
            ),
            contributions=(
                contribution_stats.total
                if contribution_stats is not None
                else None
            ),
        )

    def get_repository_commits(
        self,
        owner: str,
        repository: str,
        author: str,
    ) -> list[dict]:
        commits: list[dict] = []

        page = 1

        while True:
            response = self._client.get(
                (
                    f"{REST_API_URL}/repos/"
                    f"{owner}/{repository}/commits"
                ),
                params={
                    "author": author,
                    "per_page": 100,
                    "page": page,
                },
            )

            # Only the explicit empty-repository response is a successful empty
            # listing. A generic conflict must not prune cached history.
            if response.status_code == 409:
                payload = response.json()
                if page == 1 and payload.get("message", "").casefold().rstrip(".") == "git repository is empty":
                    return []

            response.raise_for_status()

            current_page = response.json()
            if not isinstance(current_page, list):
                raise ValueError("Invalid commit list")

            if not current_page:
                break

            commits.extend(current_page)

            if len(current_page) < 100:
                break

            page += 1

        return commits

    def get_commit_stats(
        self,
        owner: str,
        repository: str,
        sha: str,
    ) -> tuple[int, int]:
        response = self._client.get(
            (
                f"{REST_API_URL}/repos/"
                f"{owner}/{repository}/commits/{sha}"
            )
        )

        response.raise_for_status()

        commit = response.json()
        stats = commit["stats"]

        return (
            _count(stats["additions"]),
            _count(stats["deletions"]),
        )
