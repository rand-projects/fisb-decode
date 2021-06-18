"""Code for handling location support.

Location is an optional module which will add location
information to certain message types. These include:

* ``METAR``
* ``TAF``
* ``WINDS_06_HR``
* ``WINDS_12_HR``
* ``WINDS_24_HR``
* ``PIREP``

The most challenging of these are PIREPs, because PIREPs are often
encoded by humans rather than machines. The humans don't understand
that to get a location on a map a machine has to interpret their misguided
attempts at providing a location. There is an official standard for how
to encode the ``/OV`` portion of a PIREP, but it is often not followed.
This seems particularly true for tower controllers.

For PIREPS, using a starting point of 15,820 or so unique ``/OV`` 
entries, the routines in this module will get a 95% match (in actual
use the match rate is much higher, since many of the decodeable PIREPs
are repeats).

Technically, bearings in PIREPS are magnetic. When the location database is
created, it uses the *World Magnetic Model* (WMM) software to calculate the
declination for each point. This information is used to convert to true
direction (WGS84) for placement on an image.
"""
import sys, os, json, time, glob, pprint
import subprocess, re
import dateutil.parser, csv, shutil, math
from datetime import datetime, timezone, timedelta
from geographiclib import geodesic
from pymongo import MongoClient
from pymongo import errors
from tzlocal import get_localzone

import db.harvest.harvestConfig as cfg
import db.harvest.harvestExceptions as ex

# Used to convert direction name to a compass direction
BEARING_DICT = {'NORTH': 0.0, \
    'SOUTH': 180.0, \
    'EAST': 90.0, \
    'WEST': 270.0, \
    'N': 0.0, \
    'S': 180.0, \
    'E': 90.0, \
    'W': 270.0, \
    'NE': 45.0, \
    'NW': 315.0, \
    'SE': 135.0, \
    'SW': 225.0, \
    'NORTHEAST': 45.0, \
    'NORTHWEST': 315.0, \
    'SOUTHEAST': 135.0, \
    'SOUTHWEST': 225.0, \
    'NNE': 22.5, \
    'ENE': 67.5, \
    'ESE': 112.5, \
    'SSE': 157.5, \
    'SSW': 202.5, \
    'WSW': 247.5, \
    'WNW': 292.5, \
    'NNW': 337.5}

# Matches LAT and LONG entries of the form: 'xxxxN xxxxxW'
LAT_LONG_RE = re.compile(r"^([3|4][0-9]{3})N ([0-9]{5})W$")

# Matches things like '10SSE OF IND'.
DIST_DIR_FM_IDENT_RE = re.compile(r"^([0-9]{1,2}) ?((NM|SM|M|MILE) )?(NORTH|SOUTH|EAST|WEST|N|S|E|W|NE|NW|SE|SW|NORTHEAST|NORTHWEST|SOUTHEAST|SOUTHWEST|NNE|ENE|ESE|SSE|SSW|WSW|WNW|NNW)( (OF )?([A-Z0-9]{3,5}))?$")

# Matches PIREP OV with 3-5 character idents, and optional radius and bearing.
# This is by far the most common case.
# Group 1: ident
# Group 3: bearing (or None)
# Group 4: distance (or None)
IDENT_BEARING_DISTANCE_RE = re.compile(r"^(?:(OV|OVER|OVR)?( |-))?([A-Z0-9]{3,5})? ?(([0-9]{3}) ?([0-9]{3}))*$")

# Same as above, but matches 2 digit miles instead or 3. Don't change to {2,3}.. that causes errors
IDENT_BEARING_DISTANCE1_RE = re.compile(r"^(?:(OV|OVER|OVR)?( |-))?([A-Z0-9]{3,5})? ?(([0-9]{3}) ?([0-9]{2}))*$")

# Dictionary for handling cached location
# queries. The key is the station location
# id and the value is the contents of the
# 'geojson' key (in the style of the rest
# of fisb-decode [i.e. overkill]).
#
# It is questionable if this cache should be 
# periodically flushed. Either by just keeping recent
# entries in it, or just flushing it periodically.
# For a single location it holds about 600-700
# entries (that are all used periodically). If this
# was used in flight, this number might increase.
txtWxLocDict = {}

