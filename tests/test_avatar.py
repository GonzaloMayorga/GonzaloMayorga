from PIL import Image

from profile_card.avatar import image_to_pixel_matrix


def test_pixel_matrix_preserves_transparency():
    image = Image.new(
        "RGBA",
        (10, 10),
        (0, 0, 0, 0),
    )

    # pequeño bloque opaco
    for x in range(3, 7):
        for y in range(3, 7):
            image.putpixel(
                (x, y),
                (30, 30, 30, 255),
            )

    matrix = image_to_pixel_matrix(
        image,
        width=10,
    )

    flattened = [
        pixel
        for row in matrix
        for pixel in row
    ]

    assert any(pixel is None for pixel in flattened)

    visible_pixels = [
        pixel
        for pixel in flattened
        if pixel is not None
    ]

    assert visible_pixels
    assert all(
        0.0 <= pixel <= 1.0
        for pixel in visible_pixels
    )