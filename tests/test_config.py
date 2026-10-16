import pytest

from profile_card.config import ConfigError, validate_config
from profile_card import main


@pytest.mark.parametrize("section,key,value", [
    ("profile", "username", ""),
    ("profile", "username", "../someone"),
    ("profile", "name", None),
    ("profile", "name", "bad\x00name"),
    ("avatar", "width", 0),
    ("avatar", "width", 97),
    ("avatar", "width", True),
    ("avatar", "gamma", float("nan")),
    ("avatar", "gamma", -1),
    ("avatar", "gamma", "0.9"),
    ("avatar", "remove_background", "false"),
    ("avatar", "style", "blocks"),
    ("skills", "tools", "Git"),
])
def test_invalid_fields_have_useful_errors(config, section, key, value):
    config[section][key] = value
    with pytest.raises(ConfigError, match=section + r"\." + key):
        validate_config(config)


@pytest.mark.parametrize("section", ["profile", "system", "skills"])
def test_required_sections(config, section):
    del config[section]
    with pytest.raises(ConfigError, match=section):
        validate_config(config)


def test_optional_sections_and_xml_text(config):
    del config["avatar"]
    config["profile"]["name"] = 'A & B <Developer> "José"'
    validate_config(config)


@pytest.mark.parametrize("loc", [{"enabled": "false"}, {"exclude_repositories": ["repo-only"]}])
def test_invalid_loc_options(config, loc):
    config["metrics"] = {"loc": loc}
    with pytest.raises(ConfigError, match="metrics.loc"):
        validate_config(config)


def test_invalid_toml_aborts_before_network(tmp_path, monkeypatch, capsys):
    path = tmp_path / "profile.toml"
    path.write_text("[invalid")
    monkeypatch.setattr(main, "CONFIG_PATH", path)
    monkeypatch.setattr(main, "GitHubClient", lambda **kw: pytest.fail("Network must not start"))
    with pytest.raises(SystemExit) as error:
        main.main()
    assert error.value.code == 1
    assert "profile.toml" in capsys.readouterr().err
