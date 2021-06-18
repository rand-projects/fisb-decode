#!/usr/bin/env python3

import pprint, os, argparse

from xml.dom import minidom
from argparse import RawTextHelpFormatter                                                       
from pymongo import MongoClient                                                                 
from pymongo import errors                                                                      
from bson.objectid import ObjectId                                                              
                                                                                                
import db.location.createwxdbConfig as cfg

def createStationDict(indexXmlFile):
    xmlFile = minidom.parse('index.xml')

    stationDict = {}

    stations = xmlFile.getElementsByTagName('station')
    for station in stations:
        children = station.childNodes

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
    windDict = {}

    with open(windFile, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or (len(line) == 0):
                continue
            
            lineParts = line.split(',')

            stationId = lineParts[0]
            if '-' in lineParts[2]:
                latitude = float('%.5f'%(float(lineParts[2]) - (float(lineParts[3]) / 60.0)))
            else:
                latitude = float('%.5f'%(float(lineParts[2]) + (float(lineParts[3]) / 60.0)))

            if '-' in lineParts[4]:
                longitude = float('%.5f'%(float(lineParts[4]) - (float(lineParts[5]) / 60.0)))
            else:
                longitude = float('%.5f'%(float(lineParts[4]) + (float(lineParts[5]) / 60.0)))

            windDict[stationId] = [longitude, latitude]

    return windDict

def createwxdb(index_xml_file, winds_file):
    client = MongoClient(cfg.MONGO_URI, tz_aware=True)
    db = client.fisb_location

    db.WX.delete_many({})

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

    stationKeys = list(stationDict.keys())    
    for station in stationKeys:
        db.WX.insert_one({'_id': station, 'coordinates': stationDict[station]})
    
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

    parser.add_argument('index_xml_file', help="Base directory where .csv files live")
    parser.add_argument('winds_file', help="Base directory where .csv files live")
    
    args = parser.parse_args()

    index_xml_file = args.index_xml_file
    winds_file = args.winds_file

# Call createWxLocationDb
createwxdb(index_xml_file, winds_file)
