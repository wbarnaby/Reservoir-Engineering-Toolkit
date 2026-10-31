"""Main application: console on the left, tool dock on the right"""

from importlib import import_module

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input

from rtk.ui.console import ConsolePane
from rtk.ui.registry import TOOLS
from rtk.ui.theme import PHOSPHOR


class ToolkitApp(App):
    # The whole toolkit in one terminal window.

    CSS_PATH = "theme.tcss"
    TITLE = "Reservoir Toolkit"
    BINDINGS = [
        ("escape", "close_tool", "Close tool"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield ConsolePane(id="console")
            yield Vertical(id="dock")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(PHOSPHOR)
        self.theme = "phosphor"
        self.query_one("#cmd", Input).focus()

    async def open_tool(self, name):
        # Import the tool's panel class and mount it in the dock.
        title, module_path, class_name = TOOLS[name]
        module = import_module(module_path)
        panel_class = getattr(module, class_name)

        dock = self.query_one("#dock")
        await dock.remove_children()
        await dock.mount(panel_class(title))
        dock.add_class("open")

    async def action_close_tool(self) -> None:
        # Remove the open tool and give the console full width.
        dock = self.query_one("#dock")
        await dock.remove_children()
        dock.remove_class("open")
        self.query_one("#cmd", Input).focus()
