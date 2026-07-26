#!/usr/bin/env python3
"""
LED Display Diagnostic Tool
Tests matrix initialization, image rendering, and display functionality
"""

import logging
import sys
import time
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_imports():
    """Test if required libraries can be imported"""
    print("\n" + "="*70)
    print("TEST 1: Checking Python Libraries")
    print("="*70)
    
    tests = {
        'PIL': 'from PIL import Image, ImageDraw, ImageFont',
        'numpy': 'import numpy as np',
        'rgbmatrix': 'from rgbmatrix import RGBMatrix, RGBMatrixOptions',
    }
    
    for name, import_stmt in tests.items():
        try:
            exec(import_stmt)
            print(f"✓ {name:15} - Available")
        except ImportError as e:
            print(f"✗ {name:15} - MISSING: {e}")
            return False
    
    return True


def test_matrix_init():
    """Test matrix initialization"""
    print("\n" + "="*70)
    print("TEST 2: Matrix Hardware Initialization")
    print("="*70)
    
    try:
        from rgbmatrix import RGBMatrix, RGBMatrixOptions
        
        logger.debug("Creating RGBMatrixOptions...")
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = 'adafruit-hat'
        options.gpio_slowdown = 2
        options.brightness = 100
        
        logger.debug("Attempting to initialize RGBMatrix...")
        matrix = RGBMatrix(options=options)
        
        print("✓ Matrix initialized successfully")
        print(f"  Resolution: {options.cols}x{options.rows}")
        print(f"  Hardware mapping: {options.hardware_mapping}")
        
        return matrix
        
    except PermissionError as e:
        print(f"✗ Permission denied: {e}")
        print("  Hint: Run with 'sudo' or fix GPIO permissions")
        return None
        
    except FileNotFoundError as e:
        print(f"✗ Device not found: {e}")
        print("  Hint: Check GPIO wiring and enable SPI/I2C")
        return None
        
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        logger.debug(f"Full error: {e}", exc_info=True)
        return None


def test_image_creation():
    """Test image creation and rendering"""
    print("\n" + "="*70)
    print("TEST 3: Image Creation and Rendering")
    print("="*70)
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        logger.debug("Creating test image...")
        img = Image.new('RGB', (64, 32), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw some test content
        logger.debug("Drawing test content...")
        draw.rectangle([(0, 0), (63, 7)], outline=(100, 100, 100), fill=(0, 0, 0))
        draw.text((2, 1), "TEST", fill=(255, 255, 255))
        
        # Draw a simple pattern
        for y in range(8, 32, 4):
            draw.line([(0, y), (63, y)], fill=(50, 50, 50))
        
        print("✓ Test image created successfully")
        print(f"  Size: {img.size}")
        print(f"  Mode: {img.mode}")
        
        # Save for inspection
        filename = "/tmp/display_test.png"
        img.save(filename)
        print(f"✓ Test image saved to: {filename}")
        
        return img
        
    except Exception as e:
        print(f"✗ Image creation failed: {e}")
        return None


def test_matrix_display(matrix, img):
    """Test displaying image on matrix"""
    print("\n" + "="*70)
    print("TEST 4: Displaying Image on Matrix")
    print("="*70)
    
    if matrix is None:
        print("⊘ Matrix not initialized, skipping display test")
        return False
    
    if img is None:
        print("⊘ Test image not created, skipping display test")
        return False
    
    try:
        logger.debug("Calling matrix.SetImage()...")
        
        # Ensure image is RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Display on matrix
        matrix.SetImage(img)
        
        print("✓ Image displayed on matrix")
        print("  Verify visual output on the LED display")
        
        return True
        
    except AttributeError as e:
        print(f"✗ Matrix method error: {e}")
        print("  Hint: Check rgbmatrix library version")
        return False
        
    except Exception as e:
        print(f"✗ Display failed: {e}")
        logger.debug(f"Full error: {e}", exc_info=True)
        return False


def test_matrix_clear(matrix):
    """Test clearing the matrix"""
    print("\n" + "="*70)
    print("TEST 5: Clearing Matrix")
    print("="*70)
    
    if matrix is None:
        print("⊘ Matrix not initialized, skipping clear test")
        return False
    
    try:
        logger.debug("Creating black image for clear...")
        clear_img = Image.new('RGB', (64, 32), (0, 0, 0))
        
        logger.debug("Calling matrix.SetImage() with black image...")
        matrix.SetImage(clear_img)
        
        print("✓ Matrix cleared successfully")
        return True
        
    except Exception as e:
        print(f"✗ Clear failed: {e}")
        return False


def test_from_display_manager():
    """Test using the actual DisplayManager class"""
    print("\n" + "="*70)
    print("TEST 6: DisplayManager Class")
    print("="*70)
    
    try:
        from display_manager import DisplayManager
        from mta_client import Train
        
        logger.debug("Initializing DisplayManager...")
        display = DisplayManager()
        
        print(f"✓ DisplayManager initialized")
        print(f"  Test mode: {display.test_mode}")
        print(f"  Matrix: {'Detected' if not display.test_mode else 'Not detected'}")
        
        # Create test train
        now = int(time.time())
        test_train = Train('R', 'Whitehall', now + 300, 'northbound')
        
        logger.debug("Rendering test frame...")
        display.render_frame('northbound', [test_train])
        
        print("✓ Test frame rendered")
        
        if display.test_mode:
            print("  Image saved to /tmp/ (test mode)")
        else:
            print("  Image displayed on LED matrix")
        
        display.cleanup()
        return True
        
    except Exception as e:
        print(f"✗ DisplayManager test failed: {e}")
        logger.debug(f"Full error: {e}", exc_info=True)
        return False


def main():
    """Run all diagnostic tests"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "LED Display Diagnostic Tool" + " "*25 + "║")
    print("║" + " "*10 + "Troubleshoot matrix initialization and display" + " "*12 + "║")
    print("╚" + "="*68 + "╝")
    
    results = []
    
    # Test 1: Imports
    if not test_imports():
        print("\n✗ Required libraries missing. Install with:")
        print("  sudo apt-get install python3-pil")
        print("  pip install rgbmatrix numpy")
        return 1
    
    # Test 2: Matrix init
    matrix = test_matrix_init()
    
    # Test 3: Image creation
    img = test_image_creation()
    
    # Test 4: Display image
    if matrix and img:
        test_matrix_display(matrix, img)
    
    # Test 5: Clear
    if matrix:
        test_matrix_clear(matrix)
    
    # Test 6: DisplayManager
    test_from_display_manager()
    
    # Summary
    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    
    if matrix:
        print("✓ LED Matrix: Connected and responsive")
    else:
        print("✗ LED Matrix: Not connected or not responding")
        print("  Check:")
        print("  1. Power connection to matrix")
        print("  2. GPIO ribbon cable connections")
        print("  3. Raspberry Pi SPI/I2C enabled")
        print("  4. Run with 'sudo' for GPIO access")
    
    print("\n" + "="*70)
    
    return 0 if matrix else 1


if __name__ == '__main__':
    sys.exit(main())
