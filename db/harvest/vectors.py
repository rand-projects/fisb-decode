"""Code for transforming vector data to WKT (Well Known Text) format.
Will also convert fis-b decode CIRCLE data to a polygon.
"""
import sys, os, json, time, argparse, traceback, glob, pprint
import dateutil.parser, csv, shutil, math
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from pymongo import errors
from tzlocal import get_localzone
from geographiclib import geodesic

import db.harvest.harvestConfig as cfg
import db.harvest.harvestExceptions as ex

DB_VECTOR_TYPES = ['NOTAM', 'NOTAM_TFR', 'AIRMET', \
    'SIGMET', 'WST', 'CWA', \
    'G_AIRMET', 'PIREP', 'METAR', 'TAF', 'WINDS_06_HR', \
        'WINDS_12_HR', 'WINDS_24_HR']

# Functions that define premininary keys for each vector type.
# Used to name files and provide name for vector in vectordump
# .csv files.
def genericFcn(table, doc):
    """Create and return partial key for generic messages.

    Args:
        table (str): Database table.
        doc (dict): Message from database.

    Returns:
        str: With partial key for ``vectorDict``.
    """
    return table + '~' + doc['_id']

def sigWxFcn(table, doc):    
    """Create and return partial key for SIGMET, AIRMET, WST, and CWA messages.

    Args:
        table (str): Database table.
        doc (dict): Message from database.

    Returns:
        str: With partial key for ``vectorDict``.
    """
    return doc['type'] + '~' + doc['_id'] + '/' + str(doc['geojson']['features'][0]['properties']['altitudes'][2]) \
        + ':' + str(doc['geojson']['features'][0]['properties']['altitudes'][0])

def gAirmetFcn(table, doc):
    """Create and return partial key for G-AIRMET messages.

    Args:
        table (str): Database table.
        doc (dict): Message from database.

    Returns:
        str: With partial key for ``vectorDict``.
    """
    return doc['type'] + '~' + doc['_id'] + '/' + doc['geojson']['features'][0]['properties']['element'] \
        + '-' + str(doc['geojson']['features'][0]['properties']['altitudes'][2]) \
        + ':' + str(doc['geojson']['features'][0]['properties']['altitudes'][0])

def notamFcn(table, doc):
    """Create and return partial key for NOTAM messages.

    Args:
        table (str): Database table.
        doc (dict): Message from database.

    Returns:
        str: With partial key for ``vectorDict``.
    """
    return 'NOTAM-' + doc['subtype'] + '~' + doc['_id']

def notamTfrFcn(table, doc):
    """Create and return partial key for NOTAM-TFR messages.

    Args:
        table (str): Database table.
        doc (dict): Message from database.

    Returns:
        str: With partial key for ``vectorDict``.
    """
    return 'NOTAM-TFR~' + doc['_id']

def pirepFcn(table, doc):
    """Create and return partial key for PIREP messages.

    Args:
        table (str): Database table.
        doc (dict): Message from database.

    Returns:
        str: With partial key for ``vectorDict``.
    """
    return 'PIREP~' + doc['report_type'] + '-' + doc['station'] + '-' + doc['tm']

DB_VECTOR_FUNCTIONS = [notamFcn, notamTfrFcn, sigWxFcn, \
    sigWxFcn, sigWxFcn, sigWxFcn, \
    gAirmetFcn, pirepFcn, genericFcn, genericFcn, \
    genericFcn, genericFcn, genericFcn]

# Global variables set once at program startup
# --------------------------------------------

# Database connection
dbConn = None

# Dictionary that maps a table to a function that
# creates a key for the dictionary of all vector
# entries.
VECTOR_TABLE_FCN_DICT = dict(zip(DB_VECTOR_TYPES, \
    DB_VECTOR_FUNCTIONS))

# --------------------------------------------

def circleToPolygon(xCenter, yCenter, nm, numPoints = 32):
    """Convert circle to 32 coordinate polygon. Assumes ``WGS84`` coordinate system.

    Args:
        xCenter (float): longitude
        yCenter (float): latitude
        nm (float): Distance from center in nautical miles.
        numPoints (int): Number of points to use to create the circle.
          Default is 32.

    Returns:
        list: List of ``numPoints`` coordinates estimating the given circle.
    """
    coords = []
    
    # 1 NM = 1/60 degree
    nmInMeters = nm * 1852.001

    for i in range(0, numPoints):
        deg = 360.0/ numPoints * i
        v = geodesic.Geodesic.WGS84.Direct(yCenter, xCenter, deg, nmInMeters)

        coords.append([float('%.6f'%(v['lon2'])), float('%.6f'%(v['lat2']))])

    return coords

