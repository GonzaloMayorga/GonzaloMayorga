from pathlib import Path
import tomllib

from profile_card.renderer import write_profile


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "profile.toml"


def load_config() -> dict:
    with CONFIG_PATH.open("rb") as file:
        return tomllib.load(file)


def main() -> None:
    config = load_config()

    print("Generating GitHub profile card...")

    for theme in ("dark", "light"):
        output_path = write_profile(
            config=config,
            theme_name=theme,
        )

        print(f"✓ Generated {output_path.relative_to(ROOT_DIR)}")

    print("Done.")


if __name__ == "__main__":
    main()