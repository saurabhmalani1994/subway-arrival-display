#!/usr/bin/env python3
"""
Fault display for the LED matrix.

This is deliberately minimal. It renders *only* when there is nothing valid to
show — i.e. it replaces a blank screen, never a populated one. Train times are
the point of the display, and a brief API hiccup must never blank them out; the
caller is responsible for only invoking this once data has gone properly stale.
"""

import logging

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class StatusDisplay:
    """Renders short fault messages when no train data can be shown."""

    BACKGROUND = (0, 0, 0)
    TEXT_COLOR = (255, 80, 0)

    def __init__(self, display_manager):
        self.display = display_manager

    def show_error(self, message, detail=None):
        """Render a fault message centered on the matrix.

        Args:
            message: Short primary text, e.g. "NO WIFI" or "NO API KEY".
            detail: Optional smaller second line.
        """
        try:
            width = self.display.DISPLAY_WIDTH
            height = self.display.DISPLAY_HEIGHT

            img = Image.new("RGB", (width, height), self.BACKGROUND)
            draw = ImageDraw.Draw(img)

            font = self.display.fonts.get("header")
            detail_font = self.display.fonts.get("time_now") or font

            self._draw_centered(draw, message, font, width, y=8 if detail else 12)
            if detail:
                self._draw_centered(draw, detail, detail_font, width, y=19)

            if self.display.test_mode:
                self.display.save_test_image(img, "status")
            else:
                self.display.display_image(img)

        except Exception as e:
            # A failure to render the fault screen must never take down the app.
            logger.error(f"Could not render status message '{message}': {e}")

    def _draw_centered(self, draw, text, font, width, y):
        """Draw text horizontally centered at the given y."""
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        draw.text(((width - (right - left)) // 2, y), text, font=font,
                  fill=self.TEXT_COLOR)