def addTextWxLoc(db, msg):
    """Augment text weather object with location information.

    Adds a compatible ``geojson`` key and value for the given
    message.

    The first time a new weather ident is used, it will be looked
    up in the database (``fisb_location.WX``). Afterwards,
    the result is cached.

    Args:
        db (object): Database connection to ``fisb_location`` database.
        msg (dict): Message to be augmented. One of METAR, TAF, WINDS_xx_HR.

    Returns:
        dict: Message with ``geojson`` key added if we found a match,
            Else just returns the input argument.
    """
    id = msg['unique_name']

    # See if we have it cached already.
    if id in txtWxLocDict:
        msg['geojson'] = txtWxLocDict[id]
        return msg

    station = db.WX.find_one({'_id': id})
    if station is None:
        # No airport. Can't add location info. Just return.
        return msg
    
    geoField = {'type': 'FeatureCollection', \
                'features': [{'type': 'Feature', \
                              'geometry': { \
                                 'type': 'Point', \
                                 'coordinates': station['coordinates']}, \
                               'properties': {'name': id, 'id': id}}]}

    txtWxLocDict[id] = geoField
    msg['geojson'] = geoField
    return msg

def findPirepIdent(db, ident):
    """Attempt to find a set of coordinates for PIREP ident.

    If 5 characters, will try to find the ident in the ``DESIGNATED_POINTS``
    table. If 3 characters will try in ``NAVAIDS``. If 3 or 4 chars will
    try in ``AIRPORTS``.

    Args:
        db (object): Database connection to ``fisb_location`` database.
        ident (str): 3-5 character ident to lookup.

    Returns:
        tuple: Tuple:

        1. (list) List with latitude, longitude of ident.
        2. (float) Declination of point in degrees.

        ``(None, 0)`` if no point found.
    """
    ident = ident.strip()

    identLen = len(ident)

    # Only useful idents are 3 (navaid, airport), 4 (icao airport), or
    # 5 (reporting point) characters in length.
    # There are 2 character NAVAID idents (OM, MM), but have never seen
    # one used as an /OV point.
    if (identLen < 3) or (identLen > 5):
        return (None, 0)

    # If 5 chars, it could only be a reporting point.
    if identLen == 5:
        reportingPoint = db.DESIGNATED_POINTS.find_one({'_id': ident})
        if reportingPoint is None:
            return (None, 0)
        
        return (reportingPoint['coordinates'], reportingPoint['declination'])

    # NAVAIDS are 3 characters in length. Don't try if 4 chars
    if identLen == 3:
        navaid = db.NAVAIDS.find_one({'_id': ident})
        if navaid is not None:
            return (navaid['coordinates'], navaid['declination'])
    
    # Airports are 3 or 4 chars in length
    airport = db.AIRPORTS.find_one({'_id': ident})
    if airport is not None:
        return (airport['coordinates'], airport['declination'])
    
    return (None, 0)

def magneticToTrue(magBearing, declination):
    """Given magnetic bearing and declination return true bearing.

    Args:
        magBearing (float): Magnetic bearing in degrees
        declination (float): Declination in degrees (W is negative)

    Returns:
        float: True bearing in degrees
    """
    trueBearing = magBearing + declination

    # Correct so result is 0-359
    if trueBearing >= 360.0:
        trueBearing = trueBearing - 360.0
    elif trueBearing < 0.0:
        trueBearing = trueBearing + 360.0

    return trueBearing

def locationFromBearingDistance(originCoords, magBearing, declination, nm):
    """Find new location from old location at magnetic bearing and distance.

    Given an origin point (and its declination), a distance in nautical miles,
    and a magnetic bearing, find the 'true' (non-magnetic) WGS84
    coordinates of the resultant point.

    Args:
        originCoords (list): List [longitude, latitude] of origin point.
        magBearing (float): Magnetic bearing from origin point.
        declination (float): Magnetic declination at origin point.
        nm (float): Distance from origin in nautical miles.

    Returns:
        list: Resultant coordinate as list
          ``[longitude, latitude]``. Both are floats.
    """

    # PIREP bearings are magnetic. Convert to true.
    trueBearing = magneticToTrue(magBearing, declination)

    # 1 NM = 1/60 degree
    nmInMeters = nm * 1852.001

    # Calculate new location
    v = geodesic.Geodesic.WGS84.Direct(originCoords[1], \
        originCoords[0], trueBearing, nmInMeters)
    
    return [v['lon2'], v['lat2']]

