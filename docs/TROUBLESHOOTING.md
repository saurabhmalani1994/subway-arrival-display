# Troubleshooting

Most of this file is about one problem: **the Pi is headless, and when Wi-Fi
fails you have no way in.** Everything else is minor by comparison.

---

## Do this first: the rescue network

If your home Wi-Fi permanently changes — new router, new password, renamed SSID
— the Pi cannot rejoin it and cannot tell you so. No watchdog fixes that. The
only way back in without disassembling the enclosure is a **second network the
Pi already knows about**.

Save your phone's hotspot now, while everything still works:

```bash
# On the Pi, with your phone's hotspot switched on:
sudo nmcli device wifi connect "<HOTSPOT_SSID>" password "<HOTSPOT_PASSWORD>"

# Then make sure home wifi is still preferred when both are available:
sudo nmcli connection modify "<HOME_SSID>"     connection.autoconnect-priority 100
sudo nmcli connection modify "<HOTSPOT_SSID>"  connection.autoconnect-priority 10
```

To use it later: turn on your phone hotspot, wait ~60s, connect your laptop to
that same hotspot, and SSH to the Pi.

```bash
ssh pi@raspberrypi.local     # or find it in your phone's hotspot client list
```

**Rehearse this once.** Turn off your home Wi-Fi deliberately, confirm you can
reach the Pi over the hotspot, then turn it back on. An untested rescue path is
not a rescue path.

---

## The power-cycle failure

**Symptom:** after a power cut the display is blank or stuck, and the Pi is not
on the network.

**Cause:** the Pi boots in ~20 seconds. A consumer router takes 1-2 minutes to
come back. The Pi looks for a network that does not exist yet, fails, and
depending on the NetworkManager version may not retry aggressively enough. The
display service, meanwhile, has already started and made its first failed fetch.

**Two fixes, both in `deploy/`:**

1. `subway-display.service` orders itself `After=network-online.target`, so the
   app does not start until the network is actually up, and `Restart=always`
   brings it back if it dies anyway.
2. `wifi-watchdog.timer` runs a check every 2 minutes: ping the default gateway,
   and after repeated failures re-associate, then eventually reboot.

Install both:

```bash
# Display service
sudo cp deploy/subway-display.service /etc/systemd/system/
sudo systemctl enable --now subway-display.service

# Wi-Fi watchdog
sudo cp deploy/wifi-watchdog.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/wifi-watchdog.sh
sudo cp deploy/wifi-watchdog.service deploy/wifi-watchdog.timer /etc/systemd/system/
sudo systemctl enable --now wifi-watchdog.timer
```

Watch it work:

```bash
journalctl -u wifi-watchdog -f
systemctl list-timers wifi-watchdog.timer
```

The health check is "can I reach my default gateway", not "am I on the home
SSID" — deliberately, so that a rescue via phone hotspot counts as healthy and
the watchdog doesn't reboot you off it.

**Test it for real:** boot the Pi with the router switched off. You should see
`NO WIFI` on the matrix, failures accumulating in the journal, and automatic
recovery within ~2 minutes of the router returning, with no hands on the Pi.

---

## Finding the Pi on the network

The display deliberately does **not** show its IP address — the screen is for
train times, and a boot-time IP frame would delay them every restart.

```bash
ssh pi@raspberrypi.local          # mDNS, usually works
sudo nmap -sn 192.168.1.0/24      # or scan the subnet
```

Better, set a **DHCP reservation** in your router so the Pi always gets the same
address.

Best, install [Tailscale](https://tailscale.com/) for a stable name reachable
from anywhere:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Be clear about what this does and doesn't do: Tailscale ends "what IP is it on
now" permanently, including from outside your house. It does **nothing** when
the Pi has no Wi-Fi at all — that is what the watchdog and the rescue hotspot
are for.

---

## `NO WIFI` on the display

This is the app telling you it has no train data and no working network. It
appears only after several consecutive failed updates, and only when there is
nothing valid left to show — a brief API hiccup keeps the last known arrivals on
screen instead.

So: the display is fine, the network is not. See the sections above.

---

## TLS / certificate errors

**Symptom:** `SSLError`, `CERTIFICATE_VERIFY_FAILED`, or weather and trains both
failing while the network is otherwise fine.

Nearly always the Pi's **system clock**. A Pi has no battery-backed clock; if it
boots without a network it can come up in 1970, and every certificate looks
"not yet valid".

```bash
timedatectl status                       # is the time even right?
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
```

Second most likely, a stale CA bundle:

```bash
sudo apt update && sudo apt install --reinstall ca-certificates
sudo update-ca-certificates
```

There is a `VERIFY_TLS=false` escape hatch in `.env`. **Treat it as a diagnostic,
not a fix.** It disables certificate verification for all API traffic and the app
logs a warning on every start while it is off. If it makes things work, your
clock or CA bundle is wrong — fix that and turn it back on.

---

## Display problems

**Flickering or unstable pixels** — the Pi is outrunning the panel. Raise
`GPIO_SLOWDOWN` in `.env`, one step at a time:

```
GPIO_SLOWDOWN=3     # try 4 on a Pi 4 or newer
```

**Nothing on the panel at all** — check power first. The matrix needs its own 5V
supply; it cannot run off the Pi's GPIO rail. Then:

```bash
sudo python3 basic_test.py     # solid colors, corners, gradient
sudo python3 diagnose_display.py
```

Both need `sudo` — the driver requires direct GPIO access.

**Wrong colors or mirrored output** — you likely have a different panel variant.
Adjust `hardware_mapping` in `display_manager.py` (`regular` vs `adafruit-hat`).

---

## No trains

```bash
python tools/find_stops.py --search "your station" --routes
```

Check that your `STOP_ID` is the **parent** stop (`R16`), not a directional one
(`R16N`), and that `ROUTE_IDS` actually serve it. Several stations share a name
across different lines with completely different IDs — Times Sq is `R16` on the
NQRW but `127` on the 1/2/3.

Note that "northbound" and "southbound" here are railroad direction from the
GTFS feed, not compass direction. They can be counterintuitive in Brooklyn and
Queens.
