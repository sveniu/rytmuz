# RYTMUZ

A kid-friendly YouTube music player built with Python, Textualize, yt-dlp, and mpv.

## Features

- **Music-only focus**: Audio playback only, no video distractions
- **Easy search**: Always-available search field with Ctrl+S hotkey
- **Recent songs**: Quick access to recently played songs with Ctrl+R
- **Simple controls**: Play/pause, seek ±10s, volume adjustment
- **Smart caching**: Fast replay of recent songs
- **Visual feedback**: Thumbnails displayed with terminal graphics
- **Kid-friendly**: Safe search enabled, focused on music discovery

## Requirements

- Python 3.10+
- `yt-dlp` command-line tool (does all the heavy lifting for YouTube integration)
- `mpv` media player

## Setup

1. Install system dependencies:
   ```bash
   # Ubuntu/Debian
   sudo apt install yt-dlp mpv

   # macOS
   brew install yt-dlp mpv
   ```

2. Run the app:
   ```bash
   # Using uvx (recommended - no installation needed)
   uvx rytmuz

   # Or using pipx
   pipx run rytmuz

   # Or install with pipx for persistent use
   pipx install rytmuz
   rytmuz
   ```

## Usage

- **Search**: Type in the search box and press Enter, or press Ctrl+S to focus search
- **Play song**: Click on a search result or press Enter when focused
- **Recent songs**: Press Ctrl+R to view recently played songs
- **Controls**:
  - Play/Pause: Click the ⏯ button
  - Seek backward: ⏮ (-10s)
  - Seek forward: ⏭ (+10s)
  - Volume: 🔉/🔊 buttons
- **Quit**: Press Ctrl+C

## Design Decisions

- **No queueing**: Immediate playback on selection (may add later)
- **No auto-next**: Stops after song ends (may add auto-advance at a later point)
- **Minimal playback UI**: No progress bar or timeline to keep focus on the music, not the interface
- **Audio-only**: No visualization to encourage listening and dancing vs screen time
- **Fast replay**: Cached URLs enable instant playback for favorite songs
