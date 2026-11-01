"""Unit converter tool panel."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from rtk.core.units import all_dimensions, convert, units_for
from rtk.ui.tools.base import ToolPanel


def as_options(items):
    # Turn a list of strings into Select options: (label, value).
    return [(item, item) for item in items]


class UnitsPanel(ToolPanel):
    # Convert a value between any two units of the same dimension.

    def compose_body(self) -> ComposeResult:
        units = units_for("pressure")

        yield Label("Dimension")
        yield Select(
            as_options(all_dimensions()),
            value="pressure",
            allow_blank=False,
            id="dimension",
        )
        yield Label("Value")
        yield Input(placeholder="number", type="number", id="value")
        with Horizontal(classes="row"):
            yield Select(
                as_options(units),
                value=units[0],
                allow_blank=False,
                id="from-unit",
            )
            yield Label("->", classes="arrow")
            yield Select(
                as_options(units),
                value=units[1],
                allow_blank=False,
                id="to-unit",
            )
        yield Checkbox("Difference (ignore offsets)", id="delta")
        yield Button("Convert", id="convert")
        yield Static("", id="result")

    @on(Select.Changed, "#dimension")
    def dimension_changed(self, event: Select.Changed) -> None:
        units = units_for(event.value)
        from_select = self.query_one("#from-unit", Select)
        to_select = self.query_one("#to-unit", Select)
        from_select.set_options(as_options(units))
        to_select.set_options(as_options(units))
        from_select.value = units[0]
        to_select.value = units[1] if len(units) > 1 else units[0]

    @on(Button.Pressed, "#convert")
    @on(Input.Submitted, "#value")
    def do_convert(self) -> None:
        result = self.query_one("#result", Static)
        text = self.query_one("#value", Input).value.strip()
        from_unit = self.query_one("#from-unit", Select).value
        to_unit = self.query_one("#to-unit", Select).value
        delta = self.query_one("#delta", Checkbox).value

        if not text:
            result.update("Error: enter a value to convert")
            return

        try:
            value = float(text)
        except ValueError:
            result.update(f"Error: '{text}' is not a number")
            return

        try:
            answer = convert(value, from_unit, to_unit, delta=delta)
        except ValueError as err:
            result.update(f"Error: {err}")
            return

        line = f"{value:g} {from_unit} = {answer:.6g} {to_unit}"
        result.update(line)
        self.app.query_one("#console").print_line(line)
