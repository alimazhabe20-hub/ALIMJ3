from typing import Any

# Auto-split part 6: _image_info
def _image_info(image_bytes: bytes) -> dict[str, Any]:
    if Image is None:
        return {}
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            return {
                "format": im.format or "unknown",
                "width": im.width,
                "height": im.height,
                "mode": im.mode,
                "aspect_ratio": round(im.width / max(1, im.height), 3),
            }
    except Exception:
        return {}
