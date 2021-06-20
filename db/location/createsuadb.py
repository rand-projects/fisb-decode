#!/usr/bin/env python3

"""Create SUA collection.

Each entry in the SUA file is a geojson entry. A couple of entries
have multiple coordinates in a single coordinate set
(R-7201A and POWDER RIVER 1D LOW MOA)
and many have multiple sets with the same name but different
coordinates. Since the SUA NOTAM-D only tells us the name, we
have to assume all parts are active.

All entries are normalized to have a single set of coordinates per
Feature. The id is the name of the item as we will get it from the
NOTAM-D (no dashes). Each name can have multiple items in a FeatureCollection.

We also greatly reduce the number of properties to those which we
might actually use. Additionally, the coordinates come with 15(!)
decimal places, making each coordinate point good to 1.11 Angstroms.
This is silly of course, and we reduce the number of decimal places 
to 6 (which is 0.11 meters, still overkill),
"""

import sys, os, argparse, json, pprint
from argparse import RawTextHelpFormatter
from pymongo import MongoClient
from pymongo import errors
from bson.objectid import ObjectId

import db.location.createsuadbConfig as cfg

# Get items from configuration
mongoUri = cfg.MONGO_URI

def addToCollection(db, id, feature):
    """Add a new item to the collection, or append item to existing collection.

    Will add ``feature`` to the collection if it doesn't exist. If
    it does, will append it to the existing item. I.e.: add the
    feature to the ``FeatureCollection`` ``features`` list.

    Args:
        db (object): Handle to database.
        id (str): Name of object to add. Any dashes in the name should be 
            removed because the NOTAM-D SUA will remove them.
        feature (dict): Dictionary containing the SUA item to add.
    """

    # Some (many) items have more than a single entry. In that case we append
    # the new entry to the old.
    obj = db.SUA.find_one({'_id': id})
    if obj is not None:
        # Add this feature set and replace.
        obj['features'].append(feature)

        db.SUA.replace_one({'_id': id}, obj, upsert=True)
        print('Adding to:', id)
    else:
        # Add a totally new item.
        db.SUA.insert_one({'_id': id, 'type': 'FeatureCollection', 'features': [feature]})

def processSua(db, filename):
    """Add all entries from the SUA geojason file to the ``SUA`` collection.

        Args:
            db (object): Handle to database.
            filename (str): Should be ``U.S._Special_Use_Airspace.geojson`` possibly
                with a path in front.
    """
    
    # Remove all entries
    db.SUA.delete_many({})
    
    with open(filename, 'r') as fileIn:
        line = fileIn.read()
        suaInDict = json.loads(line)

        # Get list containing each feature.
        features = suaInDict['features']
        
        for feature in features:
            oldProperties = feature['properties']

            # Remove any dash from the name (NOTAMs leave out the dash).
            id = oldProperties['NAME'].replace('-', '')

            # Create new smaller set of properties.
            newProperties = {}
            if 'NAME' in oldProperties:
                newProperties['name'] = oldProperties['NAME']
            if 'TYPE_CODE' in oldProperties:
                newProperties['type'] = oldProperties['TYPE_CODE']
            if 'TIMESOFUSE' in oldProperties:
                newProperties['times_of_use'] = oldProperties['TIMESOFUSE']
            if ('REMARKS' in oldProperties) and (oldProperties['REMARKS'] != None):
                newProperties['remarks'] = oldProperties['REMARKS']

            feature['properties'] = newProperties

            # Clean up coordinates. Remove Z value and trim
            # floats to 6 decimal points.
            #
            # A couple of entries R-7201A and POWDER RIVER 1D LOW MOA
            # have more than one entry in the coordinates. For each
            # item with more than one coordinateset , we will make multiple 
            # single coordinate entries. The first will be its own item
            # and the rest will be appended to 'features' in 
            # addToCollection().
            coordinates = feature['geometry']['coordinates']

            for i in coordinates:
                inner = []
                for j in i:
                    inner.append([round(j[0], 6), round(j[1], 6)])

                # Make entry with only one coordinate set.
                feature['geometry']['coordinates'] = inner
                addToCollection(db, id, feature)

def createsuadb(filename):
    """Main routine for createsuadb.

    Args:
        filename (str): Should be ``U.S._Special_Use_Airspace.geojson`` possibly
                with a path in front.        
    """

    # Connect to database.
    client = MongoClient(mongoUri, tz_aware=True)
    db = client.fisb_location

    # Basic sanity check, make sure file exist
    if not os.path.isfile(filename):
        print("Can't find", filename)
        sys.exit(1)

    # Read and process the SUA entries.
    processSua(db, filename)
    
if __name__ == "__main__":
    hlpText = \
"""Fill the fisb_location database with SUA information.

Argument is the file name to use, usually' U.S._Special_Use_Airspace.geojson'
"""
    parser = argparse.ArgumentParser(description= hlpText, \
        formatter_class=RawTextHelpFormatter)

    parser.add_argument('filename', help="Path to U.S._Special_Use_Airspace.geojson.")
    
    args = parser.parse_args()

    # Call createsuadb
    createsuadb(args.filename)
