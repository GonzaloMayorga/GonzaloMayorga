from dataclasses import dataclass

import httpx

REST_API_URL = "https://api.github.com"
GRAPHQL_API_URL = "https://api.github.com/graphql"
API_VERSION = "2026-03-10"


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

        while True:
            response = self._client.get(
                f"{REST_API_URL}/users/{username}/repos",
                params={
                    "type": "owner",
                    "sort": "updated",
                    "per_page": 100,
                    "page": page,
                },
            )

            response.raise_for_status()

            current_page = response.json()

            if not current_page:
                break

            repositories.extend(current_page)

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
                f"GitHub GraphQL error: {payload['errors']}"
            )

        user = payload.get("data", {}).get("user")

        if user is None:
            raise RuntimeError(
                f"GitHub user not found: {username}"
            )

        contributions_collection = user["contributionsCollection"]

        return GitHubContributionStats(
            commits=contributions_collection[
                "totalCommitContributions"
            ],
            total=contributions_collection[
                "contributionCalendar"
            ]["totalContributions"],
        )

    def get_stats(self, username: str) -> GitHubStats:
        user = self.get_user(username)
        repositories = self.get_repositories(username)

        stars = sum(
            repository.get("stargazers_count", 0)
            for repository in repositories
        )
        
        try:
            contribution_stats = self.get_contributions(username)
        except(httpx.HTTPError, RuntimeError) as error:
            print(f"Warning: could not fetch contributions: {error}")
            contribution_stats = None

        return GitHubStats(
            repos=user["public_repos"],
            followers=user["followers"],
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
