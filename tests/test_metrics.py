import pytest

from profile_card.cache import LocCache
from profile_card.metrics import calculate_code_stats


SHA = "a" * 40
OTHER_SHA = "b" * 40


def repository(name="repo", fork=False):
    return {"full_name": f"user/{name}", "name": name, "owner": {"login": "user"}, "fork": fork}


def commit(sha=SHA, parents=1):
    return {"sha": sha, "parents": [{}] * parents}


class Client:
    def __init__(self, commits=None):
        self.commits = commits if commits is not None else [commit()]
        self.list_calls = []
        self.detail_calls = []

    def get_repository_commits(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.commits

    def get_commit_stats(self, **kwargs):
        self.detail_calls.append(kwargs)
        return 10, 3


def test_merges_forks_duplicates_and_exclusions(tmp_path):
    cache = LocCache(tmp_path / "loc.json")
    client = Client([commit(), commit(), commit(OTHER_SHA, parents=2)])
    repos = [repository(), repository("REPO"), repository("fork", True), repository("excluded"), repository("user")]
    stats = calculate_code_stats(client, "user", repos, cache, excluded_repositories={"USER/EXCLUDED"})
    assert stats.net == 7
    assert len(client.list_calls) == len(client.detail_calls) == 1
    assert client.list_calls[0]["author"] == "user"
    assert cache.get("user/repo", OTHER_SHA) is None


def test_shared_sha_across_repos_and_opt_in_forks_counts_once(tmp_path):
    client = Client()
    stats = calculate_code_stats(client, "user", [repository(), repository("fork", True)],
                                 LocCache(tmp_path / "loc.json"), include_forks=True)
    assert stats.net == 7
    assert len(client.list_calls) == 2
    assert len(client.detail_calls) == 1


def test_second_run_reuses_details_and_prunes_rewritten_history(tmp_path):
    path = tmp_path / "loc.json"
    client = Client()
    calculate_code_stats(client, "user", [repository()], LocCache(path))
    before = path.read_bytes()
    calculate_code_stats(client, "user", [repository()], LocCache(path))
    assert len(client.list_calls) == 2
    assert len(client.detail_calls) == 1
    assert path.read_bytes() == before
    client.commits = [commit(OTHER_SHA, parents=0)]
    calculate_code_stats(client, "user", [repository()], LocCache(path))
    assert LocCache(path).get("user/repo", SHA) is None
    assert LocCache(path).get("user/repo", OTHER_SHA) is not None
    assert len(client.detail_calls) == 2


def test_failure_does_not_prune_or_save_partial_history(tmp_path):
    path = tmp_path / "loc.json"
    cache = LocCache(path)
    cache.set("user/repo", SHA, 10, 3)
    cache.save()
    before = path.read_bytes()

    class FailingClient(Client):
        def get_repository_commits(self, **kwargs):
            if kwargs["repository"] == "failed":
                raise RuntimeError("API failed")
            return []  # Would prune the first repository if persisted too early.

    with pytest.raises(RuntimeError):
        calculate_code_stats(FailingClient(), "user", [repository(), repository("failed")], cache)
    assert path.read_bytes() == before
    assert cache.get("user/repo", SHA) is not None


def test_negative_net_is_not_clamped_and_stale_repos_are_removed(tmp_path):
    cache = LocCache(tmp_path / "loc.json")
    cache.set("user/repo", SHA, 1, 10)
    cache.set("user/removed", OTHER_SHA, 100, 0)
    result = calculate_code_stats(Client(), "user", [repository()], cache)
    assert result.net == -9
    assert set(cache.data["repositories"]) == {"user/repo"}
