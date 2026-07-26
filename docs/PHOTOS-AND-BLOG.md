# Photo checklist & blog outline

Working notes, not part of the shipped docs. Delete this file before you care
about the repo looking tidy, or keep it — it's harmless.

## Photo checklist

The README has `<!-- TODO -->` markers where each of these goes.

**The one technical trick:** an LED matrix is strobing far faster than your eye
but not faster than a phone sensor. Shot on auto, you get dark bands across the
panel. Use your camera's pro/manual mode and set shutter to **1/30s or slower**.
Longer exposure blends the refresh cycles and the panel reads solid.

| Shot | File | Notes |
|---|---|---|
| Hero — display in place on the wall | `docs/img/hero.jpg` | Dim ambient light so the panel isn't blown out. Slight angle beats dead-on. Include a bit of context (wall, doorway) so the scale reads. |
| Northbound frame | `docs/img/northbound.jpg` | Straight on, fills the frame |
| Southbound frame | `docs/img/southbound.jpg` | Same framing as above |
| Info panel | `docs/img/info-panel.jpg` | Time the shot so Nyan Cat is mid-stride |
| Hardware flat-lay | `docs/img/hardware.jpg` | Pi, bonnet, panel, PSU unassembled on a plain surface, top-down, even light |

**Highest-value single asset:** a ~10 second video of one full frame rotation,
converted to a GIF and dropped at the top of the README. It shows the sliding
destination text and the Nyan animation, neither of which survive a still. Keep
it under ~5 MB or GitHub will be slow to load it.

Resize stills to ~1600px wide and keep each under 1 MB — `docs/img/` is in git
and photos are what bloat repos.

## Blog outline

Not a draft. Confirm venue and target length before writing — that changes how
much of the middle survives.

**1. The itch**
Standing at the door, phone out, checking whether to run for the R. A wall
display is a solved problem for the MTA and an unsolved one for apartments.

**2. The feed is public, which is not the same as easy**
- GTFS-realtime is protobuf, not JSON — the first surprise
- Feeds are split by line group (`gtfs-nqrw`, `gtfs-ace`, …), so "which trains
  stop here" means fetching several and merging
- Stop IDs are opaque (`R16`), differ per line *at the same station*, and carry
  N/S suffixes for direction
- "Northbound" is railroad direction, not compass direction. In Brooklyn this
  produces confidently wrong output until you notice.
- Good place for the concrete before/after of the `direction_id` confusion

**3. 2048 pixels is a real constraint**
- 64×32 means every label is a budget negotiation; terminal names get truncated
  to fit and you end up hand-tuning abbreviations
- Sliding text as the escape hatch, and the clipping bugs that come with it
- Font rendering at 7px — where TrueType stops helping
- The Pillow decoder detour with the Nyan frames, and why the animation ended up
  base64'd into a `.py` file

**4. The part nobody warns you about: it's a headless computer behind a wall**
*This is the strongest section — lead the technical half with it if the venue
allows.*
- Everything works until the first power cut
- The Pi boots in 20s, the router takes 2 minutes, the Pi gives up
- No screen, no keyboard, no network = disassemble the enclosure
- Three fixes, only one of which actually recovers anything: watchdog (transient
  failures), pre-saved phone hotspot (permanent failures), fault frame
  (diagnosis only, fixes nothing)
- The general lesson: for a device you can't reach, recovery paths are a feature,
  and an untested one doesn't count

**5. Nyan Cat**
Short. It's there because it's funny, it made the info panel worth looking at,
and the attribution question turned out to be more interesting than expected —
MIT on the code, explicitly not on the art.

**6. What I'd do differently**
- Config-driven from day one instead of hardcoding a station and unpicking it later
- TLS verification off "temporarily" survived far longer than it should have;
  the actual bug was the Pi's clock
- Don't commit 37 MB of GTFS text you only need for a one-off lookup

**Threads worth pulling if the piece needs length:** what open transit data
actually costs to consume; why every hobbyist eventually builds a status display;
the maintenance tail of a device that lives on a wall.
