"""Decode and create messages from product id 8, 16, 17 (NOTAM) frames.

The following messages are created from here:

* NOTAM_TFR
* NOTAM
* FIS_B_UNAVAILABLE

The NOTAM type will have a subtype of 'D', 'FDC', 'TMOA', or 'TRA'.
"""

import sys, os, json, time, re, pprint

import fisb.level2.level2Config as cfg
import fisb.level2.utilities as util
import fisb.level2.level2Exceptions as ex

# RegEx for NOTAM time string (group(1) -> first date, group(2) -> second date)
NOTAM_TIMES_RE = re.compile(r"(\d\d[01]\d[0-3]\d[0-2]\d[0-5]\d)-(\d\d[01]\d[0-3]\d[0-2]\d[0-5]\d|PERM)")

# RegEx for a NOTAM-TFR to get the notam number
NOTAM_TFR_RE = re.compile(r"^NOTAM-TFR ([0-9]/[0-9]{4}) ")

# RegEx for a NOTAM-D or NOTAM-FDC for components
NOTAM_RE = re.compile(r"NOTAM-(D|FDC|TMOA|TRA) ([^ ]+) ([^ ]+) !([^ ]+) ([^ ]+) ([^ ]+) ([^ ]+)")

# RegEx for a NOTAM-D or NOTAM-FDC for the NOTAM contents (starting with !)
NOTAM_CONTENTS_RE = re.compile(r"NOTAM-(D|FDC|TMOA|TRA) ([^ ]+) ([^ ]+) (.+)", re.S)

# RegEx for basic SUA NOTAM-D parsing
#NOTAM_SUA_RE = re.compile(r".*AIRSPACE (.+) ACT (.+) \d{10}-\d{10}")
NOTAM_SUA_RE = re.compile(r".*AIRSPACE (LGT OUT/NIGHT VISION GOGGLE TRAINING )?(.+) ACT (.+) \d{10}-\d{10}")

# RegEx for parsing SUA NOTAM-D altitude string
NOTAM_SUA_ALT_RE = re.compile(r"((FL\d+)|SFC|(\d+FT( AGL)?))(-| UP TO BUT NOT INCLUDING )((FL\d+)|(\d+FT( AGL)?))")

# RegEx for FIS-B unavailable products (group(1) -> 6 digit date,
# group(2) -> list of centers, group(3) -> message text)
FISB_RE = re.compile(r"FIS-B ([0-3]\d[0-2]\d[0-5]\d)Z ([^ ]+) (.+)")

# Parses the specific FIS-B product that is unavailable.
FISB_PROD_RE = re.compile(r"^(.+) PRODUCT")