def internalPirepLocation(db, ident, magneticBearing, nm):
    """Internal function to produce coordinates from ident and optional bearing.

    Attempt to find requested coordinates. Since ``/OV`` fields contain various
    forms of trash we reject silly magnetic bearings or distances.

    Return ``None`` if no valid result, else list of form ``[longitude, latitude]``.

    Args:
        db (object): Database connection to ``fisb_location`` database.
        ident (str): 3-5 character ident to lookup.
        magneticBearing (float): Magnetic bearing, or -1 if no bearing and distance
        nm (float): Nautical miles if magnetic bearing is used.

    Returns:
        list: List of form ``[longitude, latitude]`` or ``None`` if no match.
    """
    # Sanity check for ident.
    if not isValidIdent(ident):
        return None

    # Sanity check for magneticBearing and nm
    # If we are using a magnetic bearing it must be in range 0-360.
    # If the bearing matches, the distance must be less than 400nm (arbitrary).
    if magneticBearing != -1:
        if (magneticBearing < 0) or (magneticBearing > 360):
            return None
        if (nm < 0) or (nm >= 400):
            return None

    # Find coordinated for ident.       
    coords, declination = findPirepIdent(db, ident)

    # Nothing to do here. Ident not found.
    if coords is None:
        return None

    # If we have a bearing and distance, calculate it.
    if magneticBearing != -1:
        coords = locationFromBearingDistance(coords, \
            magneticBearing, declination, nm)

    # Truncate coords to 6 decimal places to match rest of fisb-decode.
    coords[0] = round(coords[0], 6)
    coords[1] = round(coords[1], 6)

    # Return new coordinates
    return coords

def isValidIdent(ident):
    """Return ``True`` if this could be a valid ident, else ``False``.

    Idents can contain letters and numbers, but they must have
    at least one alphabetic character.

    Args:
        ident (str): Candidate ident to check.

    Returns:
        bool: ``True`` if could be ident, else ``False``.
    """
    for c in ident:
        if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            return True

    return False

def matchIdentBearingDistance(db, ov, station):
    """Use reg-ex to try to match ``/OV`` field to an ident and bearing/distance.

    Perform a regular expression match to see if the ``/OV`` field matches the
    ident with optional bearing/distance information.

    Args:
        db (object): ``fisb_location`` database containing location information.
        msg (dict): Level2 PIREP message.
        ov (str): ``/OV`` field from PIREP message.
        station (str): PIREP station.

    Returns:
        list: Coordinates [latitude, longitude] that match.
        ``None`` if there is no match.
    """
    # Match for 3 digit distances.
    m = IDENT_BEARING_DISTANCE_RE.match(ov)
    if m is None:
        # Try with 2 digit distances.
        # So items like IND05020 as opposed to what should
        # have been sent IND050020.
        m = IDENT_BEARING_DISTANCE1_RE.match(ov)
        
    if m is not None:
        _, _, g3, _, g5, g6 = m.groups()

        if g3 is None:
            ident = station
        else:
            ident = g3

        if g5 is not None:
            magneticBearing = int(g5)
            nm = int(g6)
        else:
            # If no bearing and distance found, use -1 for the bearing
            # and zero for the distance.
            magneticBearing = -1
            nm = 0

        # do database match. Will either have results or None.
        coords = internalPirepLocation(db, ident, magneticBearing, nm)
        return coords
    
    return None

def makeGeojson(itemType, coords, msg):
    """Create geojson dictionary.

    Args:
        itemType (str): One of ``Point`` or ``LineString``.
        coords (list): List of two coordinates (longitude, latitude).
        id (str): Unique name (``_id``) field for Pirep
    Returns:
        dict: Dictionary which is a 'geojson' slot of the specified type
        and coordinates.
    """
    geojson = {'type': 'FeatureCollection', \
               'features': [{'type': 'Feature', \
                             'geometry': { \
                                 'type': itemType, \
                                 'coordinates': coords}}]}

    geojson['features'][0]['properties'] = { \
        'id': msg['unique_name'], \
        }
    return geojson

