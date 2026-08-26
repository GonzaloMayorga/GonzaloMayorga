import os
from pathlib import Path
import tomllib

from profile_card.avatar import get_avatar_art
from profile_card.github import GitHubClient
from profile_card.renderer import write_profile


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "profile.toml"
ENV_PATH = ROOT_DIR / ".env"


def load_config() -> dict:
    with CONFIG_PATH.open("rb") as file:
        return tomllib.load(file)


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


def main() -> None:
    load_env_file()

    config = load_config()

    print("Generating GitHub profile card...")

    username = config["profile"]["username"]
    avatar_config = config.get("avatar", {})

    print(f"Fetching avatar for {username}...")

    avatar_matrix = get_avatar_art(
        username=username,
        width=avatar_config.get("width", 26),
        gamma=avatar_config.get("gamma", 0.9),
        remove_bg=avatar_config.get("remove_background", True),
        style=avatar_config.get("style", "blocks"),
    )

    github_token = os.getenv("GITHUB_TOKEN")

    if github_token:
        print("GitHub token detected. Fetching GraphQL stats...")
    else:
        print("No GitHub token found. Commits and contributions will be --.")

    github = GitHubClient(token=github_token)

    try:
        github_stats = github.get_stats(username)
    finally:
        github.close()

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
        "lines_of_code": "--",
    }

    for theme in ("dark", "light"):
        output_path = write_profile(
            config=config,
            theme_name=theme,
            avatar_matrix=avatar_matrix,
        )

        print(f"✓ Generated {output_path.relative_to(ROOT_DIR)}")

    print("Done.")


if __name__ == "__main__":
    main()