def msg8_16_17(contentsText, contentsGraphics, productId, \
             rYear, rMonth, rDay, \
             month, day, hour, minute, station, rcvdTime):
    """Dispatch NOTAM product_id 8, 16, and 17 messages for appropriate processing.

    Be aware that 'FIS-B Unavailable' and 'NOTAM-TFR' are products produced by the
    FIS-B provider, not the FAA. NOTAM-TFRs have a slightly different format from
    actual FAA TFR notams.

    Args:
        contentsText (dict): ``contents`` dictionary of text messages
        contentsGraphics (dict): ``contents`` dictionary
            of graphic messages. May be ``None``.
        productId (int): Product id. Will be one of 8, 16, or 17.
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        month (int): APDU month.
        day (int): APDU day.
        hour (int): APDU hour.
        minute (int): APDU minute.
        station (str): Station that originated the message.
        rcvdTime (str): Received ISO time (used only by FIS-B Unavailable and NOTAM-TFR)

    Returns:
        dict: Dictionary with completed message.

    Raises:
        TooManyRecordsException: For NOTAM messages that have more than 1 record.
    """
    newMsg = None
    
    # Should never see a record count other than 1 in a NOTAM text section
    if contentsText['record_count'] != 1:
        raise ex.TooManyRecordsException('NOTAM has more than 1 record')

    records0 = contentsText['records'][0]

    # Create the report id
    #
    # Notam Report Number meaning ('report_number')
    #  TFR, FDC       0001-9999
    #  FISB-UNAVAIL  10000-11999
    #  D             12001-12999
    #  TRA, TMOA     13001-13999 SUAE (FAA Service Area East)
    #                14001-14999 SUAC (FAA Service Area Central)
    #                15001-15999 SUAW (FAA Service Area West)
    #
    # See:
    # https://www.faa.gov/about/office_org/headquarters_offices/ato/service_units/mission_support/sc/
    # for which states are in which FAA Service Area.
    #
    # The usual case for all products other than TMOA and TRA is to use the 
    # report year and the report number (and append any location). For TMOA and TRA we use the APDU month
    # such that the report will match in the CRL
    #
    # An important concept is that any NOTAM that is part of a CRL
    # (NOTAM-TFR, NOTAM-TMOA, and NOTAM-TRA) must have an report id that
    # is ONLY the information found in the CRL (like year/month and
    # report number). However, that approach will get you into trouble
    # with NOTAM-Ds and NOTAM-FDCs where the report year and id are
    # reused all over the place. NOTAM-Ds and NOTAM-FDCs have a location
    # that will solve that problem. NOTAM cancellations will also put
    # a location for NOTAM-Ds and NOTAM-FDCs. NOTAM-TFRs and FIS-B
    # unavailable will have no location, or an empty location.
    #
    # In reviewing NOTAM-TFRs, these are 'reconstructed' by the FIS-B provider,
    # and I have never seen anything other than an empty location, making them
    # safe for CRLs (even though the FAA version often has a center location
    # associated with it).
    #
    # The result of all this is that if we get a location for type 8 NOTAMs
    # that are present and not empty, we will add it as part of the report id.
    # We need to do all this before we check for cancelled NOTAMs.

    if productId in [16, 17]:
        reportId = str(month) + '-' + str(records0['report_number'])
    else:
        reportId = str(records0['report_year']) + '-' + str(records0['report_number'])

        # Append location if present. We can't put a location on a NOTAM
        # TFR, but they don't come with one, so that is OK. FIS-B
        # UNAVAILABLE messages don't have one either, but it doesn't
        # make a difference. Adding the location makes NOTAM-Ds and NOTAM-FDCs
        # not collide.
        if 'location' in contentsText:
            location = contentsText['location'].strip()
            if len(location) > 0:
                reportId = reportId + '-' + location

    # If this is a cancellation, create and send it.
    if records0['report_status'] == 0:
        newMsg = {}
        newMsg['type'] = 'CANCEL_NOTAM'
        newMsg['unique_name'] = reportId
        newMsg['expiration_time'] = util.addMinutesToIso8601(rcvdTime, \
            cfg.CANCEL_EXPIRATION_TIME)

        return newMsg

    text = records0['text']

    # To save bandwidth NOTAM-TFRs don't send the text every transmission,
    # but alternate each transmission with sending an empty message with 
    # empty text, just the active status. So if the text is empty, send out a dummy
    # NOTAM-TFR with the 'renew-only' slot set to some value. The value of the
    # slot doesn't matter, just the fact that it exists. We also send 
    # it with a default expiration time of cfg.TWGO_DEFAULT_EXPIRATION_TIME.
    if len(text) == 0:
        newMsg = {}
        newMsg['type'] = 'NOTAM'
        newMsg['subtype'] = 'TFR'
        newMsg['unique_name'] = reportId
        newMsg['station'] = station
        newMsg['renew-only'] = '1'
        newMsg['expiration_time'] = util.addMinutesToIso8601(rcvdTime, \
            cfg.TWGO_DEFAULT_EXPIRATION_TIME)

        return newMsg
    
    # FAA text is full of trailing whitespace. Get rid of it.
    text = util.cleanFAAText(text)

    # There are 3 basic products we need to deal with:
    #  1. FIS-B product unavailable messages.
    #  2. NOTAM-TFRs, which aren't in regular NOTAM format.
    #  3. NOTAM-D, -FDC, -TMOA, -TRA in regular NOTAM format.

    # 1. FIS-B product unavailable messages are an outlier.
    if text.startswith('FIS-B'):
        return fisbProductUnavailable(rYear, rMonth, rDay, reportId, text, rcvdTime)

    # 2. NOTAM-TFRs aren't actually real notams. They come from a
    # different source and don't follow NOTAM-D and NOTAM-FDC specs.
    # In most cases it's just a large glob of (INCMPL) text.
    if text.startswith('NOTAM-TFR'):
        return tfrNotam(rYear, rMonth, rDay, reportId, text, \
            contentsGraphics, productId, station, \
            rcvdTime)
    
    # 3. If here, we have a real notam (NOTAM-D, NOTAM-FDC)
    return notam(rYear, rMonth, rDay, contentsText['location'], \
            reportId, text, contentsGraphics, productId, station, \
            rcvdTime)

