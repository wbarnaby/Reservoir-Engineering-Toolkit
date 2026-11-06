# Gas p/z material balance tool panel.

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)
from textual_fspicker import FileOpen, Filters
from textual_plotext import PlotextPlot

from rtk.core.material_balance import (
    cole_values,
    havlena_odeh_gas,
    pz_analysis,
)
from rtk.core.units import convert, units_for
from rtk.data_io.loaders import SAMPLE_DIR, parse_columns, read_text
from rtk.ui.tools.base import ToolPanel

POINT_COLOR = (255, 176, 0)  # amber, (r, g, b)
LINE_COLOR = (51, 255, 51)  # phosphor green


def read_number(text, name):
    # Convert a required input box's text to float.
    text = text.strip()
    if not text:
        raise ValueError(f"Enter a value for {name}")
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{name}: '{text}' is not a number") from None


def read_optional(text, name):
    # Like read_number, but a blank box returns None.
    if not text.strip():
        return None
    return read_number(text, name)


def field(label, widget):
    # A small column: label on top, widget below.
    return Vertical(Label(label), widget, classes="field")


class PzPanel(ToolPanel):
    # Load a production history, fit p/z, report G and reserves.

    def __init__(self, title):
        super().__init__(title)
        self.data = None  # dict of arrays once a file is loaded

    def compose_body(self) -> ComposeResult:
        yield Label("CSV file (columns: gp, p, z; optional wp)")
        with Horizontal(classes="row"):
            yield Input(value=str(SAMPLE_DIR / "pz_example.csv"), id="path")
            yield Button("Browse", id="browse")
            yield Button("Load", id="load")

        with Horizontal(classes="row"):
            yield field(
                "Gp units",
                Select(
                    [(u, u) for u in units_for("gas_surface")],
                    value="Bscf",
                    allow_blank=False,
                    id="gp-unit",
                ),
            )
            yield field("T (degF)", Input("200", type="number", id="temp"))
            yield field("ce (1/psi)", Input("0", type="number", id="ce"))

        with Horizontal(classes="row"):
            yield field(
                "p abandon (psia)",
                Input(placeholder="optional", type="number", id="p-ab"),
            )
            yield field(
                "z abandon",
                Input(placeholder="optional", type="number", id="z-ab"),
            )

        yield Button("Analyze", id="analyze")
        yield Static("Load a file, then Analyze.", id="pz-results")

        with TabbedContent():
            with TabPane("p/z plot", id="tab-pz"):
                yield PlotextPlot(id="pz-plot")
            with TabPane("Cole plot", id="tab-cole"):
                yield PlotextPlot(id="cole-plot")
            with TabPane("Data", id="tab-data"):
                yield DataTable(id="pz-table")

    def report(self, text, error=False):
        # Show a message in the results box and the console.
        self.query_one("#pz-results", Static).update(text)
        if error:
            self.notify(text, severity="error")
        else:
            self.app.query_one("#console").print_line(text)

    # ---------- loading ----------

    @on(Button.Pressed, "#browse")
    def browse(self) -> None:
        # Open an in-terminal file picker over the app.
        csv_only = Filters(
            ("CSV files", lambda path: path.suffix.lower() == ".csv"),
            ("All files", lambda _path: True),
        )
        self.app.push_screen(
            FileOpen(location=SAMPLE_DIR, title="Open CSV", filters=csv_only),
            callback=self.file_chosen,
        )

    def file_chosen(self, path) -> None:
        # Called when the picker closes. path is None if cancelled.
        if path is None:
            return
        self.query_one("#path", Input).value = str(path)
        self.load_file()

    @on(Button.Pressed, "#load")
    @on(Input.Submitted, "#path")
    def load_file(self) -> None:
        path = self.query_one("#path", Input).value.strip().strip('"')
        try:
            text = read_text(path)
            self.data = parse_columns(
                text, required=("gp", "p", "z"), optional=("wp",)
            )
        except OSError as err:
            self.report(f"Could not open file: {err.strerror}", error=True)
            return
        except ValueError as err:
            self.report(f"Bad file: {err}", error=True)
            return

        self.fill_table()
        rows = len(self.data["gp"])
        self.report(f"Loaded {rows} rows from {path}")

    def fill_table(self):
        # Show the loaded data in the Data tab.
        table = self.query_one("#pz-table", DataTable)
        table.clear(columns=True)
        names = list(self.data)
        table.add_columns(*names)
        for i in range(len(self.data["gp"])):
            table.add_row(*[f"{self.data[name][i]:g}" for name in names])

    # ---------- analysis ----------

    @on(Button.Pressed, "#analyze")
    def analyze(self) -> None:
        if self.data is None:
            self.report("Load a file first", error=True)
            return

        gp = self.data["gp"]
        p = self.data["p"]
        z = self.data["z"]
        wp = self.data.get("wp", 0.0)
        unit = self.query_one("#gp-unit", Select).value

        try:
            temp_f = read_number(self.query_one("#temp", Input).value, "T")
            ce = read_optional(self.query_one("#ce", Input).value, "ce") or 0.0
            p_ab = read_optional(self.query_one("#p-ab", Input).value, "p ab")
            z_ab = read_optional(self.query_one("#z-ab", Input).value, "z ab")
            if (p_ab is None) != (z_ab is None):
                raise ValueError(
                    "Enter both p and z at abandonment, or neither"
                )

            pz = pz_analysis(gp, p, z, ce=ce, p_abandon=p_ab, z_abandon=z_ab)
            t_rankine = convert(temp_f, "F", "R")
            ho = havlena_odeh_gas(
                convert(gp, unit, "scf"), p, z, t_rankine, wp=wp
            )
        except ValueError as err:
            self.report(f"Error: {err}", error=True)
            return

        g_ho = convert(ho["G"], "scf", unit)
        self.show_results(pz, g_ho, unit)
        self.plot_pz(gp, pz, unit)
        self.plot_cole(gp, ho, g_ho, unit)

    def show_results(self, pz, g_ho, unit):
        # Write the numeric results.
        stats = pz["stats"]
        lines = [
            f"G (p/z)          = {pz['G']:.4g} {unit}",
            f"G (Havlena-Odeh) = {g_ho:.4g} {unit}",
            f"pi/zi fitted     = {pz['intercept']:.1f} psia"
            f"   measured = {pz['pz_initial_measured']:.1f}",
            f"R2 = {stats['r2']:.5f}   RMSE = {stats['rmse']:.2f} psia",
            f"Recovery to date = {pz['recovery_factor'][-1]:.1%}",
        ]
        if "gp_abandon" in pz:
            lines.append(
                f"Recoverable = {pz['gp_abandon']:.4g} {unit}"
                f"   remaining = {pz['remaining']:.4g} {unit}"
            )
        text = "\n".join(lines)
        self.query_one("#pz-results", Static).update(text)
        self.app.query_one("#console").print_line(
            f"p/z: G = {pz['G']:.4g} {unit}, R2 = {stats['r2']:.4f}"
        )

    def plot_pz(self, gp, pz, unit):
        # Measured p/z points plus the fitted line out to G.
        plot = self.query_one("#pz-plot", PlotextPlot)
        plt = plot.plt
        plt.clear_data()
        # line first, then points on top so they stay visible
        plt.plot(
            [0, pz["G"]],
            [pz["intercept"], 0],
            color=LINE_COLOR,
            marker="braille",
        )
        plt.scatter(
            gp.tolist(), pz["y"].tolist(), color=POINT_COLOR, marker="●"
        )
        plt.title("p/z vs Gp")
        plt.xlabel(f"Gp ({unit})")
        plt.ylabel("p/z (psia)")
        plot.refresh()

    def plot_cole(self, gp, ho, g_ho, unit):
        # F/Eg vs Gp: flat means volumetric.
        gp_cole, ratio = cole_values(gp, ho["F"], ho["Eg"])
        ratio = convert(ratio, "scf", unit)

        plot = self.query_one("#cole-plot", PlotextPlot)
        plt = plot.plt
        plt.clear_data()
        plt.hline(g_ho, color=LINE_COLOR)
        plt.scatter(
            gp_cole.tolist(), ratio.tolist(), color=POINT_COLOR, marker="●"
        )
        plt.title("Cole plot: flat = volumetric")
        plt.xlabel(f"Gp ({unit})")
        plt.ylabel(f"F/Eg ({unit})")
        plot.refresh()
