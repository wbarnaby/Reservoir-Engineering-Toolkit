"""Left pane: scrolling output log plus a command input line."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RichLog

from rtk.ui.registry import TOOLS
from rtk.ui.theme import AMBER, BANNER, DIM_GREEN, RED


class ConsolePane(Vertical):
    # Command line: reads commands and prints results.

    def compose(self) -> ComposeResult:
        yield RichLog(id="log", markup=True, wrap=True)
        yield Input(placeholder="type a command (help)", id="cmd")

    def on_mount(self) -> None:
        self.border_title = "CONSOLE"
        self.print_line(BANNER)
        self.print_line(f"[{DIM_GREEN}]Type 'help' for commands.[/]")

    def print_line(self, text):
        # Write one line to the log.
        self.query_one("#log", RichLog).write(text)

    @on(Input.Submitted, "#cmd")
    async def handle_command(self, event: Input.Submitted) -> None:
        command = event.value.strip().lower()
        event.input.clear()
        if not command:
            return

        self.print_line(f"[{AMBER}]>[/] {command}")

        if command in ("help", "?"):
            self.show_help()
        elif command == "clear":
            self.query_one("#log", RichLog).clear()
        elif command == "close":
            await self.app.action_close_tool()
        elif command in ("quit", "exit"):
            self.app.exit()
        elif command in TOOLS:
            await self.app.open_tool(command)
        else:
            self.print_line(f"[{RED}]Unknown command '{command}'[/]")

    def show_help(self):
        # List built-in commands and every registered tool.
        self.print_line("Commands: help, clear, close, quit")
        self.print_line("Tools:")
        for name, (title, _module, _cls) in TOOLS.items():
            self.print_line(f"[{AMBER}]{name:<10}[/] {title}")
