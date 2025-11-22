"""Audio playback using yt-dlp and mpv."""
import subprocess
import threading
import socket
import json
import logging
from pathlib import Path
from typing import Optional, Callable
from platformdirs import user_runtime_dir, user_cache_dir

from .cache import AudioCache, AudioFileCache

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Manage audio playback using yt-dlp and mpv."""

    def __init__(self):
        """Initialize the audio player."""
        self.mpv_process: Optional[subprocess.Popen] = None
        self.current_video_id: Optional[str] = None
        self.is_playing: bool = False

        # Use XDG_RUNTIME_DIR for socket (preferred for runtime files)
        # Falls back to cache dir if runtime dir unavailable
        try:
            runtime_dir = Path(user_runtime_dir("rytmuz", ensure_exists=True))
            self._ipc_socket = str(runtime_dir / "mpv_socket")
        except Exception:
            # Fallback to cache dir if runtime dir fails
            cache_dir = Path(user_cache_dir("rytmuz", ensure_exists=True))
            self._ipc_socket = str(cache_dir / "mpv_socket")

        self.cache = AudioCache()
        self.file_cache = AudioFileCache()

    def get_audio_url(self, video_id: str) -> str:
        """Get the direct audio URL using yt-dlp with caching.

        Args:
            video_id: YouTube video ID

        Returns:
            Direct audio stream URL
        """
        # Check cache first
        cached_url = self.cache.get(video_id)
        if cached_url:
            return cached_url

        # Fetch from yt-dlp
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            result = subprocess.run(
                ["yt-dlp", "-g", "-f", "bestaudio", "--force-ipv4", youtube_url],
                capture_output=True,
                text=True,
                check=True,
                timeout=15
            )
            url = result.stdout.strip()

            # Cache the URL
            self.cache.set(video_id, url)

            return url
        except subprocess.CalledProcessError as e:
            raise Exception(f"yt-dlp failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("yt-dlp timed out")

    def play(self, video_id: str, on_end: Optional[Callable] = None) -> None:
        """Start playing audio.

        Args:
            video_id: YouTube video ID to play
            on_end: Optional callback when playback ends
        """
        # Stop current playback if any
        self.stop()

        try:
            # Check for cached audio file first
            cached_file = self.file_cache.get_path(video_id)

            if cached_file:
                # Use cached file - instant playback!
                audio_url = str(cached_file)
                logger.info(f"Playing from cache: {video_id}")
            else:
                # Stream from URL and download in background
                audio_url = self.get_audio_url(video_id)
                logger.info(f"Streaming {video_id}, starting background download")
                # Start background download
                self._download_audio_background(video_id)

            # Start mpv with IPC for control
            # Capture stderr to diagnose intermittent audio issues
            self.mpv_process = subprocess.Popen(
                [
                    "mpv",
                    "--no-video",
                    "--audio-display=no",
                    f"--input-ipc-server={self._ipc_socket}",
                    audio_url
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )

            self.current_video_id = video_id
            self.is_playing = True

            # Monitor stderr for audio issues
            def log_mpv_stderr():
                if self.mpv_process and self.mpv_process.stderr:
                    for line in self.mpv_process.stderr:
                        line = line.strip()
                        if line:
                            logger.info(f"mpv: {line}")

            threading.Thread(target=log_mpv_stderr, daemon=True).start()

            # Monitor playback in background
            if on_end:
                def monitor():
                    if self.mpv_process:
                        self.mpv_process.wait()
                        self.is_playing = False
                        on_end()

                threading.Thread(target=monitor, daemon=True).start()

        except Exception as e:
            raise Exception(f"Failed to start playback: {e}")

    def stop(self) -> None:
        """Stop current playback."""
        if self.mpv_process:
            self.mpv_process.terminate()
            try:
                self.mpv_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.mpv_process.kill()
            self.mpv_process = None

        self.is_playing = False
        self.current_video_id = None

    def toggle_pause(self) -> None:
        """Toggle pause/play state."""
        if self.mpv_process:
            self._send_command(["cycle", "pause"])

    def seek(self, seconds: int) -> None:
        """Seek forward or backward.

        Args:
            seconds: Number of seconds to seek (positive or negative)
        """
        if self.mpv_process:
            self._send_command(["seek", seconds])

    def adjust_volume(self, amount: int) -> None:
        """Adjust volume.

        Args:
            amount: Amount to adjust (positive or negative)
        """
        if self.mpv_process:
            self._send_command(["add", "volume", amount])

    def _send_command(self, command: list) -> None:
        """Send command to mpv via IPC using native Python sockets.

        Args:
            command: MPV command as a list (e.g., ["seek", 10] or ["cycle", "pause"])
        """
        try:
            # Create Unix domain socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)

            # Connect to mpv IPC socket
            sock.connect(self._ipc_socket)

            # Build and send JSON command
            cmd_json = json.dumps({"command": command}) + "\n"
            sock.sendall(cmd_json.encode('utf-8'))

            # Read response (optional, but helps catch errors)
            response = sock.recv(4096).decode('utf-8')
            logger.debug(f"Sent command {command}, response: {response.strip()}")

            sock.close()
        except (socket.error, ConnectionRefusedError, FileNotFoundError) as e:
            logger.warning(f"Failed to send mpv command {command}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending mpv command {command}: {e}")

    def _download_audio_background(self, video_id: str) -> None:
        """Start background download of audio file.

        Args:
            video_id: YouTube video ID to download
        """
        # Start download in background thread
        thread = threading.Thread(
            target=self._download_audio,
            args=(video_id,),
            daemon=True,
            name=f"download-{video_id}"
        )
        thread.start()

    def _download_audio(self, video_id: str) -> None:
        """Download full audio file to cache.

        Args:
            video_id: YouTube video ID to download
        """
        try:
            # Check if already cached
            if self.file_cache.get_path(video_id):
                logger.debug(f"Audio already cached: {video_id}")
                return

            # Create temp file for download in the same directory as cache
            temp_file = self.file_cache.cache_dir / f"{video_id}.tmp.m4a"
            temp_file.parent.mkdir(parents=True, exist_ok=True)

            youtube_url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info(f"Downloading audio for {video_id}")

            # Download using yt-dlp with concurrent fragments for speed
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f", "bestaudio",
                    "--concurrent-fragments", "4",
                    "--force-ipv4",
                    "-o", str(temp_file),
                    youtube_url
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0 and temp_file.exists():
                # Move to cache
                self.file_cache.set(video_id, temp_file)
                logger.info(f"Audio cached successfully: {video_id}")
            else:
                logger.warning(f"Failed to download audio for {video_id}: {result.stderr}")
                # Clean up temp file
                if temp_file.exists():
                    temp_file.unlink()

        except subprocess.TimeoutExpired:
            logger.error(f"Download timeout for {video_id}")
            # Clean up temp file
            temp_file = self.file_cache.cache_dir / f"{video_id}.tmp.m4a"
            if temp_file.exists():
                temp_file.unlink()
        except Exception as e:
            logger.error(f"Download error for {video_id}: {type(e).__name__}: {e}")
            # Clean up temp file
            temp_file = self.file_cache.cache_dir / f"{video_id}.tmp.m4a"
            if temp_file.exists():
                temp_file.unlink()
