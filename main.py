#!/usr/bin/env python3
"""
MTA Train Display for 32x64 LED Matrix
Main application entry point
Displays real-time train arrivals for multiple routes at a station

Frame rotation:
  - Northbound: FRAME_DURATION seconds
  - Southbound: FRAME_DURATION seconds
  - Info panel (nyan cat + clock + weather + temp): INFO_PANEL_DURATION seconds
  (repeats continuously)
"""

import socket
import time
import logging
from threading import Thread

from config import Config
from mta_client import MTAClient
from weather_client import WeatherClient
from display_manager import DisplayManager
from info_panel import InfoPanel
from status_display import StatusDisplay

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MTATrainDisplay:
    """Main application controller for MTA train display"""

    def __init__(self):
        """Initialize the display application"""
        self.config = Config
        # Initialize clients
        self.mta_client = MTAClient(api_key=self.config.MTA_API_KEY)
        self.weather_client = WeatherClient()
        self.display_manager = DisplayManager()
        self.info_panel = InfoPanel(self.display_manager)
        self.status_display = StatusDisplay(self.display_manager)

        self.running = False
        self.current_frame = "northbound"
        self.train_data = {"northbound": [], "southbound": []}
        self.weather_data = None
        self.last_update = 0
        self.last_weather_update = 0
        self.last_successful_update = 0

        logger.info("MTATrainDisplay initialized")
        logger.info(f"  Stop: {self.config.STOP_NAME}")
        logger.info(f"  Stop ID: {self.config.STOP_ID}")
        logger.info(f"  Routes: {self.config.ROUTE_IDS}")
        logger.info(f"  Display: {self.config.DISPLAY_WIDTH}x{self.config.DISPLAY_HEIGHT}")

    def fetch_train_data(self):
        """Fetch train data from MTA API

        Fetches all feeds needed for the configured routes and merges results.
        """
        try:
            self.train_data = self.mta_client.get_trains(
                self.config.STOP_ID,
                self.config.ROUTE_IDS
            )
            self.last_update = time.time()
            if self.train_data["northbound"] or self.train_data["southbound"]:
                self.last_successful_update = self.last_update

            logger.info(
                f"Updated train data - "
                f"Northbound: {len(self.train_data['northbound'])} trains, "
                f"Southbound: {len(self.train_data['southbound'])} trains"
            )

        except Exception as e:
            logger.error(f"Error fetching train data: {e}")

    def fetch_weather_data(self):
        """Fetch weather data from NOAA API"""
        try:
            self.weather_data = self.weather_client.fetch_weather()
            self.last_weather_update = time.time()
            if self.weather_data:
                logger.info(
                    f"Weather updated - {self.weather_data.temperature}\u00b0F, "
                    f"{self.weather_data.condition}"
                )
            else:
                logger.warning(
                    "Weather fetch returned no data \u2014 display will show placeholders "
                    "(? sprite, --\u00b0F). See weather_client errors above for the cause."
                )
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")

    def update_loop(self):
        """Background thread to update train and weather data periodically"""
        while self.running:
            try:
                self.fetch_train_data()

                # Refresh weather every WEATHER_UPDATE_INTERVAL seconds
                elapsed = time.time() - self.last_weather_update
                if self.weather_data is None or elapsed >= self.config.WEATHER_UPDATE_INTERVAL:
                    self.fetch_weather_data()

                time.sleep(self.config.API_UPDATE_INTERVAL)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(5)

    def is_data_stale(self):
        """True when we have no train data worth displaying.

        Requires *both* an empty dataset and a long gap since the last good
        fetch, so a single failed poll keeps showing the last known arrivals
        instead of blanking the screen.
        """
        if self.train_data["northbound"] or self.train_data["southbound"]:
            return False

        threshold = self.config.API_UPDATE_INTERVAL * self.config.STALE_DATA_MULTIPLIER
        return (time.time() - self.last_successful_update) > threshold

    def fault_message(self):
        """Best guess at why nothing is displayable, as (message, detail)."""
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3).close()
        except OSError:
            return ("NO WIFI", None)

        if not self.config.MTA_API_KEY:
            # The feeds are currently open, so this is informational rather than
            # definitely the cause.
            return ("NO DATA", "check stop")

        return ("NO DATA", "MTA feed")

    def display_loop(self):
        """Main display loop - cycles northbound -> southbound -> info panel"""
        frame_order = ["northbound", "southbound", "info_panel"]
        frame_index = 0
        self.current_frame = frame_order[frame_index]
        frame_start = time.time()

        while self.running:
            try:
                current_time = time.time()

                # Determine duration for current frame
                if self.current_frame == "info_panel":
                    duration = self.config.INFO_PANEL_DURATION
                else:
                    duration = self.config.FRAME_DURATION

                # Switch frames when duration elapsed
                if current_time - frame_start >= duration:
                    frame_index = (frame_index + 1) % len(frame_order)
                    self.current_frame = frame_order[frame_index]
                    frame_start = current_time
                    logger.info(f"Switched to frame: {self.current_frame}")

                # Render current frame. If data has gone properly stale there is
                # nothing to show, so a fault message replaces a blank screen —
                # never a populated one.
                if self.is_data_stale():
                    self.status_display.show_error(*self.fault_message())
                elif self.current_frame in ("northbound", "southbound"):
                    trains = self.train_data[self.current_frame][:2]
                    self.display_manager.render_frame(self.current_frame, trains)
                elif self.current_frame == "info_panel":
                    self.info_panel.render(self.weather_data)

                time.sleep(1 / self.config.DISPLAY_FPS)

            except Exception as e:
                logger.error(f"Error in display loop: {e}")
                time.sleep(0.1)

    def run(self):
        """Start the application"""
        logger.info("Starting MTA Train Display application")
        self.running = True

        try:
            # Start update thread
            update_thread = Thread(target=self.update_loop, daemon=True)
            update_thread.start()

            # Initial fetches
            self.fetch_train_data()
            self.fetch_weather_data()

            # Run display loop (main thread)
            self.display_loop()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down...")
        self.running = False
        self.display_manager.cleanup()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    app = MTATrainDisplay()
    app.run()
