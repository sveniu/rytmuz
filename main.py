from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Input, Button, Static, Label
from textual.binding import Binding


class RytmuzApp(App):
    """A kid-friendly YouTube music player."""

    CSS = """
    Screen {
        align: center top;
    }

    #search-container {
        dock: top;
        height: auto;
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
        height: auto;
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
    """

    BINDINGS = [
        Binding("ctrl+s", "focus_search", "Focus Search", show=True),
        Binding("ctrl+c", "quit", "Quit", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="search-container"):
            yield Input(placeholder="Search for music...", id="search-input")

        with Vertical(id="results-container"):
            yield Label("Search for music to start playing", id="results-label")

        with Container(id="player-container"):
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

    def on_mount(self) -> None:
        """Called when app starts."""
        self.query_one("#search-input", Input).focus()


def main():
    app = RytmuzApp()
    app.run()


if __name__ == "__main__":
    main()
