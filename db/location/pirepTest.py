#!/usr/bin/env python3

"""Test pirep decoding.

Reads /OV strings from the file ``ov.txt`` and prints results of non-matches.
This is used to develop better matches for determining the location
of a PIREP.

Each line is ``ov.txt`` should be the contents of the ``/OV`` segment of a
PIREP. An actual ``ov.txt`` file is not supplied, but the file
``ov-compilation.txt`` can be copied to ``ov.txt`` and used.
"""

import sys, os, argparse, csv
from datetime import datetime
import dateutil.parser, textwrap
from argparse import RawTextHelpFormatter
from pymongo import MongoClient
from pymongo import errors
from bson.objectid import ObjectId

import db.location.locationdbConfig as cfg
import db.harvest.location as loc

# Get items from configuration
mongoUrl = cfg.MONGO_URL

def pirepTest():
    """Main routine for pirepTest

    This is one of the few programs that isn't expected to be
    run from the fisb-decode/bin directory. It is expected
    to be run from the fisb-decode/db/location directory
    and to have the file ``ov.txt`` in the same directory.
    """
    client = MongoClient(mongoUrl, tz_aware=True)
    db = client.fisb_location

    # msg to use. Since we don't read stations, use 'IND' if one is needed.
    msg = {'station': 'IND'}

    with open('ov.txt', 'r') as f:
        for line in f:
            line = line.strip()

            # Since we loop, remove any geometry
            if 'geometry' in msg:
                del msg['geometry']

            msg['ov'] = line

            # Find location and update message if successful.
            msgOut = loc.pirepLocation(db, msg)
            if 'geometry' in msgOut:
                coords = msgOut['geometry'][0]['coordinates']
                #print(line, '=>', coords)
            else:
                # No match
                print(line)
    
if __name__ == "__main__":
    # Call pirepTest
    pirepTest()
