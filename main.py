import os
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Input, Button, Static, Label, ListItem, ListView
from textual.binding import Binding
from textual.message import Message
from textual import work

from youtube_search import YouTubeSearcher
from thumbnail import download_thumbnail
from player import AudioPlayer
from history import PlayHistory


class SearchResultItem(ListItem):
    """A custom list item for search results."""

    def __init__(self, video_data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_data = video_data


class RytmuzApp(App):
    """A kid-friendly YouTube music player."""

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

    #search-input {
        width: 100%;
    }

    #results-container {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }

    #player-container {
        dock: bottom;
        height: 8;
        padding: 1;
        background: $panel;
    }

    .control-button {
        margin: 0 1;
    }

    #now-playing {
        text-align: center;
        padding: 1;
    }

    #results-list {
        height: 100%;
    }

    SearchResultItem {
        padding: 1;
        height: auto;
    }

    #thumbnail-display {
        width: auto;
        height: auto;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "focus_search", "Focus Search", show=True),
        Binding("ctrl+r", "show_recent", "Recent Songs", show=True),
        Binding("ctrl+c", "quit", "Quit", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="search-container"):
            yield Input(placeholder="Search for music...", id="search-input")

        with Vertical(id="results-container"):
            yield ListView(id="results-list")

        with Container(id="player-container"):
            with Horizontal():
                yield Static("", id="thumbnail-display")
                with Vertical():
                    yield Label("No song playing", id="now-playing")
                    with Horizontal():
                        yield Button("⏮ -10s", id="seek-back", classes="control-button")
                        yield Button("⏯ Play/Pause", id="play-pause", classes="control-button")
                        yield Button("⏭ +10s", id="seek-forward", classes="control-button")
                        yield Button("🔉 Vol-", id="vol-down", classes="control-button")
                        yield Button("🔊 Vol+", id="vol-up", classes="control-button")

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    def action_show_recent(self) -> None:
        """Show recent songs."""
        results_list = self.query_one("#results-list", ListView)
        results_list.clear()

        recent_songs = self.history.get_recent(20)

        if not recent_songs:
            results_list.append(ListItem(Label("No recent songs")))
            return

        for song in recent_songs:
            title = song["title"]
            channel = song["channel"]
            item_label = Label(f"{title}\n[dim]{channel}[/dim]")
            item = SearchResultItem(song, item_label)
            results_list.append(item)

    def on_mount(self) -> None:
        """Called when app starts."""
        self.query_one("#search-input", Input).focus()

        # Initialize YouTube searcher
        api_key_file = "api_key"
        if os.path.exists(api_key_file):
            with open(api_key_file) as f:
                api_key = f.read().strip()
            self.searcher = YouTubeSearcher(api_key)
        else:
            self.searcher = YouTubeSearcher()

        # Initialize audio player
        self.player = AudioPlayer()

        # Initialize play history
        self.history = PlayHistory()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search when user presses Enter."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
                self.perform_search(query)

    @work(thread=True)
    def perform_search(self, query: str) -> None:
        """Perform a YouTube search and display results."""
        try:
            results = self.searcher.search(query, max_results=15)

            # Clear results list from main thread
            def clear_results():
                results_list = self.query_one("#results-list", ListView)
                results_list.clear()

            self.call_from_thread(clear_results)

            if not results:
                def add_no_results():
                    results_list = self.query_one("#results-list", ListView)
                    results_list.append(ListItem(Label("No results found")))
                self.call_from_thread(add_no_results)
                return

            for result in results:
                title = result["title"]
                channel = result["channel"]

                def add_result(r=result):
                    results_list = self.query_one("#results-list", ListView)
                    item_label = Label(f"{r['title']}\n[dim]{r['channel']}[/dim]")
                    item = SearchResultItem(r, item_label)
                    results_list.append(item)

                self.call_from_thread(add_result)

        except Exception as e:
            def add_error():
                results_list = self.query_one("#results-list", ListView)
                results_list.append(ListItem(Label(f"[red]Error: {e}[/red]")))
            self.call_from_thread(add_error)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle when a search result is selected."""
        if isinstance(event.item, SearchResultItem):
            video_data = event.item.video_data
            self.play_video(video_data)

    @work(thread=True)
    def play_video(self, video_data: dict) -> None:
        """Start playing a video."""
        video_id = video_data["video_id"]
        title = video_data["title"]
        thumbnail_url = video_data["thumbnail_url"]

        now_playing = self.query_one("#now-playing", Label)
        self.call_from_thread(now_playing.update, f"Loading: {title}")

        try:
            # Download and display thumbnail
            thumbnail = download_thumbnail(thumbnail_url, max_width=30)
            thumbnail_display = self.query_one("#thumbnail-display", Static)
            self.call_from_thread(thumbnail_display.update, thumbnail)

            self.player.play(video_id)
            self.call_from_thread(now_playing.update, f"▶ Playing: {title}")

            # Add to history
            self.history.add(video_data)
        except Exception as e:
            self.call_from_thread(now_playing.update, f"Error: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id

        if button_id == "play-pause":
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
    app = RytmuzApp()
    app.run()


if __name__ == "__main__":
    main()
