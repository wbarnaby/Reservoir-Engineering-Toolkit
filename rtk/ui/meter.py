"""A small usage/cost readout that floats in the console's top-right."""

from textual.widgets import Static


def format_meter(meter):
    # Build the two-line readout text from a UsageMeter.
    return (
        f"chat   {meter.total.tokens:>7,} tok   ${meter.total.cost:.4f}\n"
        f"last   {meter.last.tokens:>7,} tok   ${meter.last.cost:.4f}"
    )


class UsageMeterWidget(Static):
    # Shows total and last tokens and cost. Hidden until first use.

    def show(self, meter):
        # Update the numbers and make the widget visible.
        self.update(format_meter(meter))
        self.display = True
