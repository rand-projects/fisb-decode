#!/usr/bin/env python3

"""Locationdb loads supplemental data into the fisb_location database.

This information is used primarily to assisting in providing
geographical locations for ``PIREPS`` and text based weather
(``METAR``, ``TAF``, ``WINDS``).

Locationdb takes one argument which is the directory to find
the following files:

* ``Airports.csv``
* ``Designated_Points.csv``
* ``NAVAID_System.csv``

These files are obtained from https://adds-faa.opendata.arcgis.com/

Locationdb assumes there is a ``fisb_location`` database
(there is a script in ``fisb-decode/db/scripts``  directory to create one). It will
remove all entries from the ``AIRPORTS``, ``NAVAIDS``, and
``DESIGNATED_POINTS`` collections. It then opens up the .csv
files and stores the ID and latitude, longitude information 
from each file. It doesn't store any other data from the .csv
file. 

This program will also add the declination for each point. PIREP bearings
are magnetic and this allows conversion to true north. To do this
we use the World Magnetic Model program wmm_file.
To download the WMM, see https://ngdc.noaa.gov/geomag/WMM/DoDWMM.shtml.

For declinations: Once the data is uploaded to the database, an ordered set of data is
used to create the ``source.wmm`` file which is then fed to the 
``wmm_file`` program to produce the ``result.wmm`` file (by default,
these are stored in ``/tmp``). The ``result`` file is then read in and 
matched to the database with the declination extracts and stored in
the database tables.

One problem you will run into is that ``wmm_file`` needs the file
``WMM.COF`` in the same directory where the command is run. For ``fisb-decode``
this means you need to move the ``WMM.COF`` into the ``fisb-decode/bin`` directory.
"""

import sys, os, argparse, csv
from datetime import datetime
import dateutil.parser, textwrap
from argparse import RawTextHelpFormatter
from pymongo import MongoClient
from pymongo import errors
from bson.objectid import ObjectId

import db.location.locationdbConfig as cfg

# Directory where .csv files are located. Will
# be replaced with any directory given as argument.
BASE_DIRECTORY = '.'

# Get items from configuration
mongoUrl = cfg.MONGO_URL

def calculateDeclinations(db, table):
    """Calculate magnetic delinations for all points using the World Magnetic Model.

    Takes a database table and uses wmm_file to find declinations for 
    all points.

    Will create the ``source.wmm`` file, run the ``wmm_file`` program
    producing ``result.wmm`` then use those results to update the 
    database with declination values.

    See config file for various directory options. 

    **CAUTION**: ``wmm_file`` is very fussy about having ``WMM.COF`` in the same
    directory that the program is run from-- so you might have to move it.
    It will tell you if it cannot find it.

    Note: The ``DESIGNATED_POINTS``, but not the other tables contain
    declination. If we have gotten a declination from a table, we will
    keep that one and not use the calculated one.

    Args:
        db (object): Handle to fisb_location database.
        table (str): Name of the table this command is being applied to.
            Used on AIRPORT, NAVAIDS, and DESIGNATED_POINT tables.
    """
    # Path for source and result files.
    sourcePath = os.path.join(cfg.DECLINATION_DIR,'source.wmm')
    resultPath = os.path.join(cfg.DECLINATION_DIR,'result.wmm')

    # WMM needs a year (current model good 2020-2024).
    # This basically calculates a the mid-point of each month
    # It DOES NOT have to be accurate.
    dtUtcNow = datetime.utcnow()
    yearFrac = round(dtUtcNow.year + (dtUtcNow.month / 12.0) + (1.0 / 24.0), 2)

    # create source.wmm
    with open(sourcePath, 'w') as f:
        cur = db[table].find({}).sort('_id', 1)
        for row in cur:

            # Skip rows that already have declination
            if 'declination' in row:
                continue

            latitude = row['coordinates'][1]
            longitude = row['coordinates'][0]

            # 'E' means use WGS84 ellipsoid surface
            # 'F5000' means 5000 feet above surface (arbitrary)
            f.write('{} E F5000 {} {}\n'.format(yearFrac, latitude, longitude))

    # run wmm_file (wmm_file f <source> <result>)
    os.system('{} f {} {}'.format(os.path.join(cfg.WMM_FILE_HOME,'wmm_file'), \
        sourcePath, resultPath))
    
    # process result.wmm
    with open(resultPath, 'r') as f:
        # skip header line
        f.readline()
        
        cur = db[table].find({}).sort('_id', 1)
        for row in cur:

            # Skip rows that already have declination
            if 'declination' in row:
                continue

            line = f.readline().strip()
            valArray = line.split()

            # Declination is stored in string like '18d 27m'
            dDeg = float(valArray[5][:-1])
            isMinus = False
            if dDeg < 0:
                isMinus = True
                dDeg = -dDeg

            # Add deg and min as positive numbers, then make negative
            # if required.
            dMin = float(valArray[6][:-1])
            declination = round(dDeg + (dMin / 60.0), 2)
            if isMinus:
                declination = -declination
            
            # Update table
            db[table].update_one({ '_id': row['_id']}, \
                {'$set': {'declination': declination}},
                upsert=True)

    # Remove files
    os.remove(sourcePath)
    os.remove(resultPath)

