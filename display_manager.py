#!/usr/bin/env python3

"""
LED Display Manager - OPENSANS TRUETYPE FONT WITH SLIDING DESTINATIONS
Handles rendering to 32x64 RGB LED matrix using SetPixel() method

FEATURES:
- OpenSans TrueType font rendering
- Sliding destination text animation with proper clipping
- Tunable font sizes via configuration
- All previous fixes maintained
- Smaller font for 'NOW' time display
"""

import logging
import time
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont

from config import Config

logger = logging.getLogger(__name__)

class DisplayManager:
    """Manages rendering to LED matrix display"""

    # Display dimensions
    DISPLAY_WIDTH = Config.DISPLAY_WIDTH
    DISPLAY_HEIGHT = Config.DISPLAY_HEIGHT
    
    # Color definitions (RGB tuples)
    COLORS = {
        'black': (0, 0, 0),
        'white': (255, 255, 255),
        'yellow': (255, 255, 0),
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'cyan': (0, 255, 255),
        'magenta': (255, 0, 255),
        'gray': (128, 128, 128),
        'dark_gray': (64, 64, 64),
    }
    
    # Layout dimensions
    HEADER_HEIGHT = 5
    ROW_HEIGHT = 12
    COL_WIDTHS = [12, 30, 22]  # Train #, Destination, Time
    DEST_MAX_WIDTH = 28  # Max pixels for destination text
    DEST_COL_X = 12  # Starting X position of destination column
    
    # Font configuration - TUNABLE SIZES
    FONT_CONFIG = {
        'header_size': 8,      # Header font size
        'badge_size': 9,       # Train badge font size
        'dest_size': 9,        # Destination font size
        'time_size': 10,        # Time font size
        'time_now_size': 7,    # Smaller size for 'NOW' text
        'weather_size': 8,     # Weather/clock font size
        'weather_temp_size': 9, # Temperature font size
    }
    
    # Sliding animation configuration
    SLIDE_CONFIG = {
        'enabled': True,           # Enable sliding animation
        'speed': 2,                # Pixels per frame
        'pause_frames': 30,        # Frames to pause at edges
        'cycle_duration': 120,     # Total frames per complete cycle
    }
    
    def __init__(self):
        """Initialize display manager"""
        self.matrix = None
        self.try_init_matrix()
        
        # For testing/development without hardware
        self.test_mode = self.matrix is None
        
        # Load OpenSans TrueType fonts
        self.fonts = self._load_fonts()
        
        # Animation state for destinations
        self.slide_state = {}  # destination -> slide position
        self.frame_count = 0   # Global frame counter for animation
        
        if self.test_mode:
            logger.warning("Running in test mode - no LED matrix detected")
        else:
            logger.info("✓ LED matrix initialized successfully")
            logger.info(f"  Resolution: {self.matrix.width}x{self.matrix.height}")
    
    def _load_fonts(self):
        """Load OpenSans TrueType fonts
        
        Returns:
            Dict of font name -> ImageFont object
        """
        fonts = {}
        
        # Try to find OpenSans font file
        font_paths = [
            # "/usr/share/fonts/truetype/nunito-sans/NunitoSans-VariableFont_YTLC,opsz,wdth,wght.ttf",
            # "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
            # "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            # "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        
        # First try to find OpenSans specifically
        opensans_paths = [
            "/usr/share/fonts/truetype/opensans/OpenSans-Regular.ttf",
            "/usr/share/fonts/opentype/opensans/OpenSans-Regular.otf",
            "/usr/local/share/fonts/OpenSans-Regular.ttf",
        ]
        
        # Check for OpenSans first
        font_file = None
        for path in opensans_paths:
            if os.path.exists(path):
                font_file = path
                logger.info(f"Found OpenSans font: {path}")
                break
        
        # Fall back to other fonts if OpenSans not found
        if not font_file:
            logger.warning("OpenSans not found, trying fallback fonts...")
            for path in font_paths:
                if os.path.exists(path):
                    font_file = path
                    logger.info(f"Using fallback font: {path}")
                    break

        dejavu_fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        nunito_fontfile = "/usr/share/fonts/truetype/nunito-sans/NunitoSans-VariableFont_YTLC,opsz,wdth,wght.ttf"
        noto_fontfile = "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf"
        liberation_fontfile = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        
        # Load fonts at different sizes
        if font_file:
            try:
                fonts['header'] = ImageFont.truetype(dejavu_fontfile, self.FONT_CONFIG['header_size'])
                fonts['badge'] = ImageFont.truetype(liberation_fontfile, self.FONT_CONFIG['badge_size'])
                fonts['dest'] = ImageFont.truetype(dejavu_fontfile, self.FONT_CONFIG['dest_size'])
                fonts['time'] = ImageFont.truetype(nunito_fontfile, self.FONT_CONFIG['time_size'])
                fonts['time_now'] = ImageFont.truetype(nunito_fontfile, self.FONT_CONFIG['time_now_size'])
                fonts['weather'] = ImageFont.truetype(dejavu_fontfile, self.FONT_CONFIG['weather_size'])
                fonts['weather_temp'] = ImageFont.truetype(dejavu_fontfile, self.FONT_CONFIG['weather_temp_size'])
                logger.info(f"✓ Loaded TrueType fonts from {font_file}")
            except Exception as e:
                logger.warning(f"Could not load TrueType font: {e}")
                fonts = self._get_fallback_fonts()
        else:
            logger.warning("No suitable font found, using default fonts")
            fonts = self._get_fallback_fonts()
        
        return fonts
    
    def _get_fallback_fonts(self):
        """Get fallback fonts (default PIL fonts)
        
        Returns:
            Dict of font name -> ImageFont object
        """
        fonts = {}
        try:
            fonts['header'] = ImageFont.load_default(size=9)
            fonts['badge'] = ImageFont.load_default(size=7)
            fonts['dest'] = ImageFont.load_default(size=9)
            fonts['time'] = ImageFont.load_default(size=9)
            fonts['time_now'] = ImageFont.load_default(size=7)
            fonts['weather'] = ImageFont.load_default(size=8)
            fonts['weather_temp'] = ImageFont.load_default(size=9)
        except:
            # Very old PIL version
            default_font = ImageFont.load_default()
            fonts['header'] = default_font
            fonts['badge'] = default_font
            fonts['dest'] = default_font
            fonts['time'] = default_font
            fonts['time_now'] = default_font
            fonts['weather'] = default_font
            fonts['weather_temp'] = default_font
        
        logger.info("Using fallback default fonts")
        return fonts
    
    def try_init_matrix(self):
        """
        Try to initialize the LED matrix hardware
        Uses same API as basic_test.py which is proven to work
        """
        if Config.MATRIX_LIBRARY == "test":
            logger.info("MATRIX_LIBRARY=test - rendering to image files, no hardware")
            self.matrix = None
            return

        try:
            from rgbmatrix import RGBMatrix, RGBMatrixOptions
            logger.debug("rgbmatrix library found, initializing...")

            # Create options (same as basic_test.py)
            options = RGBMatrixOptions()
            options.rows = self.DISPLAY_HEIGHT
            options.cols = self.DISPLAY_WIDTH
            options.chain_length = Config.CHAIN_LENGTH
            options.parallel = Config.PARALLEL_CHAINS
            options.hardware_mapping = "regular"
            options.gpio_slowdown = Config.GPIO_SLOWDOWN
            options.brightness = 80
            
            # Create matrix
            self.matrix = RGBMatrix(options=options)
            logger.info("✓ LED matrix initialized with correct API")
            
        except ImportError as e:
            logger.debug(f"rgbmatrix library not available: {e}")
            self.matrix = None
        except Exception as e:
            logger.error(f"Failed to initialize LED matrix: {e}")
            logger.debug(f"Full error: {e}", exc_info=True)
            self.matrix = None
    
    def render_frame(self, direction, trains):
        """
        Render a complete frame to the LED matrix
        
        Args:
            direction: 'northbound' or 'southbound'
            trains: List of Train objects (up to 2)
        """
        try:
            # Increment frame counter for animations
            self.frame_count += 1
            
            # Create image for rendering
            img = Image.new('RGB', (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT), self.COLORS['black'])
            draw = ImageDraw.Draw(img)
            
            # STEP 1: Draw all sliding destination text first
            for idx, train in enumerate(trains[:2]):
                row_y = self.HEADER_HEIGHT + (idx * self.ROW_HEIGHT) + 2
                col2_x = self.COL_WIDTHS[0]
                font = self.fonts['dest']
                self.draw_destination_text_only(draw, train.destination, col2_x, row_y, font)
            
            # STEP 2: Draw black clipping rectangles to hide overflow
            for idx, train in enumerate(trains[:2]):
                row_y = self.HEADER_HEIGHT + (idx * self.ROW_HEIGHT) + 2
                col2_x = self.COL_WIDTHS[0]
                self.draw_clipping_rectangles(draw, col2_x, row_y)
            
            # STEP 3: Draw badges and time (on top of clipping rectangles)
            for idx, train in enumerate(trains[:2]):
                row_y = self.HEADER_HEIGHT + (idx * self.ROW_HEIGHT) + 2
                self.draw_train_badge(draw, train.route_id, row_y)
                
                # Draw time with conditional font size
                col3_x = self.COL_WIDTHS[0] + self.COL_WIDTHS[1]
                minutes = train.get_minutes_to_arrival()
                time_text = self.format_time_text(minutes)
                
                # Use smaller font for 'NOW', regular font for minutes
                if time_text == "NOW":
                    time_font = self.fonts['time_now']
                else:
                    time_font = self.fonts['time']
                
                bbox = draw.textbbox((0, 0), time_text, font=time_font)
                text_height = bbox[3] - bbox[1]
                time_y = row_y + (self.ROW_HEIGHT - text_height) // 2 - 1
                
                draw.text(
                    (col3_x + 1, time_y),
                    time_text,
                    font=time_font,
                    fill=self.COLORS['cyan']
                )
            
            # STEP 4: Draw header (NORTHBOUND/SOUTHBOUND) on top of everything
            self.draw_header(draw, direction)
            
            # Display or save
            if self.test_mode:
                self.save_test_image(img, direction)
            else:
                self.display_image(img)
                
        except Exception as e:
            logger.error(f"Error rendering frame: {e}", exc_info=True)
    
    def draw_header(self, draw, direction):
        """
        Draw header row showing full NORTHBOUND/SOUTHBOUND text
        Positioned 2 pixels higher than before
        Using OpenSans TrueType font
        
        Args:
            draw: PIL ImageDraw object
            direction: 'northbound' or 'southbound'
        """
        try:
            font = self.fonts['header']
            
            # Full direction text
            direction_text = "NORTHBOUND" if direction == 'northbound' else "SOUTHBOUND"
            
            # Get text dimensions
            bbox = draw.textbbox((0, 0), direction_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Center horizontally, position 2 pixels higher (use y=0)
            x_pos = max(0, (self.DISPLAY_WIDTH - text_width) // 2)
            y_pos = -1  # 2 pixels higher than default centered position
            
            # Draw text
            draw.text(
                (x_pos, y_pos),
                direction_text,
                font=font,
                fill=self.COLORS['white']
            )
            
        except Exception as e:
            logger.error(f"Error drawing header: {e}")
    
    def draw_destination_text_only(self, draw, destination, x_pos, y_pos, font):
        """
        Draw ONLY the destination text with sliding animation if too long
        Does not draw clipping rectangles - those are drawn separately
        
        Args:
            draw: PIL ImageDraw object
            destination: Destination string
            x_pos: X position of column
            y_pos: Y position
            font: Font to use
        """
        try:
            # Get text dimensions
            bbox = draw.textbbox((0, 0), destination, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Max width for destination column
            max_width = self.DEST_MAX_WIDTH
            
            # Vertically center text in row
            text_y = y_pos + (self.ROW_HEIGHT - text_height) // 2
            
            # Calculate offset for animation
            offset = self._calculate_slide_offset(destination, max_width)
            
            # Draw text with offset (handles both short and long text)
            draw.text(
                (x_pos + 2 - offset, text_y),
                destination,
                font=font,
                fill=self.COLORS['white']
            )
            
        except Exception as e:
            logger.error(f"Error drawing destination text: {e}")
    
    def draw_clipping_rectangles(self, draw, x_pos, y_pos):
        """
        Draw black rectangles to hide text overflow on both sides
        This is drawn AFTER the text but BEFORE badges and time
        
        Args:
            draw: PIL ImageDraw object
            x_pos: X position of destination column
            y_pos: Y position of row
        """
        try:
            max_width = self.DEST_MAX_WIDTH
            
            # Left clipping rectangle - hide overflow into badge column
            draw.rectangle(
                [(0, y_pos), (x_pos + 2 - 1, y_pos + self.ROW_HEIGHT - 1)],
                fill=self.COLORS['black']
            )
            
            # Right clipping rectangle - hide overflow into time column
            draw.rectangle(
                [(x_pos + 2 + max_width, y_pos), (self.DISPLAY_WIDTH - 1, y_pos + self.ROW_HEIGHT - 1)],
                fill=self.COLORS['black']
            )
            
        except Exception as e:
            logger.error(f"Error drawing clipping rectangles: {e}")
    
    def draw_train_badge(self, draw, route_id, y_pos):
        """
        Draw train number in yellow text with red circle
        Positioned 2 pixels higher and 1 pixel to the right
        Using OpenSans TrueType font
        
        Args:
            draw: PIL ImageDraw object
            route_id: Train route ID (e.g., 'R')
            y_pos: Y position of row
        """
        try:
            font = self.fonts['badge']
            
            # Circle parameters
            circle_x = 5
            circle_y = y_pos + self.ROW_HEIGHT // 2 - 0
            circle_radius = 5
            
            # Draw red circle outline only
            draw.ellipse(
                [(circle_x - circle_radius, circle_y - circle_radius),
                 (circle_x + circle_radius, circle_y + circle_radius)],
                outline=self.COLORS['red'],
                fill=self.COLORS['black']
            )
            
            # Get text dimensions
            bbox = draw.textbbox((0, 0), route_id, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Center in circle, with +1 pixel right and -2 pixels up
            text_x = circle_x - text_width // 2 + 0  # 1 pixel right
            text_y = circle_y - text_height // 2 - 2  # 2 pixels up
            
            # Draw text
            draw.text(
                (text_x, text_y),
                route_id,
                font=font,
                fill=self.COLORS['yellow']
            )
            
        except Exception as e:
            logger.error(f"Error drawing train badge: {e}")
    
    def draw_destination_sliding(self, draw, destination, x_pos, y_pos, font):
        """
        Draw destination text with sliding animation if too long
        Text slides back and forth to show full length
        Clipped to stay within destination column bounds
        
        Args:
            draw: PIL ImageDraw object
            destination: Destination string
            x_pos: X position of column
            y_pos: Y position
            font: Font to use
        """
        try:
            # Get text dimensions
            bbox = draw.textbbox((0, 0), destination, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Max width for destination column
            max_width = self.DEST_MAX_WIDTH
            
            # Vertically center text in row
            text_y = y_pos + (self.ROW_HEIGHT - text_height) // 2
            
            # If text fits, just draw it
            if text_width <= max_width:
                draw.text(
                    (x_pos + 2, text_y),
                    destination,
                    font=font,
                    fill=self.COLORS['white']
                )
            else:
                # Text is too long - animate sliding with clipping
                offset = self._calculate_slide_offset(destination, max_width)
                
                # Draw text directly on main image with offset
                # The text will naturally be clipped at the image boundaries
                # We offset it to create the sliding effect
                draw.text(
                    (x_pos + 2 - offset, text_y),
                    destination,
                    font=font,
                    fill=self.COLORS['white']
                )
                
                # Fill in areas outside the destination column to hide overflow
                # Left side (badge column) - draw black rectangle to hide overflow
                img = draw.im
                for py in range(y_pos, y_pos + self.ROW_HEIGHT):
                    for px in range(x_pos + 2):
                        if px >= 0:
                            img.putpixel((px, py), self.COLORS['black'])
                
                # Right side (time column) - draw black rectangle to hide overflow
                for py in range(y_pos, y_pos + self.ROW_HEIGHT):
                    for px in range(x_pos + 2 + max_width, self.DISPLAY_WIDTH):
                        if px < self.DISPLAY_WIDTH:
                            img.putpixel((px, py), self.COLORS['black'])
                
        except Exception as e:
            logger.error(f"Error drawing destination: {e}")
    
    def _calculate_slide_offset(self, text, max_width):
        """
        Calculate the horizontal offset for sliding text animation
        Text slides back and forth smoothly
        
        Args:
            text: Text to slide
            max_width: Maximum width available
            
        Returns:
            Pixel offset for text position
        """
        try:
            font = self.fonts['dest']
            bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox(
                (0, 0), text, font=font
            )
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                return 0
            
            # Distance to slide
            slide_distance = text_width - max_width + 5  # 5px margin
            
            # Get animation state
            cycle = self.SLIDE_CONFIG['cycle_duration']
            speed = self.SLIDE_CONFIG['speed']
            pause = self.SLIDE_CONFIG['pause_frames']
            
            # Calculate position in cycle
            frame = self.frame_count % cycle
            
            # Phases:
            # 0: Pause at start
            # pause: Slide right
            # pause + slide_frames: Pause at end
            # pause + slide_frames + pause: Slide left
            # Total = cycle
            
            slide_frames = (cycle - 2 * pause) // 2
            
            if frame < pause:
                # Pause at start
                offset = 0
            elif frame < pause + slide_frames:
                # Slide right
                progress = frame - pause
                offset = int((progress / slide_frames) * slide_distance)
            elif frame < pause + slide_frames + pause:
                # Pause at end
                offset = slide_distance
            else:
                # Slide left
                progress = frame - (pause + slide_frames + pause)
                offset = int(slide_distance - (progress / slide_frames) * slide_distance)
            
            return offset
            
        except Exception as e:
            logger.error(f"Error calculating slide offset: {e}")
            return 0
    
    def format_time_text(self, minutes):
        """Format arrival time for display"""
        if minutes == 0:
            return "NOW"
        elif minutes == 1:
            return "1m"
        else:
            return f"{minutes}m"
    
    def display_image(self, pil_image):
        """
        Display PIL Image on LED matrix using SetPixel() API
        
        Args:
            pil_image: PIL Image object (RGB mode, 64x32)
        """
        try:
            if not self.matrix:
                logger.error("Matrix not initialized")
                return
            
            # Ensure image is in RGB mode
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Get image data
            pixels = pil_image.load()
            
            # Set each pixel on the matrix using SetPixel()
            for x in range(self.DISPLAY_WIDTH):
                for y in range(self.DISPLAY_HEIGHT):
                    r, g, b = pixels[x, y]
                    self.matrix.SetPixel(x, y, r, g, b)
            
            logger.debug("Frame displayed on matrix using SetPixel()")
            
        except AttributeError as e:
            logger.error(f"Matrix method error: {e}")
        except Exception as e:
            logger.error(f"Error displaying image: {e}", exc_info=True)
    
    def save_test_image(self, img, direction):
        """
        Save image to file for testing (in test mode)
        
        Args:
            img: PIL Image object
            direction: Direction name for filename
        """
        try:
            filename = os.path.join(
                tempfile.gettempdir(),
                f"subway_display_{direction}_{int(time.time())}.png",
            )
            img.save(filename)
            logger.debug(f"Saved test image: {filename}")
        except Exception as e:
            logger.debug(f"Could not save test image: {e}")
    
    def cleanup(self):
        """Clean up display resources"""
        try:
            if self.matrix:
                # Clear display
                self.matrix.Clear()
                logger.info("Display cleared on shutdown")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
