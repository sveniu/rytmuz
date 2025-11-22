import os
import sys
import logging
from shutil import which
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Input, Button, Static, Label, LoadingIndicator
from textual.binding import Binding
from textual.message import Message
from textual.screen import ModalScreen
from textual import work
from textual.logging import TextualHandler

from .youtube_search import YouTubeSearcher
from .thumbnail import download_thumbnail
from .player import AudioPlayer
from .history import PlayHistory
from .i18n import _

# Configure logging at module import time (not in main())
# This ensures logging works both when running via main() and
# when Textual imports 'app' directly (textual run --dev rytmuz)
# Use WARNING level for normal users, DEBUG only if RYTMUZ_DEBUG is set
log_level = "DEBUG" if os.environ.get("RYTMUZ_DEBUG") else "WARNING"
logging.basicConfig(
    level=log_level,
    handlers=[TextualHandler()],
)


def check_external_dependencies() -> None:
    """Check if required external tools are installed.

    Exits with status 1 if any required dependencies are missing.
    """
    missing = []

    if which("yt-dlp") is None:
        missing.append("yt-dlp")

    if which("mpv") is None:
        missing.append("mpv")

    if missing:
        print("Error: Missing required dependencies:", ", ".join(missing), file=sys.stderr)
        print("\nPlease install them:", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt install yt-dlp mpv", file=sys.stderr)
        print("  macOS: brew install yt-dlp mpv", file=sys.stderr)
        print("  Windows: scoop install yt-dlp mpv", file=sys.stderr)
        print("\nOr install yt-dlp via pipx: pipx install yt-dlp", file=sys.stderr)
        sys.exit(1)


class HelpScreen(ModalScreen):
    """Modal screen showing keyboard shortcuts and help information."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("f1", "dismiss", "Close", show=False),
        Binding("q", "dismiss", "Close", show=False),
        Binding("h", "dismiss", "Close", show=False),
        Binding("question_mark", "dismiss", "Close", show=False),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 80;
        height: auto;
        max-height: 90%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #help-content {
        height: auto;
        padding: 0 1;
    }

    .help-section {
        margin-top: 1;
    }

    .help-section-title {
        text-style: bold;
        color: $accent;
    }

    .help-item {
        margin-left: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create help dialog contents."""
        with Container(id="help-dialog"):
            yield Label(_("help_title"), id="help-title")
            with ScrollableContainer(id="help-content"):
                # Keyboard shortcuts
                yield Static(_("help_keyboard_shortcuts"), classes="help-section-title")
                yield Static(f"  {_('help_ctrl_s')}", classes="help-item")
                yield Static(f"  {_('help_ctrl_r')}", classes="help-item")
                yield Static(f"  {_('help_space')}", classes="help-item")
                yield Static(f"  {_('help_escape')}", classes="help-item")
                yield Static(f"  {_('help_f1')}", classes="help-item")
                yield Static(f"  {_('help_h')}", classes="help-item")
                yield Static(f"  {_('help_ctrl_c')}", classes="help-item")

                # Player controls
                yield Static("", classes="help-section")
                yield Static(_("help_player_controls"), classes="help-section-title")
                yield Static(f"  {_('help_seek_back')}", classes="help-item")
                yield Static(f"  {_('help_play_pause')}", classes="help-item")
                yield Static(f"  {_('help_seek_forward')}", classes="help-item")
                yield Static(f"  {_('help_vol_down')}", classes="help-item")
                yield Static(f"  {_('help_vol_up')}", classes="help-item")

                # Usage tips
                yield Static("", classes="help-section")
                yield Static(_("help_usage_tips"), classes="help-section-title")
                yield Static(f"  {_('help_tip_search')}", classes="help-item")
                yield Static(f"  {_('help_tip_play')}", classes="help-item")
                yield Static(f"  {_('help_tip_cache')}", classes="help-item")
                yield Static(f"  {_('help_tip_escape')}", classes="help-item")

                yield Static("", classes="help-section")
                yield Static(_("help_close"), classes="help-item")

    def action_dismiss(self) -> None:
        """Close the help screen."""
        self.dismiss()


class ResultCard(Static):
    """A card showing a search result with thumbnail and title."""

    def __init__(self, video_data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_data = video_data
        self.add_class("result-card")

    def compose(self) -> ComposeResult:
        """Create card contents."""
        yield Static(_("loading"), classes="card-thumbnail")
        yield Label(self.video_data["title"], classes="card-title")

    def on_click(self) -> None:
        """Handle card click."""
        self.post_message(ResultCard.Selected(self))

    class Selected(Message):
        """Posted when a result card is clicked."""

        def __init__(self, card: "ResultCard"):
            super().__init__()
            self.card = card


class RytmuzApp(App):
    """A kid-friendly YouTube music player."""

    # Debug mode - toggle with Ctrl+D
    debug_mode = False

    # Currently selected search result
    selected_video_data: dict | None = None

    CSS = """
    Screen {
        align: center top;
    }

    #search-container {
        dock: top;
        height: 5;
        padding: 1;
        background: $panel;
    }

    #search-bar {
        width: 100%;
        height: 100%;
    }

    #search-input {
        width: 1fr;
    }

    #help-button {
        width: 5;
        min-width: 5;
        margin-left: 1;
    }

    #main-content {
        height: 1fr;
        padding: 0;
        margin: 0;
    }

    #results-container {
        height: 1fr;
        width: 100%;
    }

    #loading-container {
        height: 1fr;
        width: 100%;
        align: center middle;
        content-align: center middle;
    }

    #results-grid {
        height: auto;
        layout: grid;
        grid-size: 2;
        grid-gutter: 1 1;
        padding: 1;
    }

    .result-card {
        height: auto;
        min-height: 15;
        border: solid $primary;
        padding: 1;
        background: $surface;
    }

    .result-card:hover {
        background: $boost;
        border: solid $accent;
    }

    .card-thumbnail {
        width: 100%;
        height: auto;
        text-align: center;
    }

    .card-title {
        width: 100%;
        height: auto;
        text-align: center;
        padding: 1 0 0 0;
    }

    #player-view {
        height: 1fr;
        width: 100%;
        layout: vertical;
    }

    #player-content {
        width: 100%;
        height: 1fr;
        overflow: hidden;
        align: center middle;
        content-align: center middle;
    }

    #player-thumbnail {
        width: 100%;
        height: auto;
        margin: 0;
        padding: 0;
        align: center middle;
        content-align: center middle;
    }

    #now-playing {
        text-align: center;
        margin: 0 0 1 0;
        padding: 0;
        width: 100%;
        height: auto;
    }

    #controls-container {
        align: center middle;
        width: 100%;
        height: 3;
        content-align: center middle;
        margin: 0;
        padding: 0;
    }

    .control-button {
        margin: 0 1;
    }

    .hidden {
        display: none;
    }

    #debug-info {
        dock: bottom;
        height: 1;
        background: $panel;
        text-align: center;
        color: $text-muted;
        display: none;
    }

    #debug-info.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "focus_search", _("focus_search"), show=True),
        Binding("ctrl+r", "show_recent", _("recent_songs"), show=True),
        Binding("space", "toggle_playback", _("play_pause"), show=True),
        Binding("f1", "show_help", "Help", show=True),
        Binding("h", "show_help", "Help", show=False),
        Binding("question_mark", "show_help", "Help", show=False),
        Binding("escape", "back_to_player", _("back_to_player"), show=True),
        Binding("ctrl+d", "toggle_debug", _("debug"), show=False),
        Binding("ctrl+c", "quit", _("quit"), show=True),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="search-container"):
            with Horizontal(id="search-bar"):
                yield Input(placeholder=_("search_placeholder"), id="search-input")
                yield Button("?", id="help-button")

        with Container(id="main-content"):
            # Results grid view
            yield ScrollableContainer(Vertical(id="results-grid"), id="results-container")

            # Loading indicator (shown during search)
            with Container(id="loading-container", classes="hidden"):
                yield LoadingIndicator(id="loading-indicator")

            # Player view (shown during playback)
            with Vertical(id="player-view", classes="hidden"):
                with Container(id="player-content"):
                    yield Static("", id="player-thumbnail")
                yield Label(_("loading"), id="now-playing")
                with Horizontal(id="controls-container"):
                    yield Button(_("seek_back"), id="seek-back", classes="control-button")
                    yield Button(_("play_pause"), id="play-pause", classes="control-button")
                    yield Button(_("seek_forward"), id="seek-forward", classes="control-button")
                    yield Button(_("vol_down"), id="vol-down", classes="control-button")
                    yield Button(_("vol_up"), id="vol-up", classes="control-button")

        # Debug info at bottom
        yield Label("", id="debug-info")

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        self.debug_mode = not self.debug_mode
        debug_label = self.query_one("#debug-info", Label)
        if self.debug_mode:
            debug_label.add_class("visible")
        else:
            debug_label.remove_class("visible")

    def action_toggle_playback(self) -> None:
        """Toggle play/pause."""
        self.player.toggle_pause()

    def action_show_help(self) -> None:
        """Show help modal."""
        self.push_screen(HelpScreen())

    def action_focus_search(self) -> None:
        """Focus the search input and show results view."""
        # Show results view, hide player view
        self.query_one("#results-container").remove_class("hidden")
        self.query_one("#player-view").add_class("hidden")
        self.query_one("#search-input", Input).focus()

    def action_back_to_player(self) -> None:
        """Return to player view if music is playing."""
        # Only switch if player view has content (something is playing)
        if self.player.is_playing:
            self.query_one("#results-container").add_class("hidden")
            self.query_one("#player-view").remove_class("hidden")

    def action_show_recent(self) -> None:
        """Show recent songs."""
        # Show results view, hide player view
        self.query_one("#results-container").remove_class("hidden")
        self.query_one("#player-view").add_class("hidden")

        # Clear results and load recent songs
        def clear_results():
            results_grid = self.query_one("#results-grid", Vertical)
            results_grid.remove_children()

        clear_results()
        self.load_recent_songs()

    @work(thread=True)
    def load_recent_songs(self) -> None:
        """Load and display recent songs with thumbnails."""
        recent_songs = self.history.get_recent(20)

        if not recent_songs:
            def add_no_songs():
                results_grid = self.query_one("#results-grid", Vertical)
                results_grid.mount(Label(_("no_recent_songs")))
            self.call_from_thread(add_no_songs)
            return

        # Calculate thumbnail width
        terminal_width = self.size.width
        max_width = max(20, int(terminal_width / 2) - 4)

        for song in recent_songs:
            # Load thumbnail (synchronously in this worker thread)
            thumbnail = download_thumbnail(song["thumbnail_url"], max_width=max_width)

            def add_card(s=song, thumb=thumbnail):
                results_grid = self.query_one("#results-grid", Vertical)
                card = ResultCard(s)
                results_grid.mount(card)
                # Update thumbnail immediately
                try:
                    thumb_static = card.query_one(".card-thumbnail", Static)
                    thumb_static.update(thumb)
                except Exception as e:
                    self.log(f"Error updating thumbnail: {e}")

            self.call_from_thread(add_card)

    def on_mount(self) -> None:
        """Called when app starts."""
        self.log("=" * 80)
        self.log("RYTMUZ starting up")
        self.log(f"Textual version: {self.app.TEXTUAL_VERSION if hasattr(self.app, 'TEXTUAL_VERSION') else 'unknown'}")
        self.query_one("#search-input", Input).focus()

        # Check for mock mode (for development without API quota usage)
        mock_mode = os.environ.get("RYTMUZ_MOCK_MODE", "").lower() in ("1", "true", "yes")

        # Initialize YouTube searcher
        if mock_mode:
            self.searcher = YouTubeSearcher(mock_mode=True)
            self.log("YouTube searcher initialized in MOCK MODE (no API calls)")
        else:
            # Use API key from environment variable only
            self.searcher = YouTubeSearcher()
            self.log("YouTube searcher initialized (will use API key from env if available, otherwise yt-dlp fallback)")

        # Initialize audio player
        self.player = AudioPlayer()
        self.log("Audio player initialized")

        # Initialize play history
        self.history = PlayHistory()
        self.log(f"Play history loaded: {len(self.history.get_recent(50))} songs")

    def on_unmount(self) -> None:
        """Called when app exits - cleanup."""
        self.log("RYTMUZ shutting down")
        # Stop any playing audio
        if hasattr(self, 'player'):
            self.player.stop()
            self.log("Audio player stopped")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search when user presses Enter."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
                self.log(f"User submitted search query: '{query}'")
                # Show loading indicator
                self.query_one("#loading-container").remove_class("hidden")
                self.query_one("#results-container").add_class("hidden")
                self.query_one("#player-view").add_class("hidden")
                # Clear old results immediately
                results_grid = self.query_one("#results-grid", Vertical)
                results_grid.remove_children()
                self.perform_search(query)

    @work(thread=True)
    def perform_search(self, query: str) -> None:
        """Perform a YouTube search and display results."""
        try:
            results = self.searcher.search(query, max_results=20)

            # Hide loading indicator, show results
            def show_results():
                self.query_one("#loading-container").add_class("hidden")
                self.query_one("#results-container").remove_class("hidden")
                results_grid = self.query_one("#results-grid", Vertical)
                results_grid.remove_children()

            self.call_from_thread(show_results)

            if not results:
                def add_no_results():
                    results_grid = self.query_one("#results-grid", Vertical)
                    results_grid.mount(Label(_("no_results")))
                self.call_from_thread(add_no_results)
                return

            # Calculate thumbnail width based on terminal
            terminal_width = self.size.width
            max_width = max(20, int(terminal_width / 2) - 4)

            for result in results:
                # Load thumbnail (synchronously in this worker thread)
                thumbnail = download_thumbnail(result["thumbnail_url"], max_width=max_width)

                def add_result(r=result, thumb=thumbnail):
                    results_grid = self.query_one("#results-grid", Vertical)
                    card = ResultCard(r)
                    results_grid.mount(card)
                    # Update thumbnail immediately
                    try:
                        thumb_static = card.query_one(".card-thumbnail", Static)
                        thumb_static.update(thumb)
                    except Exception as e:
                        self.log(f"Error updating thumbnail: {e}")

                self.call_from_thread(add_result)

        except Exception as e:
            def show_error():
                self.query_one("#loading-container").add_class("hidden")
                self.query_one("#results-container").remove_class("hidden")
                results_grid = self.query_one("#results-grid", Vertical)
                results_grid.mount(Label(f"[red]{_('error', error=str(e))}[/red]"))
            self.call_from_thread(show_error)

    async def on_result_card_selected(self, event: ResultCard.Selected) -> None:
        """Handle when a result card is clicked."""
        video_data = event.card.video_data
        # Hide results, show player view
        self.query_one("#results-container").add_class("hidden")
        self.query_one("#player-view").remove_class("hidden")

        # Simple approach: size based on width, let layout constrain height
        terminal_width = self.size.width
        # Use 60% of terminal width
        thumb_width = int(terminal_width * 0.6)

        self.play_video(video_data, thumb_width)

    @work(thread=True)
    def play_video(self, video_data: dict, thumb_width: int) -> None:
        """Start playing a video."""
        video_id = video_data["video_id"]
        title = video_data["title"]
        thumbnail_url = video_data["thumbnail_url"]

        def update_status(msg):
            now_playing = self.query_one("#now-playing", Label)
            now_playing.update(msg)

        def log_msg(msg):
            self.call_from_thread(self.log, msg)

        log_msg(f"Starting playback: '{title}' (video_id={video_id})")
        self.call_from_thread(update_status, _("loading_title", title=title))

        try:
            # Download and display thumbnail at calculated size
            log_msg(f"Downloading thumbnail (width={thumb_width})")
            thumbnail = download_thumbnail(thumbnail_url, max_width=thumb_width)

            def update_thumbnail():
                thumbnail_display = self.query_one("#player-thumbnail", Static)
                thumbnail_display.update(thumbnail)

            self.call_from_thread(update_thumbnail)
            log_msg("Thumbnail displayed")

            log_msg("Starting mpv playback")
            self.player.play(video_id)
            self.call_from_thread(update_status, _("playing_title", title=title))
            log_msg("Playback started successfully")

            # Add to history
            self.history.add(video_data)
            log_msg("Added to play history")
        except Exception as e:
            log_msg(f"Playback error: {type(e).__name__}: {e}")
            self.call_from_thread(update_status, _("error", error=str(e)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id

        if button_id == "help-button":
            self.action_show_help()
        elif button_id == "play-pause":
            self.player.toggle_pause()
        elif button_id == "seek-back":
            self.player.seek(-10)
        elif button_id == "seek-forward":
            self.player.seek(10)
        elif button_id == "vol-down":
            self.player.adjust_volume(-5)
        elif button_id == "vol-up":
            self.player.adjust_volume(5)


def main():
    # Check for required external dependencies before starting
    check_external_dependencies()

    app = RytmuzApp()
    app.run()


if __name__ == "__main__":
    main()