def processAirports(db, path):
    """Fill AIRPORTS table with values.

    Read ``Airports.csv`` and fill AIRPORTS table with
    values.

    Args:
        db (object): Handle to fisb_location database.
        path (str): Path to ``Airports.csv``.
    """
    print('airports...')

    # Remove all entries
    db.AIRPORTS.delete_many({})

    # Read and process entries.
    with open(path, newline='') as csvfile:
        csvReader = csv.reader(csvfile, delimiter=',')
        next(csvReader) # skip header
        for row in csvReader:
            coordinates = [ round(float(row[0]), 6), round(float(row[1]), 6) ]
            ident = row[4].strip()
            isoIdent = row[9].strip()

            db.AIRPORTS.replace_one( \
            { '_id': ident}, \
            { 'coordinates': coordinates}, \
            upsert=True)

            # Some entries have 4 char ISO code. Use if present
            if len(isoIdent) != 0:
                db.AIRPORTS.replace_one( \
                { '_id': isoIdent}, \
                { 'coordinates': coordinates}, \
                upsert=True)

    # Calculate declinations for all points using WMM.
    calculateDeclinations(db, 'AIRPORTS')

def processNavaids(db, path):
    """Fill NAVAIDS table with values

    Read ``NAVAID_System.csv`` and fill NAVAIDS table with
    values.

    Navaids often (but not always) have a declination
    specified in the table. When it does, we will use the
    one provided. Else, we will use the calculated one.

    Args:
        db (object): Handle to fisb_location database.
        path (str): Path to ``NAVAIDS_System.csv``
    """
    print('navaids...')

    # Remove all entries
    db.NAVAIDS.delete_many({})

    # Process entries
    with open(path, newline='') as csvfile:
        csvReader = csv.reader(csvfile, delimiter=',')
        next(csvReader) # skip header
        for row in csvReader:
            coordinates = [ round(float(row[0]), 6), round(float(row[1]), 6) ]
            ident = row[13].strip()

            db.NAVAIDS.replace_one( \
            { '_id': ident}, \
            { 'coordinates': coordinates}, \
            upsert=True)

    # Calculate declinations for all points using WMM.
    calculateDeclinations(db, 'NAVAIDS')

def convertToDecimalDegrees(degStr):
    """Convert Designated_Points.csv DMS values to decimal degrees.

    Most ``Designated_Points.csv`` entries have decimal degrees,
    but not all. Some are in the form ``31-53-41.240N`` and
    ``086-15-32.060W``. Convert these to decimal degrees.

    Args:
        degStr (str): DMS form as described above. Either lat or long.

    Returns:
        float: Argument converted to decimal degrees.
    """
    dms = degStr.split('-')
    
    # dms[2] has form dd.dddX where x is a direction
    deg = float(dms[0])
    min = float(dms[1])
    sec = float(dms[2][:-1])

    # South and West directions need to get multipied by -1
    if dms[2][-1] in 'SW':
        multiplier = -1.0
    else:
        multiplier = 1.0

    decDeg = (deg + (min / 60.0) + (sec / 3600.0)) * multiplier
    return decDeg

