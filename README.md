# Subway Arrival Display

A real-time NYC subway arrival board for a 64×32 RGB LED matrix, driven by a
Raspberry Pi. It rotates through northbound arrivals, southbound arrivals, and
an info panel with a clock, the weather, and a Nyan Cat.

Built so you can glance at a wall instead of unlocking your phone on the way out
the door.

<!-- TODO: hero photo — docs/img/hero.jpg -->

## What it shows

| Frame | Contents |
|---|---|
| Northbound | Next two trains, route bullet, terminal, minutes away |
| Southbound | Same, other direction |
| Info panel | Nyan Cat, current time, conditions, temperature, 24h high/low |

Each frame holds for 10 seconds by default. Arrivals refresh every 10 seconds,
weather every 30 minutes.

<!-- TODO: per-frame screenshots — docs/img/northbound.jpg, southbound.jpg, info-panel.jpg -->

## Hardware

| Part | Notes |
|---|---|
| Raspberry Pi | Any model with 40-pin GPIO. A Zero 2 W is plenty. |
| 64×32 RGB LED matrix | HUB75, 3-4mm pitch |
| Adafruit RGB Matrix Bonnet (or HAT) | Saves a lot of jumper wiring |
| 5V power supply, 4A+ | **The panel needs its own supply.** Do not run it off the Pi. |

<!-- TODO: hardware flat-lay photo — docs/img/hardware.jpg -->

## Install

On the Pi:

```bash
git clone https://github.com/saurabhmalani1994/subway-arrival-display.git
cd subway-arrival-display
pip install -r requirements.txt
```

Then build the LED driver, which is not on PyPI:

```bash
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
make build-python PYTHON=$(which python3)
sudo make install-python PYTHON=$(which python3)
```

Verify the panel lights up before going further:

```bash
sudo python3 basic_test.py
```

## Configure

Everything is environment-driven — you should not need to edit any source file.

```bash
cp .env.example .env
```

The defaults run at Times Square with no further setup. The MTA's GTFS-realtime
feeds are currently open, so **no API key is required**.

To use your own station:

```bash
python tools/find_stops.py --search "borough hall" --routes
```

Then set the result in `.env`:

```
STOP_ID=232
ROUTE_IDS=4,5
STOP_NAME=Borough Hall
```

Use the **parent** stop ID (`R16`), not a directional one (`R16N`). Weather
follows the station automatically — the NOAA forecast grid is resolved from its
coordinates at runtime — or set `LATITUDE`/`LONGITUDE` yourself.

Four presets ship in `config.py`: `times-square`, `grand-central`,
`union-square`, `atlantic-av`. Select one with `STATION=grand-central`.

## Run

```bash
sudo python3 main.py
```

`sudo` is required — the matrix driver needs direct GPIO access.

To develop without hardware, render frames to PNG files instead:

```bash
MATRIX_LIBRARY=test python3 main.py
```

## Run on boot

```bash
sudo cp deploy/subway-display.service /etc/systemd/system/
sudo systemctl enable --now subway-display.service
journalctl -u subway-display -f
```

Edit `WorkingDirectory` and `ExecStart` in the unit if you cloned somewhere
other than `/home/pi`.

## Keeping a headless Pi reachable

A Pi behind a wall panel that drops off Wi-Fi after a power cut is genuinely
annoying to recover — you end up pulling the whole thing apart for a monitor and
keyboard. **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) covers how to
avoid that**, and it is worth reading before you mount anything:

- a Wi-Fi watchdog that reconnects and, failing that, reboots
- saving a phone hotspot as a pre-authorised rescue network
- Tailscale for a stable address from anywhere

Set the rescue network up *before* you need it. It does not help retroactively.

## Configuration reference

| Variable | Default | Purpose |
|---|---|---|
| `STATION` | `times-square` | Preset from `config.py` |
| `STOP_ID` | from preset | GTFS parent stop ID |
| `ROUTE_IDS` | from preset | Comma-separated routes |
| `STOP_NAME` | from preset | Header text |
| `LATITUDE` / `LONGITUDE` | from preset | Weather location |
| `MATRIX_LIBRARY` | `rgbmatrix` | `test` renders to PNG |
| `GPIO_SLOWDOWN` | `2` | Raise if the panel flickers |
| `FRAME_DURATION` | `10` | Seconds per train frame |
| `INFO_PANEL_DURATION` | `10` | Seconds on the info panel |
| `TIMEZONE` | `America/New_York` | Clock timezone |
| `VERIFY_TLS` | `true` | Leave on; see troubleshooting |
| `MTA_API_KEY` | empty | Not currently needed |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose output |

## Notes

Arrival times come from the MTA's realtime feed and are as accurate as the MTA
is — which is to say, usually good and occasionally fictional.

"Northbound" and "southbound" are railroad directions from the GTFS data, not
compass directions. In parts of Brooklyn and Queens they read strangely; that is
the feed, not a bug.

## Credits and license

Code is MIT — see [LICENSE](LICENSE).

Nyan Cat is by **Christopher Torres** and is **not** covered by that license.
It's used here decoratively in a personal, non-commercial project. Replace the
assets before using this commercially. Full attributions in
[CREDITS.md](CREDITS.md).