def fisbProductUnavailable(rYear, rMonth, rDay, reportId, text, rcvdTime):
    """Decode and return a FIS-B product unavailable message.

    Args:
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        reportId (str): Combination of FAA year '-' and FAA report number.
        text (str): Full FIS-B product unavailable text.
        rcvdTime (str): Message received ISO time.

    Returns:
        dict: Dictionary with completed message.

    Raises:
        RegexDidNotMatchException: If we got unexpected text.
    """
    # Make sure it isn't an old format used only for test messages
    if text.startswith('FIS-B SERVICE OUTAGE'):
        text = 'FIS-B ' + text[21:]
    m = FISB_RE.match(text)
    if m is None:
        raise ex.RegexDidNotMatchException("fisbRE did not match: '{}'".format(text))

    issuedTime = util.dayHourMinToIso8601(rYear, rMonth, rDay, m.group(1))
    centers = m.group(2).split(',')
    contents = m.group(3)

    # Try to parse the product that is unavailable
    m = FISB_PROD_RE.match(contents)
    if m is None:
        raise ex.RegexDidNotMatchException("fisbRE did not match: '{}'".format(text))

    product = m.group(1)

    # Make up an expiration time. Standard states these should expire 20
    # minutes past the time of last reception. These are not stored in level3.
    expireAt = util.addMinutesToIso8601(rcvdTime, cfg.FISB_EXPIRATION_MINUTES)

    newMsg = {}
    newMsg['type'] = 'FIS_B_UNAVAILABLE'
    newMsg['unique_name'] = reportId
    newMsg['issued_time'] = issuedTime
    newMsg['contents'] = contents
    newMsg['product'] = product
    newMsg['centers'] = centers
    newMsg['expiration_time'] = expireAt

    return newMsg

def createGeometryList(contentsGraphics, referenceIso, productId):
    """Create a geometry list from the current ``contents_graphics`` dictionary.

    Args:
        contentsGraphics (dict): Contents portion of graphic message.
        referenceIso (str): This is an iso time (usually ``start_of_activity_time``) which
            is used as a reference to provide parts of dates that are not provided.
        productId (int): Product ID.

    Returns:
        list: Geometry list for message inclusion.
    """
    geometryList = util.processGeometry(contentsGraphics['records'], referenceIso, productId)

    return geometryList

def tfrNotam(rYear, rMonth, rDay, reportId, text, contentsGraphics, \
        productId, station, rcvdTime):
    """Decode and a return a NOTAM_TFR message.

    These are usually big blobs of text that are
    labeled as ``(INCMPL)``. Trying to find an issue time is
    not meaningful. According to the standard, the issue time
    they send may actually be one of three things. So we ignore
    it since we can't be sure what it actually is.

    The best times we can get
    are the 'start of activity' and 'end validity' times, if they
    are present. If not, we just expire after a configurable
    number of days.

    Args:
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        reportId (str): Combination of FAA year (1 or 2 digits) '-' and FAA report number.
        text (str): Full NOTAM text
        contentsGraphics (dict): ``content_graphics`` dictionary, if any.
        productId (int): Product ID.
        station (string): Station where message originated
        rcvdTime (str): Message received time in ISO format.

    Returns:
        dict: Dictionary with completed message.

    Raises:
        RegexDidNotMatchException: If NOTAM-TFR could not match template.
    """
    newMsg = {}

    # Parse off the NOTAM number (used for display)
    nTfr = NOTAM_TFR_RE.match(text)

    # Make sure we got what the connect decoding
    if nTfr is None:
        raise ex.RegexDidNotMatchException("NOTAM-TFR could not match: '{}'".format(text))

    newMsg['type'] = 'NOTAM'
    newMsg['subtype'] = 'TFR'
    newMsg['unique_name'] = reportId
    newMsg['contents'] = text
    newMsg['station'] = station
    newMsg['number'] = nTfr.group(1)
    newMsg = insertNotamDates(rYear, rMonth, rDay, text, newMsg)

    # Don't always have a start of activity time (use received time as ISO ref)
    soat = rcvdTime
    if 'start_of_activity_time' in newMsg:
        soat = newMsg['start_of_activity_time']

    # see if we have geometry
    if contentsGraphics is not None:
        newMsg['geometry'] = createGeometryList(contentsGraphics, \
            soat, productId)

    newMsg['expiration_time'] = util.twgoExpirationTime(newMsg, rcvdTime)
    return newMsg
            
