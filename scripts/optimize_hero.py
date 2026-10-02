"""Build responsive WebP assets from the existing campus photograph."""
from pathlib import Path
from PIL import Image

directory = Path(__file__).resolve().parents[1] / "app/static/img"
with Image.open(directory / "kpi-main.png") as source:
    for filename, width in (("kpi-main.webp", 1600), ("kpi-main-mobile.webp", 480)):
        image = source.convert("RGB")
        image.thumbnail((width, width * 2), Image.Resampling.LANCZOS)
        image.save(directory / filename, "WEBP", quality=82, method=6)
        print(filename, (directory / filename).stat().st_size, "bytes")
