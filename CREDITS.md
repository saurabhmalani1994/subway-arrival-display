# Credits

## Nyan Cat

The animation on the info panel is **Nyan Cat**, created by **Christopher Torres**
in 2011. Original: <https://www.nyan.cat/>

It appears here purely as decoration in a personal, non-commercial hobby project.
Files: `assets/nyancat.gif`, `assets/nyancat_frames/`, and the base64 pixel data
in `nyan_frames.py`.

**The artwork is not mine and is not covered by this project's MIT license.** If
you fork this for anything commercial, or want to redistribute it, replace those
assets or seek permission from the rights holder. The code works with any
animation of the right dimensions — see `NYAN_GIF_PATH` in `config.py`.

## Data

- **Train arrivals** — [MTA GTFS-realtime feeds](https://api.mta.info/), New York
  City Transit. Public data.
- **Weather** — [NOAA / weather.gov API](https://www.weather.gov/documentation/services-web-api).
  Public domain, no authentication. US locations only.

## Software

- [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) by Henner
  Zeller — the LED panel driver doing the actual work (GPL-2.0).
- [Pillow](https://python-pillow.org/) for rendering.
- [gtfs-realtime-bindings](https://github.com/MobilityData/gtfs-realtime-bindings)
  for parsing the protobuf feeds.

Fonts are DejaVu, Liberation, and Nunito as installed by the system; each carries
its own license.