def createPointWkt(coords):
    """Create WKT POINT string.

    Args:
        coords (list): Two item list representing single point coordinate.

    Returns:
        str: WKT POINT string.
    """
    return 'POINT(' + str(coords[0]) + ' ' + str(coords[1]) + ')'

def createPolygonPolyline(type, coords):
    """Create WKT POLYGON or LINESTRING string.

    Args:
        type (str): ``POLYGON`` to create polygon, else will create ``LINESTRING``.
        coords (list): Two item list representing single point coordinate.

    Returns:
        str: WKT POLYGON or LINESTRING string.
    """
    if type == 'POLYGON':
        beginParens = '(('
        endParens = '))'
    else:
        beginParens = '('
        endParens = ')'

    geoStr = type + beginParens

    for x in coords:
        geoStr = geoStr + str(x[0]) + ' ' + str(x[1]) + ','

    geoStr = geoStr[0:-1] # get rid of last ','
    geoStr = geoStr + endParens

    return geoStr

def processGeometry(dumpPath, doc, vectorDict, keyStart):
    """Convert ``geojson`` data to appropriate WKT object and
    stores it in ``vectorDict``.

    Args:
        dumpPath (str): Path for storing to a file.
        doc (dict): Database entry holding data.
        vectorDict (dict): Dictionary for holding results.
        keyStart (str): Partial key for ``vectorDict``. 
    """
    geoList = doc['geojson']['features']
    
    if len(geoList) > 1:
        hasMultiple = True
    else:
        hasMultiple = False

    itemCounter = 1

    # Need a copy since the copy may have /1, /2, /3 appended.
    keyStartCopy = keyStart
    for x in geoList:
        if hasMultiple:
            keyStartCopy = keyStart + '/' + str(itemCounter)
            itemCounter += 1

        geoType = x['geometry']['type']
        if geoType == 'Point':
            vectorDict[keyStartCopy + '~PT'] = createPointWkt(x['geometry']['coordinates'])
        elif geoType == 'Polygon':
            vectorDict[keyStartCopy + '~PG'] = createPolygonPolyline('POLYGON', x['geometry']['coordinates'])
        elif geoType == 'LineString':
            vectorDict[keyStartCopy + '~LS'] = createPolygonPolyline('LINESTRING', x['geometry']['coordinates'])

def writeVectorDict(dumpPath, vectorDict):
    """Write ``vectorDict`` to a number of files depending upon which
    data it contains.

    This routine finds similar data and outputs it to a ``.csv`` file. Note
    that only data of the same type can be grouped together: All entries must be
    points, linestrings, or polygons in any single file.

    Args:
        dumpPath (str): Path for storing files.
        vectorDict (dict): Dictionary containing WKT objects.
    """
    # Loop through the vectorDict. Each time find the first entry
    # and use that to define what file type we process. Process
    # that type, deleting each row as we go. Repeat until the
    # vectorDict dictionary has no entries.
    while True:
        keys = list(vectorDict.keys())

        if len(keys) == 0:
            # We are done
            break

        # Get first entry and process all of them
        targetList = keys[0].split('~')

        targetPath = os.path.join(dumpPath, 'V-' + targetList[0] + '-' + \
            targetList[2] + '.csv')

        f = open(targetPath, 'w')

        for k in keys:
            itemList = k.split('~')
            if (itemList[0] == targetList[0]) and \
                (itemList[2] == targetList[2]):
                f.write('{}\t{}\n'.format(itemList[1], vectorDict[k]))

                # Delete item
                del vectorDict[k]

        f.close()
            
def dumpVectors(dumpPath, dbConn):
    """Dump all current vectors to the specified ``dumpPath``.

    Args:
        dumpPath (str): Path for storing files.
        dbConn (object): Database connection.
    """
    vectorDict = {}

    for t in DB_VECTOR_TYPES:
        cursor = dbConn.MSG.find({'type': t})
        for doc in cursor:
            if 'geojson' in doc:
                beginKey = VECTOR_TABLE_FCN_DICT[t]
                processGeometry(dumpPath, doc, vectorDict, beginKey(t, doc))

    # Write the vector dictionary
    writeVectorDict(dumpPath, vectorDict)