def parseAlt(altString, subOneFromAlt):
    """Convert NOTAM-D SUA altitude onto integer and units.

    Note: For SUA it gets confusing because it is not always clear
    when 'FT' means AGL or MSL. If it is not obvious (like 'SFC'),
    we just return 'FT'. Flight levels are always considered MSL.
    A few values are '<xxx>FT AGL', in which case we use AGL.

    Args:
        altString (str): String from RegEx with altitude. Should
            be one of 'FL<xxx>', '<xxx>FT', 'SFC', or '<xxx>FT AGL'.
        subOneFromAlt (bool): WIll be True if we need to subtract
            one from the final value. This is only used for things
            like 'UP TO BUT NOT INCLUDING FL180' where we should
            return 17999 MSL.

    Returns:
        tuple: Tuple:

        1. (int) Altitude in feet (flight levels are converted).
        2. (str) Units. One of ``AGL``, ``MSL``, ``FT``.

    Raises:
        BadAltitudeTypeException: If the altitude type is bad. Should never happen
            because the regular expression will only pass known values.
    """

    if altString == 'SFC':
        return (0, 'AGL')

    # Determine units.
    if 'FL' in altString:
        units = 'MSL'
    elif 'AGL' in altString:
        units = 'AGL'
    elif 'FT' in altString:
        units = 'FT'
    else:
        raise ex.BadAltitudeTypeException("Cannot parse altitude string: '{}'".format(altString))

    # Convert altitude to integer.
    if altString.startswith('FL'):
        # Flight level.
        altInt = int(altString[2:]) * 100

        # This is only meaningful for flight levels.
        if subOneFromAlt:
            altInt = altInt - 1

    else:
        # Feet. This will always match because this is what the RegEx allows.
        idx = altString.find('F')
        altInt = int(altString[0:idx])

    return (altInt, units)

def parseSuaAltitudeString(altitudeString):
    """Parse NOTAM-D altitude string into standard fisb-decode
    altitude list.

    Args:
        altitudeString (str): Altitude string from the NOTAM-D SUA message.

    Returns:
        list: If the string is successfully parsed, will contain a list
            with 4 items: High altitude, High Units, Low altitude, Low Units.
            Units will be one of ``AGL``, ``MSL``, or ``FT``. ``FT`` is used when
            that is the best guess we can make. ``None`` is returned if the 
            altitude string doesn't match the regular expression.
    """
    suaAlt = NOTAM_SUA_ALT_RE.match(altitudeString)
    if suaAlt is None:
        return None

    lowerAltitude = suaAlt.group(1)
    upperAltitude = suaAlt.group(6)

    # sep is either '-' or ' UP TO BUT NOT INCLUDING
    sep = suaAlt.group(5)
    subOneFromAlt = False
    if sep != '-':
        subOneFromAlt = True

    lowAltInt, lowAltUnits = parseAlt(lowerAltitude, False)
    highAltInt, highAltUnits = parseAlt(upperAltitude, subOneFromAlt)

    return [highAltInt, highAltUnits, lowAltInt, lowAltUnits]

