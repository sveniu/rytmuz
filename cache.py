"""Audio URL caching to reduce playback latency."""
import os
import json
import time
import hashlib
from pathlib import Path
from typing import Optional


class AudioCache:
    """Cache audio URLs to speed up playback."""

    def __init__(self, cache_dir: str = ".cache"):
        """Initialize audio cache.

        Args:
            cache_dir: Directory to store cache data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "audio_urls.json"
        self.cache: dict = {}
        self.ttl = 3600 * 6  # 6 hours TTL for URLs
        self.load()

    def load(self) -> None:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def save(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass

    def get(self, video_id: str) -> Optional[str]:
        """Get cached audio URL if available and not expired.

        Args:
            video_id: YouTube video ID

        Returns:
            Cached audio URL or None if not cached or expired
        """
        if video_id in self.cache:
            entry = self.cache[video_id]
            timestamp = entry.get("timestamp", 0)

            # Check if expired
            if time.time() - timestamp < self.ttl:
                return entry.get("url")

            # Remove expired entry
            del self.cache[video_id]
            self.save()

        return None

    def set(self, video_id: str, url: str) -> None:
        """Cache an audio URL.

        Args:
            video_id: YouTube video ID
            url: Direct audio stream URL
        """
        self.cache[video_id] = {
            "url": url,
            "timestamp": time.time()
        }
        self.save()

    def clear_expired(self) -> None:
        """Remove all expired entries from cache."""
        now = time.time()
        expired = [
            vid for vid, entry in self.cache.items()
            if now - entry.get("timestamp", 0) >= self.ttl
        ]

        for vid in expired:
            del self.cache[vid]

        if expired:
            self.save()


class SearchCache:
    """Cache YouTube search results to reduce API quota usage."""

    def __init__(self, cache_dir: str = ".cache", ttl: int = 86400):
        """Initialize search cache.

        Args:
            cache_dir: Directory to store cache data
            ttl: Time to live in seconds (default: 24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "search_results.json"
        self.cache: dict = {}
        self.ttl = ttl
        self.load()

    def load(self) -> None:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def save(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass

    def get(self, query: str) -> Optional[list]:
        """Get cached search results if available and not expired.

        Args:
            query: Search query string (case-insensitive)

        Returns:
            Cached search results or None if not cached or expired
        """
        # Normalize query to lowercase for case-insensitive matching
        key = query.lower().strip()

        if key in self.cache:
            entry = self.cache[key]
            timestamp = entry.get("timestamp", 0)

            # Check if expired
            if time.time() - timestamp < self.ttl:
                return entry.get("results")

            # Remove expired entry
            del self.cache[key]
            self.save()

        return None

    def set(self, query: str, results: list) -> None:
        """Cache search results.

        Args:
            query: Search query string
            results: List of search result dictionaries
        """
        # Normalize query to lowercase for case-insensitive matching
        key = query.lower().strip()

        self.cache[key] = {
            "results": results,
            "timestamp": time.time()
        }
        self.save()

    def clear_expired(self) -> None:
        """Remove all expired entries from cache."""
        now = time.time()
        expired = [
            query for query, entry in self.cache.items()
            if now - entry.get("timestamp", 0) >= self.ttl
        ]

        for query in expired:
            del self.cache[query]

        if expired:
            self.save()


class ThumbnailCache:
    """Cache raw thumbnail images to avoid repeated downloads."""

    def __init__(self, cache_dir: str = ".cache/thumbnails", ttl: int = 604800):
        """Initialize thumbnail cache.

        Args:
            cache_dir: Directory to store cached thumbnails
            ttl: Time to live in seconds (default: 7 days)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata: dict = {}
        self.ttl = ttl
        self.load_metadata()

    def load_metadata(self) -> None:
        """Load cache metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    self.metadata = json.load(f)
            except Exception:
                self.metadata = {}

    def save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
        except Exception:
            pass

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from thumbnail URL.

        Args:
            url: Thumbnail URL

        Returns:
            Hash-based filename for the cached image
        """
        # Use hash of URL as filename to avoid filesystem issues
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"{url_hash}.jpg"

    def get(self, url: str) -> Optional[bytes]:
        """Get cached thumbnail if available and not expired.

        Args:
            url: Thumbnail URL

        Returns:
            Raw image bytes or None if not cached or expired
        """
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / cache_key

        # Check if file exists and metadata is available
        if cache_file.exists() and cache_key in self.metadata:
            timestamp = self.metadata[cache_key].get("timestamp", 0)

            # Check if expired
            if time.time() - timestamp < self.ttl:
                try:
                    with open(cache_file, "rb") as f:
                        return f.read()
                except Exception:
                    pass

            # Remove expired entry
            self._remove(cache_key)

        return None

    def set(self, url: str, image_data: bytes) -> None:
        """Cache raw thumbnail data.

        Args:
            url: Thumbnail URL
            image_data: Raw image bytes
        """
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / cache_key

        try:
            # Write image data
            with open(cache_file, "wb") as f:
                f.write(image_data)

            # Update metadata
            self.metadata[cache_key] = {
                "url": url,
                "timestamp": time.time()
            }
            self.save_metadata()
        except Exception:
            pass

    def _remove(self, cache_key: str) -> None:
        """Remove a cache entry.

        Args:
            cache_key: Cache key to remove
        """
        cache_file = self.cache_dir / cache_key

        # Remove file
        if cache_file.exists():
            try:
                cache_file.unlink()
            except Exception:
                pass

        # Remove metadata
        if cache_key in self.metadata:
            del self.metadata[cache_key]
            self.save_metadata()

    def clear_expired(self) -> None:
        """Remove all expired thumbnail files from cache."""
        now = time.time()
        expired = [
            key for key, entry in self.metadata.items()
            if now - entry.get("timestamp", 0) >= self.ttl
        ]

        for key in expired:
            self._remove(key)
