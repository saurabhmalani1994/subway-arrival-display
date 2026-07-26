#!/usr/bin/env python3
"""
Find the GTFS stop ID for your station.

The MTA identifies stops with short codes (Times Sq 42 St on the NQRW is "R16").
You need one to configure this display. This downloads the MTA's static GTFS
bundle, caches it, and searches it.

    python tools/find_stops.py --search "times sq"
    python tools/find_stops.py --search "union" --routes

The bundle is ~40 MB and is cached in gtfs_static/ (gitignored). Delete that
directory to force a re-download.
"""

import argparse
import csv
import io
import os
import sys
import zipfile

import requests

GTFS_STATIC_URL = "http://web.mta.info/developers/data/nyct/subway/google_transit.zip"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "gtfs_static")


def ensure_gtfs(force=False):
    """Download and extract the static GTFS bundle if not already cached."""
    stops_path = os.path.join(CACHE_DIR, "stops.txt")
    if os.path.exists(stops_path) and not force:
        return CACHE_DIR

    print(f"Downloading GTFS static data from {GTFS_STATIC_URL} ...")
    try:
        response = requests.get(GTFS_STATIC_URL, timeout=120)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        sys.exit(
            f"ERROR: could not download GTFS data: {e}\n"
            f"Check https://www.mta.info/developers for the current URL."
        )

    os.makedirs(CACHE_DIR, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
        bundle.extractall(CACHE_DIR)
    print(f"Extracted to {CACHE_DIR}")
    return CACHE_DIR


def load_stops(gtfs_dir):
    """Return parent stops (the ones without an N/S direction suffix)."""
    with open(os.path.join(gtfs_dir, "stops.txt"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Directional stops are the parent ID plus N or S. Configure with the parent.
    return [r for r in rows if not r["stop_id"][-1] in ("N", "S")]


def routes_at_stop(gtfs_dir, stop_id):
    """Which routes serve a stop, via stop_times -> trips."""
    trip_to_route = {}
    with open(os.path.join(gtfs_dir, "trips.txt"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            trip_to_route[row["trip_id"]] = row["route_id"]

    routes = set()
    with open(os.path.join(gtfs_dir, "stop_times.txt"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["stop_id"].rstrip("NS") == stop_id:
                route = trip_to_route.get(row["trip_id"])
                if route:
                    routes.add(route)
    return sorted(routes)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--search", required=True,
                        help="Part of the station name, case insensitive")
    parser.add_argument("--routes", action="store_true",
                        help="Also list routes serving each match (slow, reads stop_times)")
    parser.add_argument("--refresh", action="store_true",
                        help="Re-download the GTFS bundle")
    args = parser.parse_args()

    gtfs_dir = ensure_gtfs(force=args.refresh)
    needle = args.search.lower()
    matches = [s for s in load_stops(gtfs_dir) if needle in s["stop_name"].lower()]

    if not matches:
        print(f"No stops matching '{args.search}'.")
        return

    print(f"\n{len(matches)} match(es) for '{args.search}':\n")
    for stop in matches:
        line = f"  {stop['stop_id']:<8} {stop['stop_name']}"
        if args.routes:
            line += f"   routes: {', '.join(routes_at_stop(gtfs_dir, stop['stop_id'])) or '?'}"
        print(line)

    print("\nUse one of these in .env:")
    print(f"  STOP_ID={matches[0]['stop_id']}")
    print(f"  STOP_NAME={matches[0]['stop_name']}")
    print("  ROUTE_IDS=<comma separated, e.g. N,Q,R,W>")


if __name__ == "__main__":
    main()
