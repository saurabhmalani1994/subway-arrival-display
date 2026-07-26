#!/usr/bin/env python3
"""
Info Panel - Third display panel combining nyan cat, clock, weather, and temperature.

Layout (64x32 pixels, asymmetric):
  Top-left (0,0)-(41,19)   42x20  Animated nyan cat GIF
  Bottom-left (0,20)-(41,31) 42x12  Clock (12hr am/pm)
  Top-right (42,0)-(63,15)  22x16  Animated weather sprite
  Bottom-right (42,16)-(63,31) 22x16  Temperature (°F)
"""

import base64
import logging
import math
import os
from datetime import datetime
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# ── Diagnostic: prove which code version is running ──────────────────
import sys
_NYAN_VERSION = "EMBEDDED_BASE64_V1"
print(f"[DIAG] info_panel.py loaded: version={_NYAN_VERSION}, file={__file__}", file=sys.stderr, flush=True)
try:
    with open("/tmp/nyan_diag.txt", "w") as _f:
        _f.write(f"version={_NYAN_VERSION}\nfile={__file__}\npython={sys.executable}\n")
except Exception:
    pass

try:
    from nyan_frames import NYAN_FRAME_DATA, NYAN_FRAME_WIDTH, NYAN_FRAME_HEIGHT
    print(f"[DIAG] nyan_frames imported OK: {len(NYAN_FRAME_DATA)} frames, {NYAN_FRAME_WIDTH}x{NYAN_FRAME_HEIGHT}", file=sys.stderr, flush=True)
except Exception as _e:
    print(f"[DIAG] nyan_frames import FAILED: {_e}", file=sys.stderr, flush=True)
    NYAN_FRAME_DATA = []
    NYAN_FRAME_WIDTH = 42
    NYAN_FRAME_HEIGHT = 20

# Timezone support (Python 3.9+ stdlib). Falls back to system local time if the
# zoneinfo database is missing, which is common on Windows and slim containers
# (install the `tzdata` package to fix).
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo(TIMEZONE)
except Exception as e:
    logger.warning(f"Timezone '{TIMEZONE}' unavailable ({e}); using system local time")
    LOCAL_TZ = None


