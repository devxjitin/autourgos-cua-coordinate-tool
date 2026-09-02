"""
capture.py — optional automatic screenshot capture and screen-size detection.

Both facilities are best-effort and entirely optional, and exist alongside
the fully custom/manual path (a caller-supplied image path/bytes and
explicit screen_width/screen_height), never instead of it:

- capture_screen() needs the optional `mss` dependency
  (`pip install autourgos-cua-coordinate-tool[capture]`) to auto-capture the
  current screen.
- detect_image_size() needs the optional `Pillow` dependency
  (`pip install autourgos-cua-coordinate-tool[images]`) to auto-read the
  pixel dimensions of a caller-supplied image.

Neither is required to use CoordinateFinder with explicit images/dimensions.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Optional, Tuple

__all__ = ["ScreenCapture", "capture_screen", "detect_image_size", "CaptureError"]


class CaptureError(Exception):
    """Raised when automatic screen capture is requested but unavailable."""


@dataclass(frozen=True)
class ScreenCapture:
    image_bytes: bytes
    width: int
    height: int


def capture_screen() -> ScreenCapture:
    """
    Capture the full virtual screen as PNG bytes, with its pixel dimensions.

    Requires the optional `mss` dependency
    (`pip install autourgos-cua-coordinate-tool[capture]`).
    """
    try:
        import mss
        import mss.tools
    except ImportError as exc:
        raise CaptureError(
            "Automatic screenshot capture requires the optional 'mss' dependency. "
            "Install with: pip install autourgos-cua-coordinate-tool[capture]"
        ) from exc

    with mss.MSS() as sct:
        monitor = sct.monitors[0]  # full virtual screen, all monitors combined
        shot = sct.grab(monitor)
        image_bytes = mss.tools.to_png(shot.rgb, shot.size)
        return ScreenCapture(image_bytes=image_bytes, width=shot.width, height=shot.height)


def detect_image_size(image: Any) -> Optional[Tuple[int, int]]:
    """
    Best-effort (width, height) of an already-known image (file path or bytes).

    Returns None (never raises) if Pillow isn't installed, or the image can't
    be read -- callers treat this purely as an optional convenience alongside
    explicit, caller-supplied dimensions.
    """
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        if isinstance(image, (bytes, bytearray)):
            with Image.open(io.BytesIO(image)) as im:
                return im.size
        with Image.open(image) as im:
            return im.size
    except Exception:
        return None