def checkLatLong(db, msg, ov, station):
    """Handle messages that contain latitude and longitude information directly.

    Some messages directly report the latitude and longitude of the
    reporting point. This function handles messages like:
    ``xxxxN xxxxxW``.

    Args:
        db (object): ``fisb_location`` database containing location information.
        msg (dict): Level2 PIREP message.
        ov (str): ``/OV`` field from PIREP message.
        station (str): PIREP station.

    Returns:
        tuple: Tuple:
        
        1. (bool) ``True`` if a
           location was found and the message argmented, or ``False``
           if no location was found.
        2. (dict) Augmented ``msg`` with location information if
           available, or just the original ``msg`` if no changes were made.
    """
    m = LAT_LONG_RE.match(ov)
    if m is not None:
        g1, g2 = m.groups()

        latitude = round(float(g1) / 100.0, 6)
        longitude = round(float(g2) / 100.0, 6) * -1.0

        msg['geojson'] = makeGeojson('Point', [longitude, latitude], msg)

        return (True, msg)
    
    return (False, msg)

def checkIdentBearingDistance(db, msg, ov, station):
    """Handles PIREPS that contain an ident and optional bearing and distance.

    Handles message with ``/OV`` values consisting of some combination
    of an identifier (station used if not present) and optional bearing
    and distance.
    This makes up the majority of all messages. 

    An typical example of an ``/OV`` segment from this message would be:
    ``IND270020``. This means 20NM from ``IND`` at a magnetic bearing
    of 270.

    Args:
        db (object): ``fisb_location`` database containing location information.
        msg (dict): Level2 PIREP message.
        ov (str): ``/OV`` field from PIREP message.
        station (str): PIREP station.

    Returns:
        tuple: Tuple:
        
        1. (bool) ``True`` if a location was found and the message
           argmented, or ``False`` if no location was found.
        2. (dict) Augmented ``msg`` with location information if
           available, or just the original ``msg`` if no changes
           made.
    """
    coords = matchIdentBearingDistance(db, ov, station)

    if coords == None:
        return (False, msg)

    msg['geojson'] = makeGeojson('Point', coords, msg)

    return (True, msg)

def checkRoute(db, msg, ov, station):
    """Create PIREP for route data consisting of multiple points.

    This is basically the same as :func:`checkIdentBearingDistance`
    except that there are multiple locations all separated
    with '``-``' (such as ``HUF-IND-TYQ170020``).

    Instead of creating a single point geometry, a route will consist
    of two or more sets of coordinates which form a ``POLYLINE``.

    Args:
        db (object): ``fisb_location`` database containing location information.
        msg (dict): Level2 PIREP message.
        ov (str): ``/OV`` field from PIREP message.
        station (str): PIREP station.

    Returns:
        tuple: Tuple:
        
        1. (bool) ``True`` if a location was found and the message
           argmented, or ``False`` if no location was found.
        2. (dict) Augmented ``msg`` with location information if
           available, or just the original ``msg`` if no changes
           made.
    """
    routePoints = ov.split('-')

    routeCoords = [matchIdentBearingDistance(db, x, station) for x in routePoints]

    if None in routeCoords:
        return (False, msg)

    msg['geojson'] = makeGeojson('LineString', routeCoords, msg)

    return (True, msg)

