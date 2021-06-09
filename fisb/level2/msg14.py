"""Decode and create messages from product id 14 (G-AIRMET)

The final message that comes out of here will be one of the following:

* G_AIRMET_00_HR
* G_AIRMET_03_HR
* G_AIRMET_06_HR
"""

import sys, os, json, time, re

import fisb.level2.level2Config as cfg
import fisb.level2.utilities as util
import fisb.level2.level2Exceptions as ex

def msg14(records, recordCount, productId, \
                rYear, rMonth, rDay, rHour, rMin, \
                month, day, hour, minute, station, rcvdTime):
    """Dispatch product_id 14 (G_AIRMET) messages for appropriate processing.

    Yet another Nancy Drew puzzle to solve. There are three
    G-AIRMET products we get: 00, 03, and 06 hours. This information
    is not sent and we need to infer the forecast type based-on
    the start and stop iso times. If the start-iso and end-iso times
    match, that is the 06 hour forecast. Otherwise we use the stop-iso
    time to determine the forecast. Stop-iso times of 00:00, 06:00,
    12:00, and 18:00 implies a 00 hour forecast. Stop-iso times of
    03:00, 09:00, 15:00, and 21:00 implies a 03 hour forecast.
    See table A-52 in DO-358B.

    Args:
        records (dict): Contents of ``frame['contents']['records']``
        recordCount (int): Number of records this entry has.
        productId (int): Product id.
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        rHour (int): Message received hour.
        rMin (int): Message received minute.
        month (int): APDU month.
        day (int): APDU day.
        hour (int): APDU hour.
        minute (int): APDU minute.
        station (str): Station from which message originated.
        rcvdTime (str): Message received in ISO format.

    Returns:
        dict: Dictionary with completed message.
    """
    newMsg = None

    # Use records[0] as base record for decoding things
    # We do have multiple records with this type, but only the
    # vertex_list actually changes.
    records0 = records[0]

    # Two digit year
    reportYear = records0['report_year']

    # Full year, instead of two digits
    reportFullYear = util.doubleDigitYear(rYear, reportYear, False)
    
    # Create the report id
    reportId = str(reportYear) + '-' + str(records0['report_number'])

    # Handle special case of a cancelled product.
    if records0['object_status'] == 13:
        newMsg = {}
        newMsg['type'] = 'CANCEL_G_AIRMET'
        newMsg['unique_name'] = reportId
        newMsg['expiration_time'] = util.addMinutesToIso8601(rcvdTime, \
            cfg.CANCEL_EXPIRATION_TIME)

        return newMsg

    overlayGeometryOptions = records0['overlay_geometry_options']

    # Sanity checks. Make sure nothing unexpected tries to sneak by.
    if (records0['object_status'] != 15) or \
       (records0['date_time_format'] != 1) or \
       (overlayGeometryOptions not in [3, 4, 11, 12]):
        raise ex.G_AirmetMessageException("Something wrong in G_AIRMET parameters")

    issuedTimeIso = util.componentsToIso8601(reportFullYear, \
                                          month, day, hour, minute)

    # Get starting and stopping times.
    startIso = util.componentsToIso8601Referenced(issuedTimeIso, \
                                        records0['start_month'], \
                                        records0['start_day'], \
                                        records0['start_hour'], \
                                        records0['start_minute'])

    stopIso = util.componentsToIso8601Referenced(issuedTimeIso, \
                                       records0['stop_month'], \
                                       records0['stop_day'], \
                                       records0['stop_hour'], \
                                       records0['stop_minute'])

    fcHour = -1 # forecastHour
    
    if (startIso == stopIso):
        fcHour = 6

        # For 6 hour, the start ISO is correct, but the stop
        # ISO needs 3 hours added to it.
        stopIso = util.addHoursToIso8601(startIso, 3)
        
    elif 'T00:00' in stopIso:
        fcHour = 0
    elif 'T03:00' in stopIso:
        fcHour = 3
    elif 'T06:00' in stopIso:
        fcHour = 0
    elif 'T09:00' in stopIso:
        fcHour = 3
    elif 'T12:00' in stopIso:
        fcHour = 0
    elif 'T15:00' in stopIso:
        fcHour = 3
    elif 'T18:00' in stopIso:
        fcHour = 0
    elif 'T21:00' in stopIso:
        fcHour = 3

    if fcHour == -1:
        raise ex.G_AirmetMessageException('Could not find forecast type: {}'.format(stopIso))

    newMsg = {}
    
    newMsg['type'] = 'G_AIRMET'
    newMsg['unique_name'] = reportId
    newMsg['subtype'] = fcHour
    newMsg['station'] = station
    newMsg['issued_time'] = issuedTimeIso
    newMsg['for_use_from_time'] = startIso
    newMsg['for_use_to_time'] = stopIso
    
    # Make a list of all geometries (since might be more than one record)
    newMsg['geometry'] = util.processGeometry(records, issuedTimeIso, productId)
                                               
    newMsg['expiration_time'] = util.twgoExpirationTime(newMsg, rcvdTime)
    return newMsg