class InfoPanel:
    """Renders the composite info panel with nyan cat, clock, weather, and temperature."""

    # Quadrant boundaries
    NYAN_RECT = (0, 0, 42, 20)       # x, y, width, height
    CLOCK_RECT = (0, 20, 42, 12)
    WEATHER_RECT = (42, 0, 22, 16)
    TEMP_RECT = (42, 16, 22, 16)

    def __init__(self, display_manager):
        self.dm = display_manager
        self.nyan_frames = self._load_nyan_frames()

    # ── Nyan Cat ────────────────────────────────────────────────────────

    def _load_nyan_frames(self):
        """Decode nyan cat frames from raw RGB pixel data embedded in nyan_frames.py.

        Uses Image.frombytes() which needs no image format decoder — just raw
        pixel data. This avoids Pillow PNG/zlib issues on the Raspberry Pi.
        """
        frames = []
        size = (NYAN_FRAME_WIDTH, NYAN_FRAME_HEIGHT)
        expected_bytes = NYAN_FRAME_WIDTH * NYAN_FRAME_HEIGHT * 3
        print(f"[DIAG] _load_nyan_frames called, {len(NYAN_FRAME_DATA)} entries, expecting {expected_bytes} bytes each", file=sys.stderr, flush=True)
        for i, b64 in enumerate(NYAN_FRAME_DATA):
            try:
                raw = base64.b64decode(b64)
                frame = Image.frombytes("RGB", size, raw)
                frames.append(frame)
            except Exception as e:
                print(f"[DIAG] Frame {i} decode FAILED: {e}", file=sys.stderr, flush=True)
                logger.warning(f"Error decoding embedded frame {i}: {e}")
        print(f"[DIAG] Loaded {len(frames)} nyan frames successfully", file=sys.stderr, flush=True)
        logger.info(f"Loaded {len(frames)} embedded nyan cat frames")
        return frames

    def _draw_nyancat(self, img, frame_count):
        """Paste the current nyan cat frame onto the image."""
        if not self.nyan_frames:
            # DIAGNOSTIC: log every time rainbow fallback triggers
            if frame_count <= 3:
                print(f"[DIAG] RAINBOW FALLBACK! nyan_frames={self.nyan_frames}, len={len(self.nyan_frames) if self.nyan_frames else 'None'}", file=sys.stderr, flush=True)
            # Fallback: rainbow stripes
            draw = ImageDraw.Draw(img)
            colors = [(255, 0, 0), (255, 165, 0), (255, 255, 0),
                      (0, 255, 0), (0, 0, 255), (128, 0, 128)]
            x0, y0, w, h = self.NYAN_RECT
            stripe_h = max(1, h // len(colors))
            phase = frame_count % 6
            for i, c in enumerate(colors):
                ci = (i + phase) % len(colors)
                sy = y0 + i * stripe_h
                draw.rectangle([(x0, sy), (x0 + w - 1, sy + stripe_h - 1)],
                               fill=colors[ci])
            return

        nyan_idx = (frame_count // 2) % len(self.nyan_frames)
        frame = self.nyan_frames[nyan_idx]
        img.paste(frame, (self.NYAN_RECT[0], self.NYAN_RECT[1] + 1))

    # ── Clock ───────────────────────────────────────────────────────────

    def _draw_clock(self, draw):
        """Draw current local time in 12-hour format in the bottom-left."""
        x0, y0, w, h = self.CLOCK_RECT

        if LOCAL_TZ:
            now = datetime.now(LOCAL_TZ)
        else:
            now = datetime.now()

        time_str = now.strftime("%I:%M").lstrip("0")
        ampm_str = now.strftime("%p").lower()
        full_str = f"{time_str}{ampm_str}"

        font = self.dm.fonts.get("weather", self.dm.fonts["dest"])

        bbox = draw.textbbox((0, 0), full_str, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        tx = x0 + (w - tw) // 2
        ty = y0 + (h - th) // 2 - 1

        # Draw time portion in cyan
        draw.text((tx, ty), time_str, font=font, fill=self.dm.COLORS["cyan"])

        # Draw am/pm in gray right after
        time_bbox = draw.textbbox((0, 0), time_str, font=font)
        time_w = time_bbox[2] - time_bbox[0]
        draw.text((tx + time_w, ty), ampm_str, font=font, fill=self.dm.COLORS["gray"])

    # ── Weather Sprite ──────────────────────────────────────────────────

    def _get_icon_code(self, condition_str):
        """Map weather condition string to icon code."""
        if not condition_str:
            return "unknown"

        c = condition_str.lower().strip()

        if any(w in c for w in ("thunder", "storm", "tornado", "lightning")):
            return "stormy"
        if any(w in c for w in ("snow", "sleet", "blizzard", "flurries")):
            return "snowy"
        if any(w in c for w in ("rain", "shower", "drizzle", "precipitation")):
            return "rainy"
        if any(w in c for w in ("partly cloudy", "partly sunny", "mostly sunny")):
            return "partly_cloudy"
        if any(w in c for w in ("sunny", "clear", "fair")):
            return "sunny"
        if any(w in c for w in ("cloudy", "overcast", "mostly cloudy")):
            return "cloudy"
        if any(w in c for w in ("fog", "mist", "haze")):
            return "foggy"
        if any(w in c for w in ("wind", "breezy", "gust")):
            return "windy"
        return "unknown"

    def _draw_weather_sprite(self, draw, weather_data, frame_count):
        """Draw an animated weather sprite in the top-right quadrant.

        Centered horizontally to align directly above the temperature text.
        """
        x0, y0, w, h = self.WEATHER_RECT
        # Shift right to align with temperature below: center of TEMP_RECT
        cx = self.TEMP_RECT[0] + self.TEMP_RECT[2] // 2  # 42 + 11 = 53
        cy = y0 + h // 2   # center y = 8

        if weather_data is None:
            # No data placeholder
            draw.text((x0 + 2, cy - 3), "?", font=self.dm.fonts["badge"],
                      fill=self.dm.COLORS["gray"])
            return

        condition = weather_data.condition if weather_data.condition else "Unknown"
        icon = self._get_icon_code(condition)

        colors = self.dm.COLORS
        f = frame_count  # shorthand

        if icon == "sunny":
            # Pulsing sun
            ray_extra = 1 if (f // 8) % 2 == 0 else 0
            draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=colors["yellow"])
            rl = 4 + ray_extra
            draw.line([cx - rl, cy, cx - 4, cy], fill=colors["yellow"])
            draw.line([cx + 4, cy, cx + rl, cy], fill=colors["yellow"])
            draw.line([cx, cy - rl, cx, cy - 4], fill=colors["yellow"])
            draw.line([cx, cy + 4, cx, cy + rl], fill=colors["yellow"])
            # Diagonal rays
            d = rl - 1
            draw.line([cx - d, cy - d, cx - 3, cy - 3], fill=colors["yellow"])
            draw.line([cx + 3, cy - 3, cx + d, cy - d], fill=colors["yellow"])
            draw.line([cx - d, cy + d, cx - 3, cy + 3], fill=colors["yellow"])
            draw.line([cx + 3, cy + 3, cx + d, cy + d], fill=colors["yellow"])

        elif icon == "partly_cloudy":
            # Sun with drifting cloud
            draw.ellipse([cx - 4, cy - 4, cx, cy], fill=colors["yellow"])
            cloud_dx = int(2 * math.sin(f * 0.08))
            ccx = cx + 2 + cloud_dx
            draw.ellipse([ccx - 4, cy - 1, ccx, cy + 3], fill=colors["gray"])
            draw.ellipse([ccx - 1, cy - 3, ccx + 4, cy + 1], fill=colors["gray"])
            draw.ellipse([ccx + 2, cy - 1, ccx + 7, cy + 3], fill=colors["gray"])

        elif icon == "cloudy":
            cloud_dx = int(1 * math.sin(f * 0.04))
            ccx = cx + cloud_dx
            draw.ellipse([ccx - 5, cy - 2, ccx - 1, cy + 2], fill=colors["gray"])
            draw.ellipse([ccx - 2, cy - 4, ccx + 3, cy], fill=colors["gray"])
            draw.ellipse([ccx + 1, cy - 2, ccx + 6, cy + 2], fill=colors["gray"])

        elif icon == "rainy":
            # Cloud
            draw.ellipse([cx - 5, cy - 4, cx + 1, cy - 1], fill=colors["gray"])
            draw.ellipse([cx - 1, cy - 5, cx + 4, cy - 2], fill=colors["gray"])
            # Falling drops
            for i, dx in enumerate([-3, 0, 3]):
                drop_y = (f * 2 + i * 4) % 8
                dy = cy + drop_y
                if dy + 1 <= y0 + h - 1:
                    draw.line([cx + dx, dy, cx + dx, dy + 1], fill=colors["cyan"])

        elif icon == "snowy":
            # Cloud
            draw.ellipse([cx - 5, cy - 4, cx + 1, cy - 1], fill=colors["white"])
            draw.ellipse([cx - 1, cy - 5, cx + 4, cy - 2], fill=colors["white"])
            # Drifting snowflakes
            for i, dx in enumerate([-4, 0, 4]):
                wobble = int(math.sin(f * 0.15 + i * 2) * 2)
                drop_y = (f + i * 5) % 8
                sx = cx + dx + wobble
                sy = cy + drop_y
                if sy <= y0 + h - 1:
                    draw.point((sx, sy), fill=colors["cyan"])

        elif icon == "stormy":
            # Dark cloud
            draw.ellipse([cx - 5, cy - 4, cx + 1, cy - 1], fill=colors["dark_gray"])
            draw.ellipse([cx - 1, cy - 5, cx + 4, cy - 2], fill=colors["dark_gray"])
            # Blinking lightning bolt
            if (f % 20) < 3:
                draw.line([cx, cy, cx + 1, cy + 2], fill=colors["yellow"])
                draw.line([cx + 1, cy + 2, cx - 1, cy + 4], fill=colors["yellow"])
                draw.line([cx - 1, cy + 4, cx + 1, cy + 6], fill=colors["yellow"])

        elif icon == "foggy":
            shift = (f // 15) % 3
            for i, offset in enumerate([-3, 0, 3]):
                ly = cy + offset + shift - 1
                if y0 <= ly <= y0 + h - 1:
                    draw.line([cx - 5, ly, cx + 5, ly], fill=colors["gray"])

        elif icon == "windy":
            phase = (f * 5) % 360
            for i in range(3):
                arc_y = cy - 3 + i * 3
                arc_start = (phase + i * 40) % 360
                draw.arc([cx - 5, arc_y - 2, cx + 5, arc_y + 2],
                         arc_start, arc_start + 180, fill=colors["cyan"])

        else:
            # Unknown: question mark
            draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=colors["gray"])
            draw.text((cx - 2, cy - 4), "?", font=self.dm.fonts["badge"],
                      fill=colors["white"])

    # ── Temperature ─────────────────────────────────────────────────────

    def _draw_temperature(self, draw, weather_data):
        """Draw current temperature in the bottom-right quadrant."""
        x0, y0, w, h = self.TEMP_RECT

        font = self.dm.fonts.get("weather", self.dm.fonts["dest"])

        if weather_data and weather_data.temperature is not None:
            temp_text = f"{weather_data.temperature}\u00b0F"
        else:
            temp_text = "--\u00b0F"

        bbox = draw.textbbox((0, 0), temp_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        tx = x0 + (w - tw) // 2
        ty = y0 + (h - th) // 2

        draw.text((tx, ty), temp_text, font=font, fill=self.dm.COLORS["yellow"])

    # ── Main Render ─────────────────────────────────────────────────────

    def render(self, weather_data):
        """Render the full info panel to the display.

        Args:
            weather_data: WeatherData object from weather_client, or None.
        """
        try:
            self.dm.frame_count += 1

            img = Image.new("RGB", (self.dm.DISPLAY_WIDTH, self.dm.DISPLAY_HEIGHT),
                            self.dm.COLORS["black"])
            draw = ImageDraw.Draw(img)

            self._draw_nyancat(img, self.dm.frame_count)
            self._draw_clock(draw)
            self._draw_weather_sprite(draw, weather_data, self.dm.frame_count)
            self._draw_temperature(draw, weather_data)

            if self.dm.test_mode:
                self.dm.save_test_image(img, "info_panel")
            else:
                self.dm.display_image(img)

        except Exception as e:
            logger.error(f"Error rendering info panel: {e}", exc_info=True)
