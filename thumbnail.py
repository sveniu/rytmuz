"""Thumbnail downloading and display utilities."""
import io
import requests
from PIL import Image
from rich_pixels import Pixels


def download_thumbnail(url: str, max_width: int = 40) -> str:
    """Download and convert a thumbnail to a text-based image.

    Args:
        url: URL to the thumbnail image
        max_width: Maximum width in characters (default: 40)

    Returns:
        Renderable text representation of the image
    """
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content))

        # Resize to fit terminal width
        # rich-pixels uses half-block characters (fg=top, bg=bottom) for 2x vertical resolution
        # So each character represents 1 pixel width × 2 pixels height
        aspect_ratio = image.height / image.width
        new_width = max_width  # No hard cap - scale with terminal size
        # To maintain aspect ratio: if image is W×H, we want new_width chars × new_height chars
        # where new_width × 1 : new_height × 2 = W : H (accounting for char aspect ~2:1)
        # Therefore: new_height = (new_width × H) / (2 × W) = new_width × aspect_ratio / 2
        new_height = int(new_width * aspect_ratio * 0.5)

        # Only double height, not width - rich-pixels uses half-blocks for vertical resolution
        # but horizontally it's 1 char = 1 pixel
        image = image.resize((new_width, new_height * 2), Image.Resampling.LANCZOS)

        # Convert to text representation
        pixels = Pixels.from_image(image)
        return pixels

    except Exception as e:
        return f"[dim]Could not load thumbnail: {e}[/dim]"
