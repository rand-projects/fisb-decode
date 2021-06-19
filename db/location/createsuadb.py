#!/usr/bin/env python3

"""Create SUA collection

Note: There are 2 geometries which have 2 parts. These are:
R-7201A and POWDER RIVER 1D LOW MOA
"""

import sys, os, argparse, json, pprint
from argparse import RawTextHelpFormatter
from pymongo import MongoClient
from pymongo import errors
from bson.objectid import ObjectId

import db.location.createsuadbConfig as cfg

# Get items from configuration
mongoUri = cfg.MONGO_URI

def processSua(db, filename):

    # Remove all entries
    db.SUA.delete_many({})
    
    with open(filename, 'r') as fileIn:
        line = fileIn.read()
        line = line.strip()
        suaInDict = json.loads(line)

        features = suaInDict['features']
        
        for feature in features:
            id = feature['properties']['NAME']

            # Remove any dash from the name (NOTAMs leave out the dash).
            id = id.replace('-', '')

            # Clean up coordinates. Remove Z value and trim
            # floats to 6 decimal points.
            coordinates = feature['geometry']['coordinates']

            newCoordinates = []

            for i in coordinates:
                inner = []
                for j in i:
                    inner.append([round(j[0], 6), round(j[1], 6)])

                newCoordinates.append(inner)

            feature['geometry']['coordinates'] = newCoordinates

            suaOutDict = {'_id': id, 'type': 'FeatureCollection', 'features': [feature]}

            # Some (many) items have more than a single entry. In that case we append
            # the new entry to the old.
            obj = db.SUA.find_one({'_id': id})
            if obj is not None:
                #print("************** original object ***************")
                #pprint.pprint(obj)
                #print("************** new feature ***************")
                #pprint.pprint(feature)

                # Add this feature set and replace.
                obj['features'].append(feature)

                db.SUA.replace_one({'_id': id}, obj, upsert=True)
                print('Adding to:', id)
            else:
                db.SUA.insert_one(suaOutDict)
                #print("************** insert object ***************")
                #pprint.pprint(suaOutDict)

def createsuadb(filename):
    """Main routine for createsuadb.

    """
    client = MongoClient(mongoUri, tz_aware=True)
    db = client.fisb_location

    # Basic sanity check, make sure file exist
    if not os.path.isfile(filename):
        print("Can't find", filename)
        sys.exit(1)

    # Process all tables.
    processSua(db, filename)
    
if __name__ == "__main__":
    hlpText = \
"""Fill the fisb_location database with SUA information.

Argument is the directory where the following file live:
    * U.S._Special_Use_Airspace.geojson
"""
    parser = argparse.ArgumentParser(description= hlpText, \
        formatter_class=RawTextHelpFormatter)

    parser.add_argument('filename', help="Path to U.S._Special_Use_Airspace.geojson lives.")
    
    args = parser.parse_args()

    # Call createsuadb
    createsuadb(args.filename)
