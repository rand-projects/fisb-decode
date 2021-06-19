#!/usr/bin/env python3

"""``createwxdb`` will place weather station location information
in the ``fisb_location.WX`` collection.

There are two required sources of information: NWS METAR station location
information obtained from the ``index.xml`` file, and wind station location
information from the ``winds.txt`` file (supplied).

The latest version of ``index.xml`` can be obtained from
`here <https://w1.weather.gov/xml/current_obs/index.xml>`_.

Wind station location information is not the easiest thing to find.
There is no readily available great list of wind stations. I supply
a ``winds.txt`` file consisting of NWS data from NWS directive
`10-812 <https://www.nws.noaa.gov/directives/sym/pd01008012curr.pdf>`_.

Most wind station locations are associated with a METAR source (i.e. adding
a 'K' in front results in a valid METAR station). In this case, I will use the
location data from the METAR source instead of the winds source (I have also
verified that in each case the locations are approximately the same). Some wind
locations are not associated with a METAR source from ``index.xml``. In those
cases the wind source is used. Some wind locations are located off-shore.
"""

import pprint, os, argparse

from xml.dom import minidom
from argparse import RawTextHelpFormatter                                                       
from pymongo import MongoClient                                                                 
from pymongo import errors                                                                      
from bson.objectid import ObjectId                                                              
                                                                                                
import db.location.createwxdbConfig as cfg

def createStationDict(indexXmlFile):
    """Parses ``index.xml`` to obtain station id and
    latitude, longitude information.

    Args:
        indexXmlFile (str): Path for ``index.xml``.

    Returns:
        dict: Dictionary with station name for key and
        list for value containing [lng, lat].
    """
    xmlFile = minidom.parse(indexXmlFile)

    stationDict = {}

    stations = xmlFile.getElementsByTagName('station')
    for station in stations:
        children = station.childNodes

        # Just in case a field is missing, make it easy to find
        # and not reuse value from previous loop.
        stationId = None
        latitude = None
        longitude = None

        for child in children:
            if child.nodeName == 'station_id':
                stationId = child.firstChild.nodeValue
            elif child.nodeName == 'latitude':
                latitude = float(child.firstChild.nodeValue)
            elif child.nodeName == 'longitude':
                longitude = float(child.firstChild.nodeValue)
        
        stationDict[stationId] = [longitude, latitude]

    return stationDict

def createWindDict(windFile):
    """Parses ``winds.txt`` to obtain station id and
    latitude, longitude information.

    Args:
        windFile (str): Path for ``winds.txt``.

    Returns:
        dict: Dictionary with station name for key and
        list for value containing [lng, lat].
    """
    windDict = {}

    with open(windFile, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or (len(line) == 0):
                continue
            
            lineParts = line.split(',')

            stationId = lineParts[0]
            latitude = lineParts[1]
            longitude = lineParts[2]

            windDict[stationId] = [longitude, latitude]

    return windDict

def createwxdb(index_xml_file, winds_file):
    """Fill ``fisb_location.WX`` with data from ``index.xml``
    and ``winds.txt``.

    Args:
        index_xml_file (str): Path for ``index.xml``.
        winds_file (str): Path for ``winds.txt``.
    """
    # Open database
    client = MongoClient(cfg.MONGO_URI, tz_aware=True)
    db = client.fisb_location

    # Delete all existing entries.
    db.WX.delete_many({})

    # Parse index.xml and winds.txt into dictionaries.
    stationDict = createStationDict(index_xml_file)
    windDict = createWindDict(winds_file)
    
    # Add all the wind stations to the station dictionary. If the
    # wind location has a 'K' entry, use the 'K' entries lat and long.
    # Otherwise, use the wind entries (because it's all you have).
    keys = list(windDict.keys())
    for k in keys:
        kName = 'K' + k
        if kName in stationDict:
            latLong = stationDict[kName]
        else:
            latLong = windDict[k]    

        stationDict[k] = latLong

    # Insert all entries into WX collection.
    stationKeys = list(stationDict.keys())    
    for station in stationKeys:
        db.WX.insert_one({'_id': station, 'coordinates': stationDict[station]})
    
if __name__ == "__main__":
    hlpText = \
"""Fill the fisb_location database with weather station
information.

Arguments are 'index.xml' from the NWS (see documentation
on how to obtain) and the supplied 'winds.txt' file.
"""
    parser = argparse.ArgumentParser(description= hlpText, \
        formatter_class=RawTextHelpFormatter)

    parser.add_argument('index_xml_file', help="index.xml from NWS")
    parser.add_argument('winds_file', help="winds.txt file")
    
    args = parser.parse_args()

    index_xml_file = args.index_xml_file
    winds_file = args.winds_file

    # Call createwxdb
    createwxdb(index_xml_file, winds_file)
