#!/usr/bin/env python3
"""
MTA GTFS-RT API Client
Fetches and parses real-time train data from MTA
Uses route + direction mapping to provide destinations
"""

import logging
import time
from collections import defaultdict

import requests
from google.transit import gtfs_realtime_pb2

from config import Config

logger = logging.getLogger(__name__)


class Train:
    """Represents a train with arrival information"""
    
    def __init__(self, route_id, destination, arrival_time, direction):
        self.route_id = route_id
        self.destination = destination
        self.arrival_time = arrival_time  # Unix timestamp
        self.direction = direction
    
    def get_minutes_to_arrival(self):
        """Get minutes until train arrival"""
        current_time = time.time()
        seconds_to_arrival = self.arrival_time - current_time
        minutes = max(0, int(seconds_to_arrival / 60))
        return minutes
    
    def __repr__(self):
        return f"Train(route={self.route_id}, dest={self.destination}, arrives_in={self.get_minutes_to_arrival()}m)"


class MTAClient:
    """Client for MTA GTFS-RT API"""
    
    # Map each route to the GTFS-RT feed that carries it
    ROUTE_TO_FEED = {
        '1': 'gtfs', '2': 'gtfs', '3': 'gtfs',
        'A': 'gtfs-ace', 'C': 'gtfs-ace', 'E': 'gtfs-ace',
        'N': 'gtfs-nqrw', 'Q': 'gtfs-nqrw', 'R': 'gtfs-nqrw', 'W': 'gtfs-nqrw',
        'B': 'gtfs-bdfm', 'D': 'gtfs-bdfm', 'F': 'gtfs-bdfm', 'M': 'gtfs-bdfm',
        'L': 'gtfs-l',
        'G': 'gtfs-g',
        'J': 'gtfs-jz', 'Z': 'gtfs-jz',
        'S': 'gtfs-si',  # Staten Island Railway
    }

    # Terminal station per route and direction, kept short enough for a 64px display.
    # "Northbound"/"southbound" follow the GTFS stop suffix (N/S), which is railroad
    # direction rather than true compass direction.
    DESTINATIONS = {
        '1': {'northbound': 'Van Cortlandt', 'southbound': 'South Ferry'},
        '2': {'northbound': 'Wakefield',     'southbound': 'Flatbush Av'},
        '3': {'northbound': 'Harlem 148',    'southbound': 'New Lots Av'},
        '4': {'northbound': 'Woodlawn',      'southbound': 'Crown Hts'},
        '5': {'northbound': 'Eastchester',   'southbound': 'Flatbush Av'},
        '6': {'northbound': 'Pelham Bay',    'southbound': 'Bklyn Bridge'},
        '7': {'northbound': 'Flushing',      'southbound': 'Hudson Yds'},
        'A': {'northbound': 'Inwood 207',    'southbound': 'Far Rockaway'},
        'C': {'northbound': '168 St',        'southbound': 'Euclid Av'},
        'E': {'northbound': 'Jamaica Ctr',   'southbound': 'World Trade'},
        'B': {'northbound': 'Bedford Pk',    'southbound': 'Brighton Bch'},
        'D': {'northbound': 'Norwood 205',   'southbound': 'Coney Island'},
        'F': {'northbound': 'Jamaica 179',   'southbound': 'Coney Island'},
        'M': {'northbound': 'Forest Hills',  'southbound': 'Middle Vlg'},
        'N': {'northbound': 'Astoria',       'southbound': 'Coney Island'},
        'Q': {'northbound': '96 St',         'southbound': 'Coney Island'},
        'R': {'northbound': 'Forest Hills',  'southbound': 'Bay Ridge'},
        'W': {'northbound': 'Astoria',       'southbound': 'Whitehall St'},
        'J': {'northbound': 'Jamaica Ctr',   'southbound': 'Broad St'},
        'Z': {'northbound': 'Jamaica Ctr',   'southbound': 'Broad St'},
        'L': {'northbound': '8 Av',          'southbound': 'Canarsie'},
        'G': {'northbound': 'Court Sq',      'southbound': 'Church Av'},
    }

    def __init__(self, api_key=None):
        """Initialize MTA client

        Args:
            api_key: Optional MTA API key. The GTFS-RT feeds are currently open
                and work without one; the key is sent if provided.
        """
        self.api_key = api_key
        self.base_url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds%2fnyct"
        self.session = requests.Session()
        self.session.verify = Config.VERIFY_TLS
        self.session.headers.update({"User-Agent": Config.USER_AGENT})

        if not Config.VERIFY_TLS:
            logger.warning(
                "TLS verification is DISABLED (VERIFY_TLS=false). Traffic can be "
                "intercepted. See docs/TROUBLESHOOTING.md - this is usually a wrong "
                "system clock on the Pi, not a reason to turn off verification."
            )

        if self.api_key:
            self.session.headers.update({"x-api-key": self.api_key})


    def get_feed(self, feed_path):
        """Fetch GTFS-RT feed from MTA
        
        Args:
            feed_path: Feed path (e.g., 'gtfs-nqrw' for NQRW lines)
            
        Returns:
            Parsed FeedMessage or None on error
        """
        try:
            url = f"{self.base_url}/{feed_path}"
            logger.debug(f"Fetching from {url}")
            
            response = self.session.get(url, timeout=Config.API_TIMEOUT)
            response.raise_for_status()
            
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            logger.debug(f"Successfully fetched feed with {len(feed.entity)} entities")
            return feed
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching feed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing feed: {e}")
            return None
    
    def parse_feed(self, feed, stop_id, route_ids=None):
        """Parse GTFS-RT feed to extract train arrivals
        
        Uses route + direction mapping for destinations
        
        Args:
            feed: FeedMessage from MTA
            stop_id: Base stop ID to filter (e.g., 'R16' for Times Sq 42 St)
            route_ids: List of route IDs to include, or None for all routes
                      
        Returns:
            Dict with 'northbound' and 'southbound' lists of Train objects
        """
        trains = {"northbound": [], "southbound": []}
        
        try:
            logger.debug(f"Parsing feed for stop_id={stop_id}, route_ids={route_ids}")
            
            # First pass: collect candidate stops
            all_stops = defaultdict(int)
            for entity in feed.entity:
                if not entity.HasField("trip_update"):
                    continue
                
                for stop_time in entity.trip_update.stop_time_update:
                    stop = stop_time.stop_id
                    if stop_id.upper() in stop.upper() or stop.startswith(stop_id):
                        all_stops[stop] += 1
            
            if all_stops:
                logger.debug(f"Found {len(all_stops)} candidate stops matching '{stop_id}':")
                for stop in sorted(all_stops.keys()):
                    logger.debug(f"  {stop}: {all_stops[stop]} trips")
            
            # Second pass: extract trains
            processed = 0
            matched = 0
            
            for entity in feed.entity:
                if not entity.HasField("trip_update"):
                    continue
                
                trip_update = entity.trip_update
                trip = trip_update.trip
                route_id = trip.route_id
                
                processed += 1
                
                # MULTIPLE ROUTES SUPPORT
                if route_ids is not None:
                    if route_id not in route_ids:
                        continue
                
                # Check each stop in the trip
                for stop_time in trip_update.stop_time_update:
                    stop_id_check = stop_time.stop_id
                    
                    # Check if this stop matches our target
                    matches = False
                    
                    if stop_id.upper() in stop_id_check.upper():
                        matches = True
                    elif stop_id_check.startswith(stop_id):
                        matches = True
                    elif stop_id in stop_id_check:
                        matches = True
                    
                    if matches:
                        # Determine direction from stop_id suffix
                        stop_upper = stop_id_check.upper()
                        direction = None
                        
                        if stop_upper.endswith('N') or stop_upper.endswith('1'):
                            direction = "northbound"
                        elif stop_upper.endswith('S') or stop_upper.endswith('2'):
                            direction = "southbound"
                        elif stop_upper.endswith('0') or stop_upper.endswith('3'):
                            # Use direction_id as fallback
                            direction_id = trip.direction_id if hasattr(trip, 'direction_id') else 0
                            direction = "northbound" if direction_id == 0 else "southbound"
                        
                        # Get destination from mapping (or Unknown as fallback)
                        destination = "Unknown"
                        if route_id in self.DESTINATIONS:
                            destination = self.DESTINATIONS[route_id].get(direction, "Unknown")
                        
                        # Get arrival time
                        arrival_time = None
                        if stop_time.HasField("arrival"):
                            arrival_time = stop_time.arrival.time
                        elif stop_time.HasField("departure"):
                            arrival_time = stop_time.departure.time
                        
                        if arrival_time and direction:
                            train = Train(
                                route_id=route_id,
                                destination=destination,
                                arrival_time=arrival_time,
                                direction=direction
                            )
                            trains[direction].append(train)
                            matched += 1
                            logger.debug(f"✓ Added {direction} train: {route_id} to '{destination}' (stop: {stop_id_check})")
                        
                        break  # Found this trip's stop, move to next trip
            
            logger.info(f"Processed {processed} trips, matched {matched} to stop '{stop_id}'")
            
            # Sort by arrival time and limit to top 5
            for direction in ["northbound", "southbound"]:
                trains[direction].sort(key=lambda t: t.arrival_time)
                trains[direction] = trains[direction][:5]
            
            logger.info(f"Parsed trains - Northbound: {len(trains['northbound'])}, Southbound: {len(trains['southbound'])}")
            
            if len(trains['northbound']) == 0 and len(trains['southbound']) == 0:
                logger.warning("⚠ No trains found!")
                logger.warning(f"  Stop ID: '{stop_id}'")
                logger.warning(f"  Routes: {route_ids}")
                logger.warning(f"  Processed {processed} total trips")
            
            return trains
            
        except Exception as e:
            logger.error(f"Error parsing feed: {e}", exc_info=True)
            return trains
    
    def get_trains(self, stop_id, route_ids):
        """Fetch all needed feeds for the given routes and return merged train data.

        Args:
            stop_id: Base stop ID (e.g. 'R16')
            route_ids: List of route IDs (e.g. ['N', 'Q', 'R', 'W'])

        Returns:
            Dict with 'northbound' and 'southbound' lists of Train objects,
            sorted by arrival time.
        """
        # Figure out which feeds we need
        feeds_needed = {}
        for route in route_ids:
            feed_path = self.ROUTE_TO_FEED.get(route)
            if feed_path:
                feeds_needed.setdefault(feed_path, []).append(route)
            else:
                logger.warning(f"No feed mapping for route '{route}'")

        logger.info(f"Fetching {len(feeds_needed)} feed(s) for routes {route_ids}: {list(feeds_needed.keys())}")

        merged = {"northbound": [], "southbound": []}

        for feed_path, routes_in_feed in feeds_needed.items():
            feed = self.get_feed(feed_path)
            if feed is None:
                logger.warning(f"Failed to fetch feed '{feed_path}' (routes {routes_in_feed})")
                continue
            result = self.parse_feed(feed, stop_id, route_ids=routes_in_feed)
            merged["northbound"].extend(result["northbound"])
            merged["southbound"].extend(result["southbound"])

        # Sort and limit
        for direction in ("northbound", "southbound"):
            merged[direction].sort(key=lambda t: t.arrival_time)
            merged[direction] = merged[direction][:5]

        logger.info(
            f"Merged trains - Northbound: {len(merged['northbound'])}, "
            f"Southbound: {len(merged['southbound'])}"
        )
        return merged

    @staticmethod
    def get_display_name(route_id):
        """Get display name for route"""
        return route_id
