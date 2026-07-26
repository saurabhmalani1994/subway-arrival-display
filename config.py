#!/usr/bin/env python3
"""
Configuration for the subway arrival display.

Everything here can be overridden with environment variables (see .env.example),
so you should not need to edit this file to run it at your own station.
"""
import os

# Load a local .env if python-dotenv is available. Optional: on the Pi the
# systemd unit supplies the same variables via EnvironmentFile, and real
# environment variables always win over the file either way.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Application configuration."""

    # --- MTA API ---------------------------------------------------------
    MTA_API_KEY = os.getenv("MTA_API_KEY", "")
    """Register for a free key at https://api.mta.info/"""

    # --- Station ---------------------------------------------------------
    # Presets for a few well-known stations. Pick one with STATION=<key>, or
    # override STOP_ID / ROUTE_IDS / STOP_NAME individually.
    #
    # To find the stop_id for your own station, run: python tools/find_stops.py
    STATION_CONFIGS = {
        "times-square": {
            "stop_id": "R16",
            "route_ids": ["N", "Q", "R", "W"],
            "stop_name": "Times Sq 42 St",
            "latitude": 40.7557,
            "longitude": -73.9866,
        },
        "grand-central": {
            "stop_id": "631",
            "route_ids": ["4", "5", "6"],
            "stop_name": "Grand Central",
            "latitude": 40.7527,
            "longitude": -73.9772,
        },
        "union-square": {
            "stop_id": "635",
            "route_ids": ["4", "5", "6"],
            "stop_name": "14 St Union Sq",
            "latitude": 40.7359,
            "longitude": -73.9906,
        },
        "atlantic-av": {
            "stop_id": "235",
            "route_ids": ["2", "3", "4", "5"],
            "stop_name": "Atlantic Av",
            "latitude": 40.6840,
            "longitude": -73.9776,
        },
    }

    STATION = os.getenv("STATION", "times-square")
    """Which preset to use. Must be a key of STATION_CONFIGS."""

    _station = STATION_CONFIGS.get(STATION, STATION_CONFIGS["times-square"])

    STOP_ID = os.getenv("STOP_ID", _station["stop_id"])
    """Base GTFS stop ID. Directional stops are this plus N/S (e.g. R16N, R16S)."""

    ROUTE_IDS = [
        r.strip().upper()
        for r in os.getenv("ROUTE_IDS", ",".join(_station["route_ids"])).split(",")
        if r.strip()
    ]
    """Routes to show at this stop. The right GTFS-RT feeds are derived from these."""

    STOP_NAME = os.getenv("STOP_NAME", _station["stop_name"])
    """Display name shown in the header."""

    # --- Weather ---------------------------------------------------------
    # The NOAA forecast grid is resolved from these at runtime, so changing
    # station automatically changes the weather location.
    LATITUDE = float(os.getenv("LATITUDE", _station["latitude"]))
    LONGITUDE = float(os.getenv("LONGITUDE", _station["longitude"]))

    # --- LED matrix ------------------------------------------------------
    DISPLAY_WIDTH = int(os.getenv("DISPLAY_WIDTH", "64"))
    DISPLAY_HEIGHT = int(os.getenv("DISPLAY_HEIGHT", "32"))

    MATRIX_LIBRARY = os.getenv("MATRIX_LIBRARY", "rgbmatrix")
    """rgbmatrix for real hardware, or 'test' to render to PNG files instead."""

    GPIO_SLOWDOWN = int(os.getenv("GPIO_SLOWDOWN", "2"))
    """Increase (1-4) if the display flickers. Faster Pis need a higher value."""

    CHAIN_LENGTH = int(os.getenv("CHAIN_LENGTH", "1"))
    PARALLEL_CHAINS = int(os.getenv("PARALLEL_CHAINS", "1"))

    # --- Timing ----------------------------------------------------------
    FRAME_DURATION = int(os.getenv("FRAME_DURATION", "10"))
    """Seconds to show each train direction."""

    INFO_PANEL_DURATION = int(os.getenv("INFO_PANEL_DURATION", "10"))
    """Seconds to show the info panel (nyan cat + clock + weather)."""

    DISPLAY_FPS = int(os.getenv("DISPLAY_FPS", "30"))
    API_UPDATE_INTERVAL = int(os.getenv("API_UPDATE_INTERVAL", "10"))
    WEATHER_UPDATE_INTERVAL = int(os.getenv("WEATHER_UPDATE_INTERVAL", "1800"))
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))

    STALE_DATA_MULTIPLIER = int(os.getenv("STALE_DATA_MULTIPLIER", "3"))
    """Show a fault message only after this many update intervals with no data."""

    # --- Networking ------------------------------------------------------
    VERIFY_TLS = _env_bool("VERIFY_TLS", True)
    """Leave this on. See docs/TROUBLESHOOTING.md before turning it off."""

    USER_AGENT = os.getenv(
        "USER_AGENT",
        "subway-arrival-display (https://github.com/saurabhmalani1994/subway-arrival-display)",
    )
    """weather.gov asks API users to identify themselves."""

    # --- Assets / logging ------------------------------------------------
    NYAN_GIF_PATH = os.path.join(os.path.dirname(__file__), "assets", "nyancat.gif")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def set_station(cls, station_key):
        """Switch to a different station preset at runtime."""
        station = cls.STATION_CONFIGS.get(station_key)
        if station is None:
            raise KeyError(
                f"Unknown station '{station_key}'. "
                f"Known: {', '.join(sorted(cls.STATION_CONFIGS))}"
            )
        cls.STATION = station_key
        cls.STOP_ID = station["stop_id"]
        cls.ROUTE_IDS = list(station["route_ids"])
        cls.STOP_NAME = station["stop_name"]
        cls.LATITUDE = station["latitude"]
        cls.LONGITUDE = station["longitude"]
