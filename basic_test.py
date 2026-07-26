#!/usr/bin/env python3
"""
Basic functional test for a 32x64 RGB LED matrix panel on Raspberry Pi.

- Cycles solid colors (R, G, B, Y, M, C, W, Black)
- Shows a checkerboard pattern
- Lights each corner in different colors
- Draws a color gradient

Run with:
    sudo python3 basic_test.py
"""

import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions


def make_matrix():
    options = RGBMatrixOptions()
    options.rows = 32              # panel height
    options.cols = 64              # panel width
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = "regular"  # "adafruit-hat" if using that HAT/bonnet
    options.gpio_slowdown = 2      # bump to 3–4 if you see flicker
    options.brightness = 80        # 0–100

    return RGBMatrix(options=options)


def solid_color_test(matrix, delay=0.8):
    colors = [
        (255, 0, 0),    # red
        (0, 255, 0),    # green
        (0, 0, 255),    # blue
        (255, 255, 0),  # yellow
        (255, 0, 255),  # magenta
        (0, 255, 255),  # cyan
        (255, 255, 255),# white
        (0, 0, 0),      # black / off
    ]
    for r, g, b in colors:
        matrix.Fill(r, g, b)
        time.sleep(delay)


def checkerboard_test(matrix, block_size=4, delay=2.0):
    width = matrix.width
    height = matrix.height
    matrix.Clear()
    for x in range(width):
        for y in range(height):
            if ((x // block_size) + (y // block_size)) % 2 == 0:
                matrix.SetPixel(x, y, 255, 255, 255)
            else:
                matrix.SetPixel(x, y, 0, 0, 0)
    time.sleep(delay)


def corners_test(matrix, delay=1.5):
    width = matrix.width
    height = matrix.height
    matrix.Clear()

    # Top-left: red
    matrix.SetPixel(0, 0, 255, 0, 0)
    # Top-right: green
    matrix.SetPixel(width - 1, 0, 0, 255, 0)
    # Bottom-left: blue
    matrix.SetPixel(0, height - 1, 0, 0, 255)
    # Bottom-right: yellow
    matrix.SetPixel(width - 1, height - 1, 255, 255, 0)

    time.sleep(delay)


def gradient_test(matrix, delay=2.5):
    width = matrix.width
    height = matrix.height
    matrix.Clear()

    for x in range(width):
        for y in range(height):
            r = int(255 * x / max(1, width - 1))
            g = int(255 * y / max(1, height - 1))
            b = int(255 * (1 - (x / max(1, width - 1))))
            matrix.SetPixel(x, y, r, g, b)
    time.sleep(delay)


def brightness_sweep_test(matrix, step=15, hold=0.4):
    for b in range(10, 101, step):
        matrix.brightness = b
        matrix.Fill(255, 255, 255)
        time.sleep(hold)
    matrix.brightness = 80


def main():
    matrix = make_matrix()
    try:
        while True:
            solid_color_test(matrix)
            checkerboard_test(matrix)
            corners_test(matrix)
            gradient_test(matrix)
            brightness_sweep_test(matrix)
    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == "__main__":
    main()
