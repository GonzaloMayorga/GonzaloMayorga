from profile_card.github import GitHubClient, GitHubContributionStats


def test_get_stats_aggregates_github_data(monkeypatch):
    client = GitHubClient(token="fake-token")

    monkeypatch.setattr(
        client,
        "get_user",
        lambda username: {
            "public_repos": 12,
            "followers": 5,
        },
    )

    monkeypatch.setattr(
        client,
        "get_repositories",
        lambda username: [
            {"stargazers_count": 2},
            {"stargazers_count": 5},
            {"stargazers_count": 1},
        ],
    )

    monkeypatch.setattr(
        client,
        "get_contributions",
        lambda username: GitHubContributionStats(
            commits=22,
            total=31,
        ),
    )

    stats = client.get_stats("GonzaloMayorga")

    assert stats.repos == 12
    assert stats.followers == 5
    assert stats.stars == 8
    assert stats.contributions == 31
    assert stats.commits == 22

    client.close()

def test_contributions_without_token_returns_none():
    client = GitHubClient()

    contributions = client.get_contributions(
        "GonzaloMayorga"
    )

    assert contributions is None

    client.close()


import httpx
import pytest


@pytest.fixture
def client_factory():
    clients = []

    def make(handler, token="test-credential"):
        client = GitHubClient(token=token)
        client._client.close()
        client._client = httpx.Client(transport=httpx.MockTransport(handler))
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()


def test_authenticated_graphql_success(client_factory):
    def handler(request):
        assert request.method == "POST"
        return httpx.Response(200, json={"data": {"user": {"contributionsCollection": {
            "totalCommitContributions": 7, "contributionCalendar": {"totalContributions": 9}
        }}}})
    result = client_factory(handler).get_contributions("user")
    assert result == GitHubContributionStats(commits=7, total=9)


@pytest.mark.parametrize("status,payload", [
    (401, {}), (500, {}),
    (200, {"errors": [{"message": "private-response-sentinel"}]}),
    (200, {"data": {"user": None}}),
    (200, {"data": None}),
    (200, {"data": {"user": {"contributionsCollection": {"totalCommitContributions": None}}}}),
])
def test_graphql_failure_degrades_without_logging_payload(client_factory, capsys, status, payload):
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"public_repos": 1, "followers": 2})
        return httpx.Response(status, json=payload)
    stats = client_factory(handler).get_stats("user", repositories=[])
    assert stats.commits is None and stats.contributions is None
    assert stats.repos == 1
    output = capsys.readouterr()
    assert "unavailable" in output.err
    assert "private-response-sentinel" not in output.err
    assert "test-credential" not in output.err


@pytest.mark.parametrize("status", [401, 403, 500])
def test_required_rest_error_propagates(client_factory, status):
    client = client_factory(lambda req: httpx.Response(status, json={"message": "failure"}))
    with pytest.raises(httpx.HTTPStatusError):
        client.get_stats("user", repositories=[])


def test_repository_and_commit_pagination(client_factory):
    calls = []
    def handler(request):
        calls.append(request)
        page = int(request.url.params["page"])
        if request.url.path.endswith("/repos"):
            return httpx.Response(200, json=[{"full_name": f"user/r{i}"} for i in range(100)] if page == 1 else [{"full_name": "USER/R0"}, {"full_name": "user/last"}])
        assert request.url.params["author"] == "user"
        assert "sha" not in request.url.params  # Default branch, not all branches.
        return httpx.Response(200, json=[{"sha": str(i)} for i in range(100)] if page == 1 else [])
    client = client_factory(handler)
    assert len(client.get_repositories("user")) == 101
    assert len(client.get_repository_commits("user", "repo", "user")) == 100
    assert len(calls) == 4


@pytest.mark.parametrize("empty", [True, False])
def test_only_explicit_empty_repository_is_a_success(client_factory, empty):
    message = "Git Repository is empty." if empty else "Conflict"
    client = client_factory(lambda req: httpx.Response(409, json={"message": message}))
    if empty:
        assert client.get_repository_commits("user", "repo", "user") == []
    else:
        with pytest.raises(httpx.HTTPStatusError):
            client.get_repository_commits("user", "repo", "user")


@pytest.mark.parametrize("payload", [{}, {"stats": {}}, {"stats": {"additions": None, "deletions": 2}}])
def test_missing_commit_stats_never_become_zero(client_factory, payload):
    client = client_factory(lambda req: httpx.Response(200, json=payload))
    with pytest.raises((KeyError, ValueError)):
        client.get_commit_stats("user", "repo", "a" * 40)
