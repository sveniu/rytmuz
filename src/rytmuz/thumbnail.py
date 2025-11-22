"""Thumbnail downloading and display utilities."""
import io
import logging
import requests
from PIL import Image
from rich_pixels import Pixels

from cache import ThumbnailCache

logger = logging.getLogger(__name__)

# Disk cache for raw thumbnail images
_raw_cache = ThumbnailCache()

# In-memory cache for processed thumbnails
# Key: (url, max_width) -> Value: Pixels object
_thumbnail_cache: dict[tuple[str, int], Pixels] = {}


def download_thumbnail(url: str, max_width: int = 40) -> str:
    """Download and convert a thumbnail to a text-based image.

    Args:
        url: URL to the thumbnail image
        max_width: Maximum width in characters (default: 40)

    Returns:
        Renderable text representation of the image
    """
    # Check in-memory processed cache first
    cache_key = (url, max_width)
    if cache_key in _thumbnail_cache:
        logger.debug(f"In-memory thumbnail cache hit: {url[:50]}... (width={max_width})")
        return _thumbnail_cache[cache_key]

    try:
        # Try to get raw image from disk cache
        raw_data = _raw_cache.get(url)

        if raw_data is None:
            # Not cached, download from URL
            logger.debug(f"Downloading thumbnail from URL: {url[:50]}...")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            raw_data = response.content

            # Cache the raw data
            _raw_cache.set(url, raw_data)

        # Process the raw image
        image = Image.open(io.BytesIO(raw_data))

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

        # Cache the result
        _thumbnail_cache[cache_key] = pixels
        logger.debug(f"Processed and cached thumbnail: {url[:50]}... (width={max_width})")

        return pixels

    except Exception as e:
        logger.warning(f"Failed to load thumbnail from {url[:50]}...: {e}")
        return f"[dim]Could not load thumbnail: {e}[/dim]"
