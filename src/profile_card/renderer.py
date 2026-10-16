from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from profile_card.avatar import AvatarMatrix


ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT_DIR / "templates"
GENERATED_DIR = ROOT_DIR / "generated"


THEMES = {
    "dark": {
        "background": "#0d1117",
        "border": "#30363d",
        "primary": "#e6edf3",
        "secondary": "#8b949e",
        "accent": "#58a6ff",
        "green": "#3fb950",
        "purple": "#bc8cff",
    },
    "light": {
        "background": "#ffffff",
        "border": "#d0d7de",
        "primary": "#1f2328",
        "secondary": "#656d76",
        "accent": "#0969da",
        "green": "#1a7f37",
        "purple": "#8250df",
    },
}


def get_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        # The template ends in .j2, so extension-based SVG escaping misses it.
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_profile(
    config: dict[str, Any],
    theme_name: str,
    avatar_matrix: AvatarMatrix,
) -> str:
    if theme_name not in THEMES:
        raise ValueError(f"Unknown theme: {theme_name}")

    environment = get_environment()
    template = environment.get_template("profile.svg.j2")

    return template.render(
        **config,
        theme=THEMES[theme_name],
        avatar_matrix=avatar_matrix,
    )


def write_profile(
    config: dict[str, Any],
    theme_name: str,
    avatar_matrix: AvatarMatrix,
) -> Path:
    GENERATED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg = render_profile(
        config=config,
        theme_name=theme_name,
        avatar_matrix=avatar_matrix,
    )

    output_path = (
        GENERATED_DIR
        / f"profile-{theme_name}.svg"
    )

    output_path.write_text(
        svg,
        encoding="utf-8",
    )

    return output_path
