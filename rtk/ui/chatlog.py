"""Scrolling console log that can hold both text lines and images.

RichLog only holds text, so LaTeX images need a plain scroll
container whose children are Static (text) and Image (math) widgets.

textual_image checks the terminal's graphics support when it is
imported, which must happen before the app takes over the screen.
That is why it is imported at the top of this module, never lazily.
"""

import math

from textual.containers import VerticalScroll
from textual.widgets import Static
from textual_image import renderable
from textual_image.widget import Image, get_cell_size

# True when the terminal can show real images (Sixel or Kitty graphics).
# Otherwise images would be drawn with block characters, which makes
# equations unreadable, so the console shows LaTeX source instead.
GRAPHICS = renderable.Image in (renderable.SixelImage, renderable.TGPImage)


class ChatLog(VerticalScroll):
    """Append-only log of text and images that follows the newest line."""

    def write(self, content):
        """Add one line: a markup string or a rich Text."""
        self.mount(Static(content, classes="log-line"))
        self.call_after_refresh(self.scroll_end, animate=False)

    def write_image(self, picture):
        """Add a PIL image sized to the terminal's character cells."""
        cell = get_cell_size()
        image = Image(picture, classes="log-math")
        image.styles.width = math.ceil(picture.width / cell.width)
        image.styles.height = math.ceil(picture.height / cell.height)
        self.mount(image)
        self.call_after_refresh(self.scroll_end, animate=False)

    def clear(self):
        """Remove everything."""
        self.remove_children()