def processReportingPoints(db, path):
    """Fill ``DESIGNATED_POINTS`` table with values.

    Read ``Designated_Points.csv`` and fill ``DESIGNATED_POINTS`` table with
    values.

    NOTE: Not all ``DESIGNATED_POINTS`` idents are 5 characters, but we usually
    only search this table when we have a 5-character identifier.

    Args:
        db (object): Handle to fisb_location database.
        path (str): Path to ``Designated_Points.csv``.
    """
    print('reporting points...')

    # Remove all entries
    db.DESIGNATED_POINTS.delete_many({})

    # Process entries.
    with open(path, newline='') as csvfile:
        csvReader = csv.reader(csvfile, delimiter=',')
        next(csvReader) # skip header
        for row in csvReader:
            # Sigh. For some reason, not all entries have a decimal coordinate.
            # Some have a dd-mm-ss coordinate. If so, convert it.
            if len(row[0].strip()) == 0:  # 'X' column is empty
                longitude = convertToDecimalDegrees(row[12])
            else:
                longitude = float(row[0])

            if len(row[1].strip()) == 0: # 'Y' column is empty
                latitude = convertToDecimalDegrees(row[11])
            else:
                latitude = float(row[1])

            coordinates = [ round(longitude, 6), round(latitude, 6) ]
            ident = row[10].strip()

            # Make dictionary now in case we add declination to it.
            coordDict = { 'coordinates': coordinates}

            # Most, but not all, entries have declination
            declinationStr = row[14].strip()
            if len(declinationStr) != 0:
                declination = round(float(declinationStr), 6)
                coordDict['declination'] = declination

            db.DESIGNATED_POINTS.replace_one( \
            { '_id': ident}, \
            coordDict, \
            upsert=True)

    # Calculate declinations for all points using WMM.
    calculateDeclinations(db, 'DESIGNATED_POINTS')

def locationDb():
    """Main routine for locationdbs.

    Process and fill database with the 3 .csv files contents. Will
    also add magnetic declination information.
    """
    client = MongoClient(mongoUrl, tz_aware=True)
    db = client.fisb_location

    # Basic sanity check, make sure files exist
    airportsPath = os.path.join(BASE_DIRECTORY, 'Airports.csv')
    navaidsPath = os.path.join(BASE_DIRECTORY, 'NAVAID_System.csv')
    reportingPointsPath = os.path.join(BASE_DIRECTORY, 'Designated_Points.csv')    

    hasAnyErrors = False

    if not os.path.isfile(airportsPath):
        hasAnyErrors = True
        print("Can't find", airportsPath)
    if not os.path.isfile(navaidsPath):
        hasAnyErrors = True
        print("Can't find", navaidsPath)
    if not os.path.isfile(reportingPointsPath):
        hasAnyErrors = True
        print("Can't find", reportingPointsPath)

    if hasAnyErrors:
        sys.exit(1)

    # Process all tables.
    processAirports(db, airportsPath)
    processNavaids(db, navaidsPath)
    processReportingPoints(db, reportingPointsPath)
    
if __name__ == "__main__":
    hlpText = \
"""Fill the fisb_location database with ID, location and 
magnetic declination information.

Argument is the directory where the following files live:
    * Airports.csv
    * Designated_Points.csv
    * NAVAID_System.csv

Also, you will need the 'wmm_file' program installed
somewhere and the 'WMM.COF' file in the directory you are 
running this from.
"""
    parser = argparse.ArgumentParser(description= hlpText, \
        formatter_class=RawTextHelpFormatter)

    parser.add_argument('directory', help="Base directory where .csv files live")
    
    args = parser.parse_args()

    BASE_DIRECTORY = args.directory

    # Call locationDb
    locationDb()
