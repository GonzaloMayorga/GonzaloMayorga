"""Small, explicit validation for the fixed v1 card layout."""

import math
import re


class ConfigError(ValueError):
    pass


def validate_config(config: dict) -> None:
    def section(parent: dict, key: str, path: str, required: bool = True) -> dict:
        value = parent.get(key, None if required else {})
        if not isinstance(value, dict):
            raise ConfigError(f"[{path}] must be a TOML table.")
        return value

    def text(value: object, path: str, *, nonempty: bool = True) -> None:
        if not isinstance(value, str) or (nonempty and not value.strip()):
            raise ConfigError(f"{path} must be a {'nonempty ' if nonempty else ''}string.")
        if any(not (c in '\t\n\r' or 0x20 <= ord(c) <= 0xD7FF
                    or 0xE000 <= ord(c) <= 0xFFFD
                    or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
            raise ConfigError(f"{path} contains a character forbidden in XML.")

    def strings(value: object, path: str) -> None:
        if not isinstance(value, list):
            raise ConfigError(f"{path} must be an array of strings (empty is allowed).")
        for item in value:
            text(item, path)

    profile = section(config, "profile", "profile")
    for key in ("username", "name", "role", "location"):
        text(profile.get(key), f"profile.{key}", nonempty=key in {"username", "name"})
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", profile["username"]):
        raise ConfigError("profile.username must be a GitHub login (1–39 letters, digits or hyphens).")

    system = section(config, "system", "system")
    strings(system.get("os"), "system.os")
    skills = section(config, "skills", "skills")
    for key in ("languages", "backend", "frontend", "tools"):
        strings(skills.get(key), f"skills.{key}")

    avatar = section(config, "avatar", "avatar", required=False)
    width = avatar.get("width", 26)
    if type(width) is not int or not 8 <= width <= 96:
        raise ConfigError("avatar.width must be an integer between 8 and 96 for this layout.")
    gamma = avatar.get("gamma", 0.9)
    if type(gamma) not in (int, float) or not math.isfinite(gamma) or not 0.1 <= gamma <= 3:
        raise ConfigError("avatar.gamma must be a finite number between 0.1 and 3.")
    if type(avatar.get("remove_background", True)) is not bool:
        raise ConfigError("avatar.remove_background must be true or false.")
    for obsolete in ("style", "pixel_size"):
        if obsolete in avatar:
            raise ConfigError(f"Remove avatar.{obsolete}: v1 uses fixed-size SVG pixels; this option had no visual effect.")

    metrics = section(config, "metrics", "metrics", required=False)
    loc = section(metrics, "loc", "metrics.loc", required=False)
    for key in ("enabled", "include_forks"):
        if type(loc.get(key, False)) is not bool:
            raise ConfigError(f"metrics.loc.{key} must be true or false.")
    exclusions = loc.get("exclude_repositories", [])
    strings(exclusions, "metrics.loc.exclude_repositories")
    for repo in exclusions:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ConfigError("metrics.loc.exclude_repositories entries must use owner/repository.")
