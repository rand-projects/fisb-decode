#!/usr/bin/env python3

"""Vectordump saves all vector data in the current database as a
``.csv`` file which can be input by QGIS as a 'Delimited Text Layer'.

Each type of data is stored in a file whose name is of the format:
``V-<type>-<PG|PT|LS>.csv`` where ``type`` is the type of data
such as ``G_AIRMET_00_HR``, followed by one of ``PG`` (polygon),
``PT`` (point), or ``LS`` (linestring).

Within each ``.cvs`` file each line represents a geometry in WKT form.
"""

import sys, os, json, time, argparse, traceback, glob
import dateutil.parser, curses, textwrap
from pymongo import MongoClient
from pymongo import errors

sys.path.insert(0, os.path.abspath('..'))

import db.harvest.vectors as vec
import db.vectordump.vectordumpConfig as cfg

# Get items to display from configuration
mongoUrl = cfg.MONGO_URL

# Possible file names
OUTPUT_FILES = ['V-AIRMET-PG.csv', 'V-G_AIRMET_00_HR-LS.csv', \
    'V-G_AIRMET_00_HR-PG.csv', 'V-G_AIRMET_03_HR-LS.csv', \
    'V-G_AIRMET_03_HR-PG.csv', 'V-G_AIRMET_06_HR-LS.csv', \
    'V-G_AIRMET_06_HR-PG.csv', 'V-METAR-PT.csv', 'V-TAF-PT.csv', \
    'V-PIREP-PT.csv', 'V-WINDS_06_HR-PT.csv', 'V-WINDS_12_HR-PT.csv', \
    'V-WINDS_24_HR-PT.csv', 'V-NOTAM-D-PT.csv', 'V-NOTAM-FDC-PT.csv', \
    'V-NOTAM-TFR-PT.csv', 'V-NOTAM-TFR-PG.csv', 'V-METAR-PT.csv']

def vectordump():
    """Dump all vector data to ``.csv`` files.
    """
    client = MongoClient(mongoUrl, tz_aware=True)
    db = client.fisb

    currentPath = '.'

    # Delete any existing .csv files so we don't get confused as
    # to what is new and what is old.
    for x in OUTPUT_FILES:
        csvPath = os.path.join(currentPath, x)
        if os.path.isfile(csvPath):
            os.remove(csvPath)

    vec.dumpVectors(currentPath, db)
    
if __name__ == "__main__":
    hlpText = \
"""Dump vector data from database in WKT csv format for QGis.
    
"""
    parser = argparse.ArgumentParser(description= hlpText)

    args = parser.parse_args()
        
    # Call vectordump
    vectordump()
