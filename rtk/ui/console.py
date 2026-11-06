"""Left pane: scrolling output log plus a command input line.

The console has these modes:
    "command"        normal tool commands
    "key"            waiting for an API key (input is masked)
    "access_id"      browser only: waiting for an Access Client ID
    "access_secret"  browser only: waiting for its secret (input is masked)
    "chat"           messages go to the AI assistant
"""

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input

from rtk.ui.chatlog import GRAPHICS, ChatLog
from rtk.ui.meter import UsageMeterWidget
from rtk.ui.registry import TOOLS
from rtk.ui.theme import AMBER, BANNER, DIM_GREEN, GREEN, RED

COMMAND_HINT = "type a command (help)"
CHAT_HINT = "ask the assistant (:clear resets, :exit leaves)"
KEY_HINT = "paste your Anthropic API key (:exit cancels)"
ACCESS_ID_HINT = "enter your Client ID (:exit cancels)"
ACCESS_SECRET_HINT = "enter your Client Secret (:exit cancels)"


class ConsolePane(Vertical):
    # Command line: reads commands and prints results.

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "command"
        self.api_key = None  # kept in memory only, never written to disk
        self.access_id = None  # browser only, also never written to disk
        self.session = None  # ChatSession once AI mode starts
        self.meter = None
        self.busy = False  # True while a reply is streaming

    def compose(self) -> ComposeResult:
        yield ChatLog(id="log")
        yield UsageMeterWidget(id="meter")
        yield Input(placeholder=COMMAND_HINT, id="cmd")

    def on_mount(self) -> None:
        self.border_title = "CONSOLE"
        self.print_line(BANNER)
        self.print_line(f"[{DIM_GREEN}]Type 'help' for commands.[/]")

    def print_line(self, text):
        # Write one line to the log (a markup string or a rich Text).
        self.query_one("#log", ChatLog).write(text)

    def set_mode(self, mode):
        # Switch modes and update the input box to match.
        self.mode = mode
        box = self.query_one("#cmd", Input)
        box.password = mode in ("key", "access_secret")
        if mode == "command":
            box.placeholder = COMMAND_HINT
            self.border_title = "CONSOLE"
        elif mode == "key":
            box.placeholder = KEY_HINT
            self.border_title = "CONSOLE: AI SETUP"
        elif mode == "access_id":
            box.placeholder = ACCESS_ID_HINT
            self.border_title = "CONSOLE: AI SETUP"
        elif mode == "access_secret":
            box.placeholder = ACCESS_SECRET_HINT
            self.border_title = "CONSOLE: AI SETUP"
        else:
            box.placeholder = CHAT_HINT
            self.border_title = "CONSOLE : AI"

    # ------------ input routing ------------

    @on(Input.Submitted, "#cmd")
    async def handle_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.clear()
        if not text:
            return

        if self.mode == "key":
            self.receive_key(text)
        elif self.mode == "access_id":
            self.receive_access_id(text)
        elif self.mode == "access_secret":
            self.receive_access_secret(text)
        elif self.mode == "chat":
            self.chat_input(text)
        else:
            await self.run_command(text)

    async def run_command(self, text):
        # Normal command mode.
        command = text.lower()
        self.print_line(f"[{AMBER}]>[/] {command}")

        if command in ("help", "?"):
            self.show_help()
        elif command == "clear":
            self.query_one("#log", ChatLog).clear()
        elif command == "close":
            await self.app.action_close_tool()
        elif command in ("quit", "exit"):
            self.app.exit()
        elif command == "ai":  # secret: not listed in help
            self.start_ai()
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

    # ---------- AI mode ----------

    def start_ai(self):
        # Enter AI mode, asking for a key first if none is available.
        from rtk.assistant.config import IN_BROWSER, key_from_environment

        if IN_BROWSER:
            self.print_line(
                f"[{DIM_GREEN}]AI assistant needs Cloudflare Access "
                "credentials.[/]"
            )
            self.set_mode("access_id")
            return

        if self.api_key is None:
            self.api_key = key_from_environment()

        if self.api_key is None:
            self.print_line(
                f"[{DIM_GREEN}]AI assistant needs your API key.[/]"
            )
            self.set_mode("key")
        else:
            self.open_session()

    def receive_key(self, text):
        # Handle what was typed in key mode.
        from rtk.assistant.config import looks_like_key

        if text == ":exit":
            self.set_mode("command")
            return
        if not looks_like_key(text):
            self.print_line(
                Text("That does not look like a key (sk-ant-...).", RED)
            )
            return

        self.api_key = text
        self.open_session()

    def receive_access_id(self, text):
        # Handle the Client ID, the "username" of an Access service token.
        if text == ":exit":
            self.set_mode("command")
            return
        self.access_id = text
        self.set_mode("access_secret")

    def receive_access_secret(self, text):
        # Handle the Client Secret, then ask Access to approve the pair.
        client_id, self.access_id = self.access_id, None
        self.set_mode("command")
        if text != ":exit":
            self.check_access(client_id, text)

    @work(exclusive=True, group="ai")
    async def check_access(self, client_id, client_secret):
        """Open AI mode only once Cloudflare Access approves."""
        from rtk.assistant.web_session import GatewayError, WebChatSession

        self.print_line(Text("Checking with Cloudflare Access...", DIM_GREEN))
        session = WebChatSession(client_id, client_secret)
        try:
            await session.verify()
        except GatewayError as err:
            self.print_line(Text(str(err), style=RED))
        else:
            self.open_session(session)

    def open_session(self, session=None):
        # Create the chat session and switch to chat mode.
        # imported here so the app starts fast and works without the
        # anthropic package until AI mode is actually used
        from rtk.assistant.config import MODEL
        from rtk.assistant.usage import UsageMeter

        if session is None:
            from rtk.assistant.session import ChatSession

            session = ChatSession(self.api_key)
        self.session = session
        self.meter = UsageMeter(MODEL)
        self.query_one("#meter", UsageMeterWidget).show(self.meter)
        self.set_mode("chat")
        self.print_line(Text("AI assistant ready.", style=f"bold {GREEN}"))

    def chat_input(self, text):
        # Handle what was typed in chat mode.
        if text == ":exit":
            self.set_mode("command")
            self.print_line(Text("Left AI mode.", DIM_GREEN))
        elif text == ":clear":
            self.session.reset()
            self.meter.reset()
            self.query_one("#meter", UsageMeterWidget).show(self.meter)
            self.print_line(Text("Conversation cleared.", DIM_GREEN))
        elif self.busy:
            self.notify("Still answering, please wait", severity="warning")
        else:
            self.ask(text)

    @work(exclusive=True, group="ai")
    async def ask(self, text):
        """Stream one reply into the log: text lines and LaTeX images."""
        from rtk.assistant.latex import MathStreamer

        self.busy = True
        self.print_line(Text(f"you> {text}", style=AMBER))

        streamer = MathStreamer()
        buffer = ""
        try:
            async for piece in self.session.reply(text):
                buffer += piece
                *complete, buffer = buffer.split("\n")
                for line in complete:
                    await self.show_segments(streamer.feed(line))
            if buffer:
                await self.show_segments(streamer.feed(buffer))
            await self.show_segments(streamer.finish())
            self.update_meter()
        except self.session.errors as err:
            message, locked_out = self.session.explain(err)
            self.print_line(Text(message, style=RED))
            if locked_out:
                self.api_key = None
                self.session = None
                self.set_mode("command")
        finally:
            self.busy = False

    async def show_segments(self, segments):
        """Print text segments; render math segments as images."""
        import asyncio

        from rtk.assistant.latex import render_latex

        log = self.query_one("#log", ChatLog)
        for kind, content in segments:
            if kind == "text":
                log.write(Text(content, style=GREEN))
                continue
            if not GRAPHICS:
                # terminal cannot draw images: show the LaTeX source
                log.write(Text(f"  {content}", style=AMBER))
                continue
            try:
                # rendering takes ~50 ms; a thread keeps the UI responsive
                picture = await asyncio.to_thread(render_latex, content)
            except ValueError:
                log.write(Text(f"[LaTeX] {content}", style=DIM_GREEN))
            else:
                log.write_image(picture)

    def update_meter(self):
        # Record the latest turn's usage and refresh the readout.
        usage = self.session.last_usage
        if usage is not None:
            self.meter.record(usage)
            self.query_one("#meter", UsageMeterWidget).show(self.meter)