def notam(rYear, rMonth, rDay, location, reportId, text, contentsGraphics, \
        productId, station, rcvdTime):
    """Decode and a return a NOTAM- D,FDC,TMOA, or TRA message.

    These are in regular NOTAM format except for the FIS-B
    added header. Trying to find an issue time is
    not meaningful. According to the standard, the issue time
    they send may actually be one of three things. So we ignore
    it since we can't be sure what it actually is.

    The best times we can get are the 'start of activity' and 'end
    validity' times, if they
    are present. If not, we just expire after a configurable
    number of days.

    Args:
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        location (str): ICAO location for NOTAM.
        reportId (str): Combination of FAA year (1 or 2 digits) '-' and FAA report number.
        text (str): Full NOTAM text.
        contentsGraphics (dict): ``content_graphics`` dictionary, if any.
        productId (int): Product ID.
        station (string): Station where message originated
        rcvdTime (str): Message received time in ISO format.

    Returns:    
        dict: Dictionary with completed message.

    Raises:
        RegexDidNotMatchException: If NOTAM could not match template.
    """
    newMsg = {}

    # Parse off the NOTAM components
    nComp = NOTAM_RE.match(text)

    # Parse the NOTAM text (!...)
    nText = NOTAM_CONTENTS_RE.match(text)

    # Make sure we got what the connect decoding
    if (nComp is None) or (nText is None):
        raise ex.RegexDidNotMatchException("NOTAM could not match: '{}'".format(text))

    # Get the rest of the components
    notamSubtype = nComp.group(1)
    accountableLocation = nComp.group(4)
    affectedLocation = nComp.group(6)
    keyword = nComp.group(7)
    notamNumber = nComp.group(5)

    # Get the contents (must start with '!')
    notamContents = nText.group(4)

    if notamContents[0] != '!':
        raise ex.RegexDidNotMatchException("NOTAM format problem: '{}'".format(text))

    # Create the message
    newMsg['type'] = 'NOTAM'
    newMsg['subtype'] = notamSubtype

    newMsg['unique_name'] = reportId
    newMsg['location'] = location
    newMsg['contents'] = notamContents
    newMsg['accountable'] = accountableLocation
    newMsg['affected'] = affectedLocation
    newMsg['keyword'] = keyword
    newMsg['number'] = notamNumber
    newMsg['station'] = station
    newMsg = insertNotamDates(rYear, rMonth, rDay, text, newMsg)

    # Change subtype if this is an SUA message (can be SUAC, SUAE, SUAW).
    if (notamSubtype == 'D') and accountableLocation.startswith('SUA'):
        newMsg['subtype'] = 'D-SUA'
    
    # TMOA, TRA, and D-SUA can have airspace and altitude_text fields.
    # D-SUA can also parse top level altitudes field.
    if newMsg['subtype'] in ['TMOA', 'TRA', 'D-SUA']:

        # Parse the NOTAM-D SUA text
        nSua = NOTAM_SUA_RE.match(notamContents)
        if nSua is not None:
            newMsg['airspace'] = nSua.group(2)
            newMsg['altitude_text'] = nSua.group(3)

            # Try to parse the altitude text (D-SUA only)
            if newMsg['subtype'] == 'D-SUA':
                altitudes = parseSuaAltitudeString(nSua.group(3))
                if altitudes is not None:
                    newMsg['altitudes'] = altitudes
            
    # Don't always have a start of activity time (use received time as ISO ref)
    soat = rcvdTime
    if 'start_of_activity_time' in newMsg:
        soat = newMsg['start_of_activity_time']
    
    # see if we have geometry
    if contentsGraphics is not None:
        newMsg['geometry'] = createGeometryList(contentsGraphics, \
            soat, productId)

    # Also supply the NOTAM expiration time unless it is a PERM time.
    notamExpireTime = None
    if 'end_of_validity_time' in newMsg:
        eovt = newMsg['end_of_validity_time']
        if eovt != cfg.NOTAM_PERM_TIME:
            notamExpireTime = eovt

    newMsg['expiration_time'] = util.twgoExpirationTime(newMsg, rcvdTime, notamExpireTime)
    return newMsg

def insertNotamDates(rYear, rMonth, rDay, text, dict):
    """Inserts 'start of activity' and 'end of validity' dates in message.

    Places the ``start_of_activity_time``, and ``end_of_validity_time``
    keys in the dictionary for all NOTAM types. 

    An ``end_of_validity_time`` of PERM will use a configurable date which should
    be way in the future.

    Args:
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        text (str): Text of the entire NOTAM.
        dict (dict): Dictionary to insert messages into.

    Returns:
        dict: Dictionary with updated message fields.
    """
    startActIso = None
    endValidIso = None

    m = NOTAM_TIMES_RE.search(text)
    if m is not None:
        startAct = m.group(1)
        endValid = m.group(2)

        # See if permanent, if so use configured fixed date way in the future.
        if (endValid == 'PERM'):
            endValidIso = cfg.NOTAM_PERM_TIME
        else:
            endValidIso = util.notamTimeToIso8601(rYear, endValid)

        startActIso = util.notamTimeToIso8601(rYear, startAct)
        
    if startActIso is not None:
        dict['start_of_activity_time'] = startActIso

    if endValidIso is not None:
        dict['end_of_validity_time'] = endValidIso

    return dict
