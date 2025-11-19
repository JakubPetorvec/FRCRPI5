import numpy as np
from PIL import Image

# oficiální kodové knihovny (bit patterny)
FAMILIES = {
    "tag36h11": (36, 11, "apriltag/patterns/tag36_11.npz"),
    "tag25h9":  (25, 9, "apriltag/patterns/tag25_9.npz"),
    "tag16h5":  (16, 5, "apriltag/patterns/tag16_5.npz"),
}

# ---------------------------------------------------
# CREATE APRILTAG IMAGE FROM FAMILY + ID
# ---------------------------------------------------
def generate_tag(family: str, tag_id: int, size: int = 400) -> Image.Image:
    family = family.lower()

    if family not in FAMILIES:
        raise ValueError(f"Unknown family {family}")

    bits, hamming, file_path = FAMILIES[family]
    pattern = np.load(file_path)["arr_0"]

    if tag_id >= pattern.shape[0]:
        raise ValueError(f"ID {tag_id} out of range for {family}")

    bitmap = pattern[tag_id]

    # vytvořit obrázek
    cell = size // bitmap.shape[0]
    img = Image.new("RGB", (size, size), "white")
    pixels = img.load()

    for y in range(bitmap.shape[0]):
        for x in range(bitmap.shape[1]):
            val = bitmap[y, x]
            color = 0 if val == 1 else 255
            for dy in range(cell):
                for dx in range(cell):
                    pixels[x * cell + dx, y * cell + dy] = (color, color, color)

    return img
