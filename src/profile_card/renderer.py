from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


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
        autoescape=select_autoescape(["svg"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_profile(
    config: dict[str, Any],
    theme_name: str,
) -> str:
    if theme_name not in THEMES:
        raise ValueError(f"Unknown theme: {theme_name}")

    environment = get_environment()
    template = environment.get_template("profile.svg.j2")

    return template.render(
        **config,
        theme=THEMES[theme_name],
    )


def write_profile(
    config: dict[str, Any],
    theme_name: str,
) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    svg = render_profile(config, theme_name)

    output_path = GENERATED_DIR / f"profile-{theme_name}.svg"
    output_path.write_text(svg, encoding="utf-8")

    return output_path