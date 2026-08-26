from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageEnhance, ImageOps


AvatarMatrix = list[list[float | None]]
BLOCK_CHARACTERS = "█▓▒░."
ROOT_DIR = Path(__file__).resolve().parents[2]
DEBUG_DIR = ROOT_DIR / "generated" / "debug"


def download_avatar(username: str) -> Image.Image:
    url = f"https://github.com/{username}.png?size=460"

    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=15.0,
    )
    response.raise_for_status()

    return Image.open(BytesIO(response.content)).convert("RGBA")


def remove_background(image: Image.Image) -> Image.Image:
    try:
        from rembg import remove
    except ModuleNotFoundError as error:
        if error.name == "onnxruntime":
            raise RuntimeError(
                "Missing dependency: onnxruntime. "
                "Install project dependencies again with "
                "`python -m pip install -e .`."
            ) from error

        raise

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    result = remove(buffer.getvalue())

    return Image.open(BytesIO(result)).convert("RGBA")


def crop_subject(
    image: Image.Image,
    focus_height: float = 0.80,
    focus_width: float = 0.72,
) -> Image.Image:
    alpha = image.getchannel("A")

    mask = alpha.point(
        lambda value: 255 if value > 20 else 0
    )

    bbox = mask.getbbox()

    if bbox is None:
        return ImageOps.fit(
            image,
            (256, 256),
            method=Image.Resampling.LANCZOS,
        )

    left, top, right, bottom = bbox

    subject_width = right - left
    subject_height = bottom - top

    crop_height = max(1, int(subject_height * focus_height))
    crop_width = max(1, int(subject_width * focus_width))

    center_x = (left + right) // 2

    crop_left = center_x - crop_width // 2
    crop_right = center_x + crop_width // 2

    crop_top = top
    crop_bottom = top + crop_height

    crop_left = max(0, crop_left)
    crop_top = max(0, crop_top)
    crop_right = min(image.width, crop_right)
    crop_bottom = min(image.height, crop_bottom)

    cropped = image.crop(
        (
            crop_left,
            crop_top,
            crop_right,
            crop_bottom,
        )
    )

    side = max(cropped.width, cropped.height)

    canvas = Image.new(
        "RGBA",
        (side, side),
        (0, 0, 0, 0),
    )

    offset_x = (side - cropped.width) // 2
    offset_y = (side - cropped.height) // 2

    canvas.paste(
        cropped,
        (offset_x, offset_y),
        cropped,
    )

    return canvas.resize(
        (256, 256),
        Image.Resampling.LANCZOS,
    )


def save_debug_image(
    image: Image.Image,
    filename: str,
) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    image.save(DEBUG_DIR / filename)


def preprocess_subject(image: Image.Image) -> tuple[Image.Image, Image.Image]:
    alpha = image.getchannel("A")

    grayscale = image.convert("L")
    grayscale = ImageOps.autocontrast(grayscale, cutoff=2)
    grayscale = ImageEnhance.Contrast(grayscale).enhance(1.8)
    grayscale = ImageEnhance.Sharpness(grayscale).enhance(1.4)

    return grayscale, alpha

def image_to_pixel_matrix(
    image: Image.Image,
    width: int = 42,
    gamma: float = 0.9,
) -> AvatarMatrix:
    grayscale, alpha = preprocess_subject(image)

    aspect_ratio = grayscale.height / grayscale.width
    height = max(1, int(width * aspect_ratio))

    grayscale = grayscale.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )

    alpha = alpha.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )

    grayscale_pixels = grayscale.load()
    alpha_pixels = alpha.load()

    matrix: AvatarMatrix = []

    for y in range(height):
        row: list[float | None] = []

        for x in range(width):
            if alpha_pixels[x, y] < 40:
                row.append(None)
                continue

            brightness = grayscale_pixels[x, y] / 255.0

            intensity = (1.0 - brightness) ** gamma

            row.append(intensity)

        matrix.append(row)

    return matrix

def image_to_blocks(
    image: Image.Image,
    width: int = 26,
    gamma: float = 0.9,
) -> list[str]:
    grayscale, alpha = preprocess_subject(image)

    aspect_ratio = grayscale.height / grayscale.width
    height = max(1, int(width * aspect_ratio * 0.55))

    grayscale = grayscale.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )

    alpha = alpha.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )

    grayscale_pixels = grayscale.load()
    alpha_pixels = alpha.load()

    lines: list[str] = []

    for y in range(height):
        row = []

        for x in range(width):
            if alpha_pixels[x, y] < 30:
                row.append(" ")
                continue

            brightness = grayscale_pixels[x, y] / 255.0
            brightness = brightness**gamma

            index = int(brightness * (len(BLOCK_CHARACTERS) - 1))
            row.append(BLOCK_CHARACTERS[index])

        lines.append("".join(row).rstrip())

    return lines


def get_avatar_art(
    username: str,
    width: int = 42,
    gamma: float = 0.9,
    remove_bg: bool = True,
    style: str = "blocks",
) -> AvatarMatrix:
    if style not in {"blocks", "matrix", "pixels"}:
        raise ValueError(f"Unsupported avatar style: {style}")

    image = download_avatar(username)

    save_debug_image(image, "01-original.png")

    if remove_bg:
        image = remove_background(image)
        save_debug_image(image, "02-no-background.png")

    image = crop_subject(image)
    save_debug_image(image, "03-face-crop.png")

    return image_to_pixel_matrix(
        image,
        width=width,
        gamma=gamma,
    )
