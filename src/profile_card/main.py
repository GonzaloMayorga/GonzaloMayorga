import os
import sys

import httpx
from pathlib import Path
import tomllib

from profile_card.avatar import get_avatar_art
from profile_card.github import GitHubClient, error_summary
from profile_card.config import ConfigError, validate_config
from profile_card.renderer import write_profile
from profile_card.cache import LocCache
from profile_card.metrics import calculate_code_stats


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "profile.toml"
ENV_PATH = ROOT_DIR / ".env"
LOC_CACHE_PATH = ROOT_DIR / "cache" / "loc.json"


def load_config() -> dict:
    try:
        with CONFIG_PATH.open("rb") as file:
            config = tomllib.load(file)
    except (OSError, ValueError) as error:
        raise ConfigError("Cannot read profile.toml; check that it exists and contains valid UTF-8 TOML.") from error
    validate_config(config)
    return config


def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if line.startswith("export "):
            line = line.removeprefix("export ").strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("'\"")

        os.environ.setdefault(name, value)


def generate_profile() -> None:
    config = load_config()
    load_env_file()

    print("Generating GitHub profile card...")

    username = config["profile"]["username"]
    avatar_config = config.get("avatar", {})

    github_token = os.getenv("GITHUB_TOKEN", "").strip()

    if github_token:
        print("GitHub token detected. Fetching GraphQL stats...")
    else:
        print("No GitHub token found. Commits and contributions will be --.")

    github = GitHubClient(token=github_token)

    try:
        repositories = github.get_repositories(username)
        github_stats = github.get_stats(
            username,
            repositories=repositories,
        )

        loc_config = (
            config
            .get("metrics", {})
            .get("loc", {})
        )

        code_stats = None

        if loc_config.get("enabled", False):
            print("Calculating code statistics...")

            try:
                loc_cache = LocCache(LOC_CACHE_PATH)

                code_stats = calculate_code_stats(
                    client=github,
                    username=username,
                    repositories=repositories,
                    cache=loc_cache,
                    include_forks=loc_config.get(
                        "include_forks",
                        False,
                    ),
                    excluded_repositories=set(
                        loc_config.get(
                            "exclude_repositories",
                            [],
                        )
                    ),
                )
            except (httpx.HTTPError, OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as error:
                print(f"Warning: LOC unavailable (--); no partial total published. {error_summary(error)}", file=sys.stderr)
    finally:
        github.close()

    print(f"Fetching avatar for {username}...")

    avatar_matrix = get_avatar_art(
        username=username,
        width=avatar_config.get("width", 26),
        gamma=avatar_config.get("gamma", 0.9),
        remove_bg=avatar_config.get("remove_background", True),
    )

    config["stats"] = {
        "repos": github_stats.repos,
        "followers": github_stats.followers,
        "stars": github_stats.stars,
        "contributions": (
            github_stats.contributions
            if github_stats.contributions is not None
            else "--"
        ),
        "commits": (
            github_stats.commits
            if github_stats.commits is not None
            else "--"
        ),
        "lines_of_code": (
            f"{code_stats.net:,}"
            if code_stats is not None
            else "--"
        ),
    }

    for theme in ("dark", "light"):
        output_path = write_profile(
            config=config,
            theme_name=theme,
            avatar_matrix=avatar_matrix,
        )

        print(f"✓ Generated {output_path.relative_to(ROOT_DIR)}")

    print("Done.")


def main() -> None:
    try:
        generate_profile()
    except ConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    except (httpx.HTTPError, OSError, RuntimeError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Error: profile generation aborted. {error_summary(error)}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
