from profile_card.cache import LocCache


def test_loc_cache_stores_prunes_and_saves_commit_stats(tmp_path):
    cache_path = tmp_path / "loc.json"
    cache = LocCache(cache_path)

    cache.set(
        repository="GonzaloMayorga/example",
        sha="abc123",
        additions=10,
        deletions=3,
    )
    cache.set(
        repository="GonzaloMayorga/example",
        sha="old456",
        additions=5,
        deletions=1,
    )

    cache.prune_repository(
        repository="GonzaloMayorga/example",
        active_shas={"abc123"},
    )
    cache.save()

    reloaded_cache = LocCache(cache_path)

    cached = reloaded_cache.get(
        repository="GonzaloMayorga/example",
        sha="abc123",
    )

    assert cached is not None
    assert cached.additions == 10
    assert cached.deletions == 3
    assert (
        reloaded_cache.get(
            repository="GonzaloMayorga/example",
            sha="old456",
        )
        is None
    )


import json
import pytest


@pytest.mark.parametrize("contents", [
    "{", "[]", '{"version": 999}',
    '{"version": 1, "repositories": []}',
    json.dumps({"version": 1, "repositories": {"u/r": {"commits": {"abcdef": {"additions": -1, "deletions": 0}}}}}),
    json.dumps({"version": 1, "repositories": {"u/r": {"commits": {"abcdef": {"additions": True, "deletions": 0}}}}}),
])
def test_corrupt_cache_can_be_rebuilt(tmp_path, capsys, contents):
    path = tmp_path / "loc.json"
    path.write_text(contents)
    cache = LocCache(path)
    assert cache.data["repositories"] == {}
    assert "rebuilding" in capsys.readouterr().err
    # Loading alone never destroys the previous file.
    assert path.read_text() == contents
    cache.set("User/Repo", "abcdef", 5, 2)
    cache.save()
    assert LocCache(path).get("USER/REPO", "abcdef").additions == 5


def test_atomic_save_preserves_previous_cache_on_failure(tmp_path, monkeypatch):
    import profile_card.cache as module
    path = tmp_path / "loc.json"
    cache = LocCache(path)
    cache.set("u/r", "abcdef", 5, 2)
    cache.save()
    before = path.read_bytes()
    cache.set("u/r", "123456", 10, 1)

    def fail_replace(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(OSError):
        cache.save()
    assert path.read_bytes() == before
    assert list(tmp_path.glob("*.tmp")) == []


def test_cache_does_not_persist_extra_fields(tmp_path):
    path = tmp_path / "loc.json"
    path.write_text(json.dumps({"version": 1, "extra": "not-public-data", "repositories": {
        "User/Repo": {"extra": "discard", "commits": {"abcdef": {"additions": 1, "deletions": 2, "message": "discard"}}}
    }}))
    cache = LocCache(path)
    cache.save()
    data = json.loads(path.read_text())
    assert data == {"version": 1, "repositories": {"user/repo": {"commits": {"abcdef": {"additions": 1, "deletions": 2}}}}}
