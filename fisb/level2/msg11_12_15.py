"""Decode and create messages from product id 11, 12, 15.

This module creates the following messages:

* AIRMET
* SIGMET
* WST
* CWA
"""

import sys, os, json, time, re

import fisb.level2.level2Config as cfg
import fisb.level2.utilities as util
import fisb.level2.level2Exceptions as ex

# RegEx for a TWGO
TWGO_RE = re.compile(r"([^ ]+) ([^ ]+) ([0-3]\d[0-2]\d[0-5]\d)")

# Special case for SIGMET xxxxxx with no station
TWGO1_RE = re.compile(r"([^ ]+) +([0-3]\d[0-2]\d[0-5]\d)")

#: Sometimes messages get stuck in the system. For over a year, these messages
#: have been stuck and continue to exist. Hopefully, one day these will
#: be gone, but until then we have to manually ignore them. This includes putting
#: special code for the ``CRL`` message (:mod:`fisb.level2.msgCrl`) so that they
#: are ignored there too.
BAD_MESSAGES = [\
    "WST KMKC 062057 CONVECTIVE SIGMET 99C\nFL TN AL MS LA AR TX OK AND FL AL MS LA CSTL WTRS\nFROM 20ENE MEM-20NNW VUZ-110S CEW-50SSW LSU-70NW GGG-10SSW\nFSM-20ENE MEM\nAREA TS MOV LTL. TOPS TO FL410.\n",\
    "WST KMKC 170253 CONVECTIVE SIGMET 3E\nNC AND NC SC CSTL WTRS\nFROM 40S ECG-120SE ECG-200SE ILM-120SSE ILM-30WSW ILM-40S ECG\nAREA EMBD TS MOV FROM 17015KT. TOPS TO FL430.\n"\
    ]

def msg11_12_15(frame, productId, \
                rYear, rMonth, rDay, rHour, rMin, \
                month, day, hour, minute, station, rcvdTime):
    """Dispatch product_ids 11, 12, 15 messages for appropriate processing.

    Args:
        frame (dict): Contents of the entire frame.
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

    Raises:
        IllegalTwgoMessageException: If empty text message in TWGO, or
            overlay geometry not 3 or 4.
        TwgoHeaderParseException: If required regular expression didn't match.

    """
    newMsg = None

    # Will always have a contents_text
    contentsText = frame['contents_text']
    records0 = contentsText['records'][0]

    # Two digit year
    reportYear = records0['report_year']

    # Create the report id
    reportId = str(reportYear) + '-' + str(records0['report_number'])

    # Handle special case of a cancelled product 15 (CWA).
    # These are the only text messages we should get.
    if (productId == 15) and \
       (contentsText['record_format'] == 2) and \
       (records0['report_status'] == 0):
        newMsg = {}
        newMsg['type'] = 'CANCEL_CWA'
        newMsg['unique_name'] = reportId
        newMsg['expiration_time'] = util.addMinutesToIso8601(rcvdTime, \
            cfg.CANCEL_EXPIRATION_TIME)

        return newMsg

    text = records0['text']

    # Note: Rarely, messages get stuck in the system for months. This is an
    # attempt to bypass those messages.
    if text in BAD_MESSAGES:
        return None

    # Sanity checks. Make sure nothing unexpected tries to sneak by.
    if len(text) == 0:
        raise ex.IllegalTwgoMessageException("Empty text message in TWGO type 11,12, or 15")

    # FAA text is full of trailing whitespace. Get rid of it.
    text = util.cleanFAAText(text)
    
    # Get the report type and issue time.
    m = TWGO_RE.match(text)

    if m is None:
        # Try to see if station missing
        m = TWGO1_RE.match(text)
        if m is None:
            raise ex.TwgoHeaderParseException('TWGO Regex did not match: "{}"'.format(text))
        else:
            twgo_type = m.group(1)
            twgo_time = m.group(2)
    else:
        twgo_type = m.group(1)
        twgo_time = m.group(3)

    hasGraphics = False
    if 'contents_graphics' in frame:
         hasGraphics = True
        
    issueTimeIso = util.dayHourMinToIso8601(rYear, rMonth, rDay, twgo_time)
    
    if hasGraphics:
        gRecords = frame['contents_graphics']['records']
        gRecords0 = gRecords[0]

        overlayGeometryOptions = gRecords0['overlay_geometry_options']
        if overlayGeometryOptions not in [3,4]:
            raise ex.IllegalTwgoMessageException("Overlay geo not 3 or 4 in TWGO type 11,12, or 15")

        # Get starting and stopping times.
        # Some test data doesn't have start and stop times
        startIso = None
        stopIso = None

        if gRecords0['record_applicability_options'] == 3:
            startIso = util.componentsToIso8601Referenced(issueTimeIso, \
                                        gRecords0['start_month'], \
                                        gRecords0['start_day'], \
                                        gRecords0['start_hour'], \
                                        gRecords0['start_minute'])

            stopIso = util.componentsToIso8601Referenced(issueTimeIso, \
                                       gRecords0['stop_month'], \
                                       gRecords0['stop_day'], \
                                       gRecords0['stop_hour'], \
                                       gRecords0['stop_minute'])

    newMsg = {}

    reportType = twgo_type
    newMsg['type'] = reportType
    newMsg['unique_name'] = reportId
    newMsg['station'] = station
    newMsg['issued_time'] = issueTimeIso
    if hasGraphics:
        if startIso is not None:
            newMsg['for_use_from_time'] = startIso
        if stopIso is not None:
            newMsg['for_use_to_time'] = stopIso

    newMsg['contents'] = text

    if hasGraphics:
        newMsg['geometry'] = util.processGeometry(gRecords, issueTimeIso, productId)

    newMsg['expiration_time'] = util.twgoExpirationTime(newMsg, rcvdTime)
    return newMsg
