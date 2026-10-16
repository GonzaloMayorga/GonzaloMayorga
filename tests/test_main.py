import xml.etree.ElementTree as ET

import httpx
import pytest

from profile_card import main, renderer
from profile_card.cache import LocCache
from profile_card.github import GitHubStats
from test_metrics import Client, repository, commit, SHA, OTHER_SHA


@pytest.fixture
def local_run(config, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "load_config", lambda: config)
    monkeypatch.setattr(main, "load_env_file", lambda: None)
    monkeypatch.setattr(main, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(main, "LOC_CACHE_PATH", tmp_path / "cache/loc.json")
    monkeypatch.setattr(renderer, "GENERATED_DIR", tmp_path / "generated")
    monkeypatch.setattr(main, "get_avatar_art", lambda **kw: [[None, 0.5]])
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    return tmp_path


def test_loc_failure_produces_both_cards_with_no_partial_total(config, local_run, monkeypatch, capsys):
    config["metrics"] = {"loc": {"enabled": True}}
    cache = LocCache(main.LOC_CACHE_PATH)
    cache.set("user/repo", SHA, 10, 3)
    cache.save()
    before = main.LOC_CACHE_PATH.read_bytes()

    class PartialFailure(Client):
        def get_repositories(self, username):
            return [repository()]
        def get_stats(self, *args, **kw):
            return GitHubStats(1, 2, 3, None, None)
        def get_commit_stats(self, **kw):
            raise httpx.ReadTimeout("simulated")
        def close(self):
            self.closed = True

    client = PartialFailure([commit(), commit(OTHER_SHA)])
    monkeypatch.setattr(main, "GitHubClient", lambda **kw: client)
    main.main()
    assert client.closed
    assert main.LOC_CACHE_PATH.read_bytes() == before
    for theme in ("dark", "light"):
        root = ET.parse(local_run / f"generated/profile-{theme}.svg")
        loc = root.find(".//{*}text[@x='250'][@y='462']/{*}tspan")
        assert loc.text == "--"
    assert "no partial total" in capsys.readouterr().err


def test_loc_is_opt_in(config, local_run, monkeypatch):
    class NoLoc(Client):
        def get_repositories(self, username):
            return [repository()]
        def get_stats(self, *args, **kw):
            return GitHubStats(1, 2, 3, None, None)
        def get_repository_commits(self, **kw):
            pytest.fail("LOC must be opt-in")
        def close(self):
            pass
    monkeypatch.setattr(main, "GitHubClient", lambda **kw: NoLoc())
    main.main()
    assert not main.LOC_CACHE_PATH.exists()


def test_required_api_failure_leaves_existing_cards_untouched(local_run, monkeypatch, capsys):
    renderer.GENERATED_DIR.mkdir()
    for theme in ("dark", "light"):
        (renderer.GENERATED_DIR / f"profile-{theme}.svg").write_text("previous card")
    class InvalidToken:
        def get_repositories(self, username):
            response = httpx.Response(401, request=httpx.Request("GET", "https://api.github.com/users/example/repos"))
            response.raise_for_status()
        def close(self):
            self.closed = True
    client = InvalidToken()
    monkeypatch.setattr(main, "GitHubClient", lambda **kw: client)
    with pytest.raises(SystemExit) as error:
        main.main()
    assert error.value.code == 1
    assert client.closed
    assert "HTTP 401" in capsys.readouterr().err
    for path in renderer.GENERATED_DIR.glob("*.svg"):
        assert path.read_text() == "previous card"


def test_env_file_does_not_override_exported_token(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('# comment\nexport GITHUB_TOKEN="local-test-value"\n')
    monkeypatch.setenv("GITHUB_TOKEN", "")
    main.load_env_file(path)
    assert main.os.environ["GITHUB_TOKEN"] == ""
    monkeypatch.delenv("GITHUB_TOKEN")
    main.load_env_file(path)
    assert main.os.environ["GITHUB_TOKEN"] == "local-test-value"
