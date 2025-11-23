"""Audio playback using yt-dlp and mpv."""
import subprocess
import threading
import socket
import json
import logging
from pathlib import Path
from typing import Optional, Callable

from .cache import AudioCache, AudioFileCache

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Manage audio playback using yt-dlp and mpv."""

    def __init__(self):
        """Initialize the audio player."""
        self.mpv_process: Optional[subprocess.Popen] = None
        self.current_video_id: Optional[str] = None
        self.is_playing: bool = False

        # Create socketpair for IPC with mpv
        # This bypasses snap filesystem restrictions since no path is needed
        self._ipc_socket: Optional[socket.socket] = None
        self._mpv_socket: Optional[socket.socket] = None
        self._create_socketpair()

        self.cache = AudioCache()
        self.file_cache = AudioFileCache()

    def _create_socketpair(self):
        """Create a new socketpair for IPC communication."""
        # Close existing sockets if any
        if self._ipc_socket:
            try:
                self._ipc_socket.close()
            except Exception:
                pass
        if self._mpv_socket:
            try:
                self._mpv_socket.close()
            except Exception:
                pass

        # Create new socketpair
        self._ipc_socket, self._mpv_socket = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

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
                ["yt-dlp", "-g", "-f", "bestaudio", youtube_url],
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
                file_exists = cached_file.exists() if hasattr(cached_file, 'exists') else Path(audio_url).exists()
                logger.info(f"Playing from cache: {video_id}, path={audio_url}, exists={file_exists}")
            else:
                # Stream from URL and download in background
                audio_url = self.get_audio_url(video_id)
                logger.info(f"Streaming {video_id}, starting background download")
                # Start background download
                self._download_audio_background(video_id)

            # Create new socketpair for this mpv instance
            self._create_socketpair()

            # Start mpv with IPC for control using socketpair
            # Capture stderr to diagnose intermittent audio issues
            mpv_fd = self._mpv_socket.fileno()
            mpv_cmd = [
                "mpv",
                "--no-video",
                "--audio-display=no",
                "--network-timeout=5",
                f"--input-ipc-client=fd://{mpv_fd}",
                audio_url
            ]
            logger.debug(f"Starting mpv: {' '.join(mpv_cmd)}")

            self.mpv_process = subprocess.Popen(
                mpv_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                pass_fds=(mpv_fd,)
            )

            # Close mpv's socket end in our process (mpv inherited it)
            self._mpv_socket.close()
            self._mpv_socket = None

            self.current_video_id = video_id
            self.is_playing = True

            # Monitor stderr and exit code
            def monitor_mpv():
                if not self.mpv_process or not self.mpv_process.stderr:
                    return

                # Read all stderr output
                for line in self.mpv_process.stderr:
                    line = line.strip()
                    if line:
                        logger.info(f"mpv stderr: {line}")

                # Wait for process to exit and log exit code
                exit_code = self.mpv_process.wait()
                logger.info(f"mpv exited with code {exit_code} (video_id={self.current_video_id})")

                self.is_playing = False

                # Call end callback if provided
                if on_end:
                    on_end()

            threading.Thread(target=monitor_mpv, daemon=True).start()

            # Give mpv a moment to start, then check if it's still running
            import time
            time.sleep(0.1)
            poll_result = self.mpv_process.poll()
            if poll_result is not None:
                logger.error(f"mpv exited immediately with code {poll_result}")

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

        # Close IPC socket
        if self._ipc_socket:
            try:
                self._ipc_socket.close()
            except Exception:
                pass
            self._ipc_socket = None

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
        """Send command to mpv via IPC using socketpair.

        Args:
            command: MPV command as a list (e.g., ["seek", 10] or ["cycle", "pause"])
        """
        if not self._ipc_socket or not self.mpv_process:
            logger.warning(f"Cannot send command {command}: no active mpv process")
            return

        try:
            # Build and send JSON command
            cmd_json = json.dumps({"command": command}) + "\n"
            self._ipc_socket.sendall(cmd_json.encode('utf-8'))

            # Set non-blocking to read available responses without hanging
            self._ipc_socket.setblocking(False)
            try:
                response = self._ipc_socket.recv(4096).decode('utf-8')
                logger.debug(f"Sent command {command}, response: {response.strip()}")
            except BlockingIOError:
                # No immediate response available, that's okay
                logger.debug(f"Sent command {command}, no immediate response")
            finally:
                # Restore blocking mode
                self._ipc_socket.setblocking(True)

        except (socket.error, BrokenPipeError) as e:
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
