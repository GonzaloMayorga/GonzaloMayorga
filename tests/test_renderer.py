import xml.etree.ElementTree as ET

import pytest

from profile_card.renderer import render_profile


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_render_profile_generates_svg(config, theme):
    root = ET.fromstring(render_profile(config, theme, [[None, 0.8], [0.4, 1.0]]))
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["viewBox"] == "0 0 900 500"
    assert len(root.findall(".//{*}g[@class='avatar']/{*}rect")) == 3
    assert "Engineer" in "".join(root.itertext())


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_configuration_is_text_not_markup(config, theme):
    value = 'A & B <script>alert("x")</script> > \'café\' 日本語 🚀'
    for key in config["profile"]:
        config["profile"][key] = value
    config["system"]["os"] = [value]
    for key in config["skills"]:
        config["skills"][key] = [value]
    root = ET.fromstring(render_profile(config, theme, []))
    assert root.find("{*}title").text == value + " GitHub Profile"
    assert value in root.find("{*}desc").text
    assert root.findall(".//{*}script") == []
    text = "".join(root.itertext())
    assert text.count(value) == 10
    assert all(element.tag.startswith("{http://www.w3.org/2000/svg}") for element in root.iter())


def test_render_profile_rejects_unknown_theme():
    with pytest.raises(ValueError, match="Unknown theme"):
        render_profile({}, "windows-95", [])
