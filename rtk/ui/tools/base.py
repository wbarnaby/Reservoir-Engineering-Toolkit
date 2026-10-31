"""Base class every docked tool panel inherits from."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button


class ToolPanel(VerticalScroll):
    # Shared dock behavior: titled border and a close button.

    def __init__(self, title):
        super().__init__()
        self.border_title = title
        self.border_subtitle = "esc to close"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="tool-header"):
            yield Button("close", id="close-tool", classes="close-btn")
        yield from self.compose_body()

    def compose_body(self) -> ComposeResult:
        # Override in each tool to yield that tool's widgets.
        yield from ()

    @on(Button.Pressed, "#close-tool")
    async def close_pressed(self) -> None:
        await self.app.action_close_tool()