def checkDistanceDirectionFromIdent(db, msg, ov, station):
    """Try to match distance and direction from a location.

    Try to parse ``/OV`` fields like ``10 S BOS``. Here,
    the directions are compass directions.
    This is the second most common kind of ``/OV`` field.

    Looks for various text clues in the message that indicate
    the location of the message.

    Args:
        db (object): ``fisb_location`` database containing location information.
        msg (dict): Level2 PIREP message.
        ov (str): ``/OV`` field from PIREP message.
        station (str): PIREP station.

    Returns:
        tuple: Tuple:
        
        1. (bool) ``True`` if a location was found and the message
           argmented, or ``False`` if no location was found.
        2. (dict) Augmented ``msg`` with location information if
           available, or just the original ``msg`` if no changes
           made.
    """
    m = DIST_DIR_FM_IDENT_RE.match(ov)
    if m is not None:
        # g1 - distance
        # g3 - NM or SM
        # g4 - direction
        # g7 - ident
        g1, _, g3, g4, _, _, ident = m.groups()

        magneticBearing = BEARING_DICT[g4]
        nm = float(g1)

        # Convert SM to NM if needed
        if (g3 is not None) and (g3 == 'SM'):
            nm = nm * 0.86897624

        # No ident means use station
        if ident is None:
            ident = station

        coords = internalPirepLocation(db, ident, magneticBearing, nm)
        if coords is None:
            return (False, msg)

        msg['geojson'] = makeGeojson('Point', coords, msg)

        return (True, msg)
    
    return (False, msg)

def checkText(db, msg, ov, station):
    """Check PIREP for text based hints.

    Looks for various text clues in the message that indicate
    the location of the message. Most of these are messages that
    indicate that the origin of the PIREP is the station.

    Args:
        db (object): ``fisb_location`` database containing location information.
        msg (dict): Level2 PIREP message.
        ov (str): ``/OV`` field from PIREP message.
        station (str): PIREP station.

    Returns:
        tuple: Tuple:
        
        1. (bool) ``True`` if a location was found and the message
           argmented, or ``False`` if no location was found.
        2. (dict) Augmented ``msg`` with location information if
           available, or just the original ``msg`` if no changes
           made.
    """
    # Assume station for these
    if (ov.startswith('RUNWAY') or \
            ov.startswith('RWY') or \
            ov.startswith('FINAL') or \
            ov.startswith('ON FINAL') or \
            ov.startswith('SHORT FINAL') or \
            ov == 'DURD' or \
            ov == 'DURC'):
        coords = internalPirepLocation(db, station, -1, 0)

        if coords is None:
            return (False, msg)

        msg['geojson'] = makeGeojson('Point', coords, msg)

        return (True, msg)

    return (False, msg)

def saveUnmatchedPirep(contents):
    """Save any unmatched PIREPs to a file for future study (or amusement).

    If ``cfg.SAVE_UNMATCHED_PIREPS`` is ``True``, will append the
    PIREP to the file specified by ``cfg.SAVE_UNMATCHED_PIREPS_FILE``.

    Args:
        contents (str): Original text contents of a PIREP.
    """
    with open(cfg.SAVE_UNMATCHED_PIREPS_FILE, 'a') as f:
        f.write(contents)
        f.write('\n')

def pirepLocation(db, msg):
    """Augment message with ``geometry`` information if location
    can be decoded..

    Take a PIREP message and try to determine its location. If so
    the message is augmented with the appropriate ``geojson``
    key.

    If the location cannot be found, just returns the message.
    
    Args:
        db (object): Database connection to ``fisb_location`` database.
        msg (dict): Level2 message to augment

    Returns:
        dict: ``msg``, either augmented or not.
    """
    station = msg['station']
    ov = msg['ov']
    
    # Check for '-'. This indicates route.
    if '-' in ov:
        res, msg = checkRoute(db, msg, ov, station)
        if res:
            return msg
        
    # Most common case. Ident and optional bearing/distance
    res, msg = checkIdentBearingDistance(db, msg, ov, station)
    if res:
        return msg

    # Next most coomon case is miles and direction from point in
    # form like '10 E IND', '10E IND', '10E OF IND', etc.
    res, msg = checkDistanceDirectionFromIdent(db, msg, ov, station)
    if res:
        return msg

    # Check for latitude longitude entries
    res, msg = checkLatLong(db, msg, ov, station)
    if res:
        return msg
    
    # Check for various text items that usually indicate the 
    # report is at the station.
    res, msg = checkText(db, msg, ov, station)
    if res:
        return msg

    # Nothing worked, just return the message
    if cfg.SAVE_UNMATCHED_PIREPS:
        saveUnmatchedPirep(msg['contents'])

    return msg
