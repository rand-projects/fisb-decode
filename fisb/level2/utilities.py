"""Module containing utility functions for level2
"""

import sys, os, datetime, copy
import math, random

import fisb.level2.level2Exceptions as ex
import fisb.level2.level2Config as cfg

# Timedelta object representing one day.
ONE_DAY = datetime.timedelta(1)

# String used to compress bins. Each index is the number
# of times to repeat a bin. 0 isn't used, and the max number 
# of repetitions is 32 ('W')
REPETITION_MAP = '0123456789ABCDEFGHIJKLMNOPQRSTUVW'

def cleanFAAText(origText):
    """Take FAA text message and trim whitespace from end.

    FAA text messages have all sorts of trailing whitespace
    issues. We split the message into lines and remove all
    right trailing whitespace. We then recombine them into
    a uniform version with no trailing whitespace.

    The final line will not have a newline character at the
    end.

    Args:
        origText (str): Message text as it comes from the FAA.

    Returns:
        str: Cleaned up text as described above.
    """
    lines = origText.split('\n')
    numLines = len(lines)

    # Remove empty line at end if present
    if lines[-1] == '':
        numLines -= 1

    for i in range(0, numLines):
        lines[i] = lines[i].rstrip()

    newText = '\n'.join(lines).rstrip()

    return newText
    
def iso8601ToSeconds(isoString, allowMicroSeconds = False):
    """Convert ISO-8601 UTC datestring to seconds past epoch.

    Args:
        isoString (str): ISO-8601 string
        allowMicroSeconds (bool): Default is ``False``, round results
         to nearest seconds. If ``True``, will keep microseconds.

    Returns:
        str: ISO-8601 string converted to python time in fractional
        seconds.
    """
    if '.' in isoString:
        utc = datetime.datetime.strptime(isoString, '%Y-%m-%dT%H:%M:%S.%fZ')
    else:
        utc = datetime.datetime.strptime(isoString, '%Y-%m-%dT%H:%M:%SZ')
        
    # Convert to seconds
    secs = (utc - datetime.datetime(1970, 1, 1)).total_seconds()
    if not allowMicroSeconds:
        secs = round(secs)
    return secs

def componentsToIso8601Referenced(referenceIso, month, day, hour, minute):
    """Return time components as an ISO-8601 formatted string referenced to ISO date.

    Given an month, day, hour, and minute as well as reference ISO time,
    return an ISO formatted date most closely matching the reference date.
    This basically implies finding the best year. This is useful for times
    close to when the year changes. The year portion of the returned ISO date
    will either be the same as the reference or +/- 1 year.

    Args:
        month (int): Month of year (1-12)
        day (int): Day of month
        hour (int): Hour of day (0-23)
        minute (int): Minute of hour (0-59)

    Returns:
        str: ISO-8601 string representing the supplied parameters.
    """
    referenceYear = int(referenceIso[0:4])
    referenceSeconds = iso8601ToSeconds(referenceIso)


    lastYearDiff = abs(referenceSeconds - datetime.datetime(referenceYear - 1, month, \
        day, hour, minute, tzinfo=datetime.timezone.utc).timestamp())
    nextYearDiff = abs(referenceSeconds - datetime.datetime(referenceYear + 1, month, \
        day, hour, minute, tzinfo=datetime.timezone.utc).timestamp())
    thisYearDiff = abs(referenceSeconds - datetime.datetime(referenceYear, month, \
        day, hour, minute, tzinfo=datetime.timezone.utc).timestamp())

    winner = min(lastYearDiff, nextYearDiff, thisYearDiff)

    if winner == thisYearDiff:
        winnerIso = componentsToIso8601(referenceYear, month, day, hour, minute)        
    elif winner == nextYearDiff:
        winnerIso = componentsToIso8601(referenceYear + 1, month, day, hour, minute)        
    else:
        winnerIso = componentsToIso8601(referenceYear - 1, month, day, hour, minute)

    return winnerIso

def componentsToIso8601(year, month, day, hour, minute):
    """Return time components as an ISO-8601 formatted string

    Args:
        year (int): 4 digit year
        month (int): Month of year (1-12)
        day (int): Day of month
        hour (int): Hour of day (0-23)
        minute (int): Minute of hour (0-59)

    Returns:
        str: ISO-8601 string representing the supplied parameters.
    """
    
    dtObj = datetime.datetime(year, month, day, hour, minute)
    return '{}Z'.format(dtObj.isoformat())

def case24Hour(dateObj, faaHour):
    """Correct a date when FAA sends '24' as an hour. Add a day.

    For certain forcasts like TAF end time of a valid period,
    an FAA time can have 24 as the hour. This implies the next day.
    Add a day to the date and set the hour back to zero.

    Args:
        dateObj (datetime.date): Object representing a date.
        faaHour (int): FAA supplied hour. Usually 0-23, but may be 24 in 
            certain forecasts.
    Returns:
        tuple: Two item tuple:

        1. ``dateObj``: See below.
        2. ``faaHour``: See below.

        If the ``faaHour`` is not 24, returns a tuple of the supplied 
        arguments. If the faaHour is 24, will return a tuple
        where ``dateObj`` is increased by one day, and ``faaHour``
        will be 0.
    """
    if (faaHour != 24):
        return (dateObj, faaHour)

    return (dateObj + ONE_DAY, 0)

def addSecondsToIso8601(isoStr, seconds):
    """Given an ISO-8601 string, add ``seconds`` seconds to it.

    Args:
        isoStr (str): ISO-8601 formatted string to have minutes added.
        seconds (int): Number of seconds to add. Can be negative.

    Returns:
        str: ISO-8601 string with the specified number of seconds
        added.
    """
    secs = iso8601ToSeconds(isoStr) + seconds

    utcObj = datetime.datetime.utcfromtimestamp(secs)
    return '{}Z'.format(utcObj.isoformat())

def addMinutesToIso8601(isoStr, minutes):
    """Given an ISO-8601 string, add ``minutes`` minutes to it.

    Args:
        isoStr (str): ISO-8601 formatted string to add minutes to.
        minutes (int): Number of minutes to add. Can be negative.

    Returns:
        str: ISO-8601 string with the specified number of minutes
        added.
    """
    secs = iso8601ToSeconds(isoStr) + (minutes * 60)

    utcObj = datetime.datetime.utcfromtimestamp(secs)
    return '{}Z'.format(utcObj.isoformat())

def addHoursToIso8601(isoStr, hours):
    """Given an ISO-8601 string, add ``hours`` hours to it.

    Args:
        isoStr (str): ISO-8601 formatted string to add hours to.
        hours (int): Number of hours to add. Can be negative.

    Returns:
        str: ISO-8601 string with the specified number of hours
        added.
    """
    secs = iso8601ToSeconds(isoStr) + (hours * 3600)

    utcObj = datetime.datetime.utcfromtimestamp(secs)
    return '{}Z'.format(utcObj.isoformat())

def addDaysToIso8601(isoStr, days):
    """Given an ISO-8601 string, add ``days`` days to it.

    Args:
        isoStr (str): ISO-8601 formatted string to add days to.
        days (int): Number of days to add. Can be negative.

    Returns:
        str: ISO-8601 string with the specified number of days
        added.
    """
    secs = iso8601ToSeconds(isoStr) + (days * 86400)

    utcObj = datetime.datetime.utcfromtimestamp(secs)
    return '{}Z'.format(utcObj.isoformat())

def notamTimeToIso8601(currentYear, faaStr):
    """Converts NOTAM ``yymmddhhmm`` string to Iso8601

    Args:
        currentYear (int): Current time year
        faaStr (str): FAA NOTAM time in the form ``YYMMDDHHMM``

    Returns:
        str: FAA time as an ISO-8601 string
    """
    faaYear = doubleDigitYear(currentYear, faaStr[0:2])
    faaMonth = int(faaStr[2:4])
    faaDay = int(faaStr[4:6])
    faaHour = int(faaStr[6:8])
    faaMinute = int(faaStr[8:10])    

    return componentsToIso8601(faaYear, \
                               faaMonth, \
                               faaDay, \
                               faaHour, \
                               faaMinute)

def iso8601FromApduHourMins(currentYear, currentMonth, \
            currentDay, currentHour, currentMinute, \
            apduHour, apduMinute, favorPast=True):
    """Best guess date from APDU hour and minute.

    Another episode of the FAA's favorite game show: *Guess my time*.
    In this show we are given an hour and a minute, and asked to figure
    out what date the FAA was thinking of. This date is sometimes in
    the future and sometimes in the past. It should be within 24 hours of
    the current message received date.

    What we do is figure out the time the message was received, then
    plug the hour and minute into the current date. We then check that
    value, as well as one day in the future and one day in the past and
    pick the one closest to the message received time.

    Args:
        currentYear (int): Message received year (4 digit).
        currentMonth (int): Message received month (1-12).
        currentDay (int): Message received day of month.
        currentHour (int): Message received hour (0-23).
        currentMinute (int): Message received minute (0-60).
        apduHour (int): APDU received hour (0-23).
        apduMinute (int): APDU minute (0-60).
        favorPast (bool): In case of a tie with past and future, favorPast
          if ``True``.

    Returns:
        str: Best ISO-8601 UTC match given the supplied arguments.
    """
    # Datetime object when the message was received.
    currentDtObj = datetime.datetime(currentYear, currentMonth,\
        currentDay, currentHour, currentMinute)

    # Meet today's contestents...
    apduNow = datetime.datetime(currentYear, currentMonth, currentDay,\
        apduHour, apduMinute)
    apduPlusDay = apduNow + datetime.timedelta(days=1)
    apduMinusDay = apduNow + datetime.timedelta(days=-1)

    # Calculate time differences...
    diffNowSecs = abs((currentDtObj - apduNow).total_seconds())
    diffPlusSecs = abs((currentDtObj - apduPlusDay).total_seconds())
    diffMinusSecs = abs((currentDtObj - apduMinusDay).total_seconds())
    minimumSecs = min(diffNowSecs, diffPlusSecs, diffMinusSecs)

    # Rare, but we can have a tie. 'favorPast' can be used as a
    # clue if this event would normally fall in the past or future.
    hasTie = False
    if diffPlusSecs == diffMinusSecs:
        hasTie = True

    # See who today's winner is!
    winner = apduNow
    if minimumSecs == diffPlusSecs:
        winner = apduPlusDay
    elif minimumSecs == diffMinusSecs:
        winner = apduMinusDay

    # If a tie, figure out the winner
    if (winner != apduNow) and hasTie:
        if favorPast:
            winner = apduMinusDay
        else:
            winner = apduPlusDay
            
    # Today's winner gets a free ISO-8601 conversion
    # and a starring role in a JSON message!!
    return componentsToIso8601(winner.year, \
                               winner.month, \
                               winner.day, \
                               winner.hour, \
                               winner.minute)

def dayHourMinToIso8601(currentYear, currentMonth, currentDay, faaStr):
    """Convert FAA standard 6 digit time string to ISO time

    Converts a string of the form ``ddhhmm`` (i.e. ``052245``)
    into an ISO time string. It will also handle string of the
    form ``ddhh`` (i.e. ``0522`` and ``0524``) that
    are used in forecasts.

    Assumes that the date/time is within 10 days +/- of the 
    current time.

    Args:
        currentYear (int): Current year (4 digit).
        currentMonth (int): Current month (1-12).
        currentDay (int): Current day of month.
        faaStr (int): FAA supplied string either in the form
            ``ddhhmm`` or ``ddhh``.

    Returns:
        str: Best ISO-8601 UTC match given the supplied arguments.

    Raises:
        FAADateOutOfRangeException: If the date is outside the range of reasonable
            possibilities.
    """
    faaDay = int(faaStr[0:2])
    faaHour = int(faaStr[2:4])

    # Some dates, like forecast valid times, don't have a
    # minute.
    if (len(faaStr) == 6):
        faaMinute = int(faaStr[4:6])
    else:
        faaMinute = 0

    currentDate = datetime.date(currentYear, currentMonth, currentDay)

    # Easy case, same day
    if faaDay == currentDay:
        (currentDate, faaHour) = case24Hour(currentDate, faaHour)
        return componentsToIso8601(currentDate.year, \
                                   currentDate.month, \
                                   currentDate.day, \
                                   faaHour, \
                                   faaMinute)

    # We will look forwards and backwards at the same time
    # to try to find the correct day (the assumption is that
    # most days will be close to the current day). Raise an exception
    # if we don't find it. Let Python handle the heavy lifting of
    # changing months, years, and worrying about leap years.

    forwardDate = currentDate
    backwardDate = currentDate
    
    for _ in range(0, 10):
        
        forwardDate = forwardDate + ONE_DAY
        if forwardDate.day == faaDay:
            (forwardDate, faaHour) = case24Hour(forwardDate, faaHour)
            return componentsToIso8601(forwardDate.year, \
                                       forwardDate.month, \
                                       forwardDate.day, \
                                       faaHour, \
                                       faaMinute)            

        backwardDate = backwardDate - ONE_DAY
        if backwardDate.day == faaDay:
            (backwardDate, faaHour) = case24Hour(backwardDate, faaHour)
            return componentsToIso8601(backwardDate.year, \
                                       backwardDate.month, \
                                       backwardDate.day, \
                                       faaHour, \
                                       faaMinute)            

    # If we made it here, the date wasn't with 10 days.
    raise ex.FAADateOutOfRangeException("FAA date too far out of range. " + \
                                        "Current day {}, FAA date {}" \
                                        .format(currentDay, faaStr))

def singleDigitYear(currentYear, suppliedYearStr):
    """Convert FAA single digit year string into integer year.

    If year is up to 4 years in the future, consider it a future
    year. Otherwise, consider it a past year.

    For example: ::

       2019, '9' -> 2019
       2019, '6' -> 2016
       2019, '1' -> 2021

    Args:
        currentYear (int): Current full year as an integer.
        suppliedYearStr (str): Single digit string from 0-9.

    Returns:
        int: Integer year that best fits the supplied value.

    Raises:
        BadYearException: If got something other than 0-9.
    """
    suppliedYear = int(suppliedYearStr)
    
    if suppliedYear >= 10:
        raise ex.BadYearException('In singleDigitYear, expecting value 0-9, got {}'.format(suppliedYear))

    # Get 1's place of current year as digit (0-9)
    currentYearDigit = int(str(currentYear)[3])

    # Difference or year digits.
    diff = suppliedYear - currentYearDigit

    # This is the number line used for year determination
    # It is the suppliedYear - currentYearDigit (or 'diff').
    # We go 4 years in the future and 5 years in the past.
    # Current year stays the current year.
    #
    # [-9 -8 -7 -6] -5 -4 -3 -2 -1  [0  1  2  3  4]  5  6  7  8  9
    #   f  f  f  f   p  p  p  p  p   f  f  f  f  f   p  p  p  p  p
    #
    # where: f = future date and p = past date
    
    if (diff >= 0) and (diff < 5):
        retYear = currentYear + diff
    elif diff <= -6:
        retYear = currentYear + (diff + 10)
    elif (diff > -6) and (diff < 0):
        retYear = currentYear + diff
    elif diff >= 5:
        retYear = currentYear - (10 - diff)

    return retYear

def doubleDigitYear(currentYear, suppliedYearStr, isString = True):
    """Convert FAA double digit year string into integer year.

    If year is up to 49 years in the future, consider it a future
    year. Otherwise, consider it a past year.

    For example: ::

       2019, '19' -> 2019
       2019, '10' -> 2010
       2019, '30' -> 2030

    Args:
        currentYear (int): Current full year as an integer.
        suppliedYearStr (str): Digit string from 0-99.
        isString: If ``True``: ``suppliedYearStr`` is treated as a two
            digit year string. If ``False``: it is assumed to be a integer between 
            0 and 99.

    Returns:
        int: Integer year that best fits the supplied value.

    Raises:
        BadYearException: got something other than 00-99.
    """
    if isString:
        suppliedYear = int(suppliedYearStr)
    else:
        suppliedYear = suppliedYearStr

    if suppliedYear >= 100:
        raise ex.BadYearException('In doubleDigitYear, expecting value 00-99, got {}'.format(suppliedYear))

    # Get last 2 places of current year as digit (0-99)
    currentYearDigit = int(str(currentYear)[2:4])

    diff = suppliedYear - currentYearDigit

    if (diff >= 0) and (diff < 50):
        retYear = currentYear + diff
    elif diff <= -60:
        retYear = currentYear + (diff + 100)
    elif (diff > -60) and (diff < 0):
        retYear = currentYear + diff
    elif diff >= 50:
        retYear = currentYear - (100 - diff)
           
    return retYear

def decodeObjectQualifiersList(objectQualifiers):
    """Turn an object qualifiers list into a list of conditions.

    Object qualifiers are found as part of G-AIRMET messages.

    Object qualifiers are stored in a three array list, each element represents
    eight bits or 24 bits in total. Most of the elements are reserved, with the
    last byte containing most of the values we care about.

    Args:
        objectQualifiers (list): List of 3 integers representing the
            object qualifiers list from the message.

    Returns:
        list: List of text abbreviations representing the qualifiers.
        Available qualifiers:

          - UNSPCFD (unspecified)
          - ASH
          - DUST
          - CLOUDS
          - BLSNOW (blowing snow)
          - SMOKE
          - HAZE
          - FOG
          - MIST
          - PCPN (precipitation)
    """
    objQualList = []

    if (objectQualifiers[0] & 0x80) != 0:
        # Unspecified
        objQualList.append('UNSPCFD')

    if (objectQualifiers[1] & 0x01) != 0:
        # Ash
        objQualList.append('ASH')

    if (objectQualifiers[2] & 0x80) != 0:
        # Dust
        objQualList.append('DUST')

    if (objectQualifiers[2] & 0x40) != 0:
        # Clouds
        objQualList.append('CLOUDS')

    if (objectQualifiers[2] & 0x20) != 0:
        # Blowing snow
        objQualList.append('BLSNOW')

    if (objectQualifiers[2] & 0x10) != 0:
        #Smoke
        objQualList.append('SMOKE')

    if (objectQualifiers[2] & 0x08) != 0:
        # Haze
        objQualList.append('HAZE')

    if (objectQualifiers[2] & 0x04) != 0:
        # Fog
        objQualList.append('FOG')

    if (objectQualifiers[2] & 0x02) != 0:
        # Mist
        objQualList.append('MIST')

    if (objectQualifiers[2] & 0x01) != 0:
        # Precipitation
        objQualList.append('PCPN')
    
    return objQualList

def getAltitudeAndGeoType(overlayGeometryOptions):
    """Given a FIS-B 'overlay geometry option', turn into altitude and geometry types.

    Args:
        overlayGeometryOptions (int): FIS-B overlay geometry option

    Returns:
        tuple: Tuple:

        1. (str) Altitude type (``MSL`` or ``AGL``)
        2. (str) Geometry type (one of ``POLYGON``, ``POLYLINE``, ``CIRCLE``, or ``POINT``)

    Raises:
        TwgoGeometryNotImplementedException: For unimplemented geometry.
    """
    if overlayGeometryOptions == 3:
            altType = "MSL"
            geoType = "POLYGON"
    elif overlayGeometryOptions == 4:
            altType = "AGL"
            geoType = "POLYGON"
    elif overlayGeometryOptions == 7:
            altType = "MSL"
            geoType = "CIRCLE"
    elif overlayGeometryOptions == 8:
            altType = "AGL"
            geoType = "CIRCLE"
    elif overlayGeometryOptions == 9:
            altType = "AGL"
            geoType = "POINT"
    elif overlayGeometryOptions == 10:
            altType = "MSL"
            geoType = "POINT"
    elif overlayGeometryOptions == 11:
            altType = "MSL"
            geoType = "POLYLINE"
    elif overlayGeometryOptions == 12: # Have never seen this
            altType = "AGL"
            geoType = "POLYLINE"
    else:
        ex.TwgoGeometryNotImplementedException("Geometry {} not implemented".format(overlayGeometryOptions))

    return (altType, geoType)

# Object element values
OBJECT_ELEMENT_LIST = ['TFR', 'TURB', 'LLWS', 'SFC', 'ICING', \
                     'FRZLVL', 'IFR', 'MTN']

def populateCommonItems(record, referenceIso):
    """Populate message items common to all geometry types.

    Handles things like the geometry type, start and stop times, 
    cancelled status, element type, label, and G-AIRMET qualifiers.

    This gets the geometry portion of the message started, and more 
    items are added when the geometry specific function is called.

    Args:
        record (dict): Record containing geometry information.
        referenceIso (str): ISO time relatively close to the message time
            which helps to fill in any date details for start and stop 
            times.
    
    Returns:
        dict: Dictionary containing geometry information. Further items
        will be added.
    """
    recDict = {}
    
    # Basic geometry type and altitude type
    overlayGeometryOptions = record['overlay_geometry_options']
    altType, geoType = getAltitudeAndGeoType(overlayGeometryOptions)
    
    recDict['type'] = geoType

    # High altitude, high altitude type, low altitude, low altitude type
    # The altitudes will get modified for each geometry. Only TRA and TMOA
    # will change the altitude types.
    recDict['altitudes'] = [0, altType, 0, altType]

    # Start and stop times
    # Usually, the record has a definite start and end time. It doesn't have
    # to, but the only time we see this is in test data.
    # These values have an impact on when messages get expired. It may mean adding
    # a received time to the message to keep it active.

    # Some NOTAMS run over multiple days, for certain hours of the day.
    # These need to have a received time so that they will expire only after
    # they are done being sent.
    dateTimeFormat = record['date_time_format']    

    recordAppOpt = record['record_applicability_options']

    if recordAppOpt in [1, 3]:
        if dateTimeFormat == 1:
            recDict['start_time'] = componentsToIso8601Referenced(referenceIso, \
                                        record['start_month'], \
                                        record['start_day'], \
                                        record['start_hour'], \
                                        record['start_minute'])
        elif dateTimeFormat == 3:
            recDict['start_hour'] = '{:02d}{:02d}'.format(record['start_hour'], \
                record['start_minute'])
    if recordAppOpt in [2, 3]:
        if dateTimeFormat == 1:        
            recDict['stop_time'] = componentsToIso8601Referenced(referenceIso, \
                                       record['stop_month'], \
                                       record['stop_day'], \
                                       record['stop_hour'], \
                                       record['stop_minute'])
        elif dateTimeFormat == 3:
            recDict['stop_hour'] = '{:02d}{:02d}'.format(record['stop_hour'], \
                record['stop_minute'])
    
    # Cancelled status
    if record['object_status'] == 13:
        recDict['cancelled'] = 1
    
    # Element type
    if record['element_flag'] != 0:
        recDict['element'] = OBJECT_ELEMENT_LIST[record['object_element']]

    # Label
    if record['label_flag'] == 1:
        recDict['airport_id'] = record['object_label']

    # Qualifier for G-AIRMET
    if record['qual_flag'] == 1:
        recDict['conditions'] = decodeObjectQualifiersList(record['object_qualifiers'])

    return recDict

def shapeBasedDispatch(shape, vertexList, recDict):
    """Given a shape, process it using its specific routine.

    Args:
        shape (str): Type of shape. One of ``POLYGON``, ``POLYLINE``,
          ``CIRCLE``, or ``POINT``.
        vertexList (list): List of vertexes for this shape.
        recDict (dict): Dictionary to add the shape to.
    """
    if shape in ['POLYGON', 'POLYLINE']:
        processPolygonPolyline(vertexList, recDict)
    elif shape == 'CIRCLE':
        processCircle(vertexList, recDict)
    elif shape == 'POINT':
        processPoint(vertexList, recDict)

def polylineAppendCheck(currentVL, nextVL):
    """Given two polyline vertex lists, append them if needed.

    Polylines to be appended will have the last coordinate of
    the first vertex list be the same as the first coordinate of the
    second vertex list. When appending, we need to eliminate
    one of these coordinates.

    Args:
        currentVL (list): First of two lists of vertexes to check.
        nextVL (list): Second of two lists of vertexes to check.

    Returns:
        tuple: Tuple:

        1. ``True`` if the vertexes were appended, otherwise ``False``.
        2. New vertex list if appended (otherwise ignored).
    """
    wasAppended = False
    appendedList = []

    # In a polyline, the last coord of the first list will be the 
    # first coord of the new list
    last = currentVL[-1]
    first = nextVL[0]

    if (last[0] == first[0]) and (last[1] == first[1]) and (last[2] == first[2]):
        # It is to be appended
        wasAppended = True
        appendedList = currentVL[:-1] + nextVL
        
    return (wasAppended, appendedList)

def polygonAppendCheck(currentVL, nextVL):
    """Given two polygon vertex lists, append them if needed.

    Polygons will always have the last coordinate be the same
    as the first coordinate. When appending, they may, or may not,
    have the last coordinate of
    the first vertex list be the same as the first coordinate of the
    second vertex list. When appending, we need to eliminate
    one of these coordinates if present.

    Args:
        currentVL (list): First of two lists of vertexes to check.
        nextVL (list): Second of two lists of vertexes to check.

    Returns:
        tuple: Tuple:

        1. ``True`` if the vertexes were appended, otherwise ``False``.
        2. New vertex list if appended (otherwise ignored).
    """
    wasAppended = False
    appendedList = []

    # In a polygon, the polygon always connects to the origin. However, there
    # may be two different altitude levels present.
    currentStart = currentVL[0]
    polyIsComplete = False

    for x in currentVL[1:]:
        if (x[0] == currentStart[0]) and (x[1] == currentStart[1]) \
            and (x[2] == currentStart[2]):
            polyIsComplete = True
        elif polyIsComplete:
            # Polygon probably starting new altitude
            currentStart = x
            polyIsComplete = False

    if not polyIsComplete:
        wasAppended = True

        # In SOME cases, multi-record polygons act like
        # polylines and duplicate the last point.
        last = currentVL[-1]
        first = nextVL[0]

        if (last[0] == first[0]) and (last[1] == first[1]) and (last[2] == first[2]):
            # skip duplicate element
            appendedList = currentVL[:-1] + nextVL
        else:
            appendedList = currentVL + nextVL
        
    return (wasAppended, appendedList)

def polyAppend(isPolygon, records, curRecordNum, numRecords):
    """Called for polygons and polylines only. Append any needed vertexes.

    Performs the actual work of appending large polygons or polylines.

    Args:
        isPolygon (bool): ``True`` if polygon. ``False`` is polyline.
        records (list): List of geometry records. This will be altered to
          do the merge.
        curRecordNum (int): Index into ``records`` we are working on.
        numRecords (int): Total original length of ``records`` before merging.

    Returns:
        tuple: Tuple:

        1. Number of records to skip. If we appended two records we will
           then need to skip one record when going through a list of 
           records.
        2. Updated (merged) record to use (or original if no merge was
           performed).
    """
    # We will always have at least one more record to check
    # If the next record is the same type as the current one, we are done.
    skipNum = 0
    origRecordNum = curRecordNum
    vertexList = records[curRecordNum]['vertex_list']

    while True:
        curRecordNum = curRecordNum + 1
        if curRecordNum == numRecords:
            # Return with altered (if any) original record with new vertex list
            records[origRecordNum]['vertex_list'] = vertexList
            return (skipNum, records[origRecordNum])
        
        # If the next record is the type as the current one, we are done.    
        if records[origRecordNum]['overlay_geometry_options'] != \
            records[curRecordNum]['overlay_geometry_options']:
            # Return with altered (if any) original record with new vertex list
            records[origRecordNum]['vertex_list'] = vertexList
            return (skipNum, records[origRecordNum])

        # May be looking at a possible append
        if isPolygon:
            wasAppended, appendedVertextList = \
                polygonAppendCheck(vertexList, records[curRecordNum]['vertex_list'])
        else:
            wasAppended, appendedVertextList = \
                polylineAppendCheck(vertexList, records[curRecordNum]['vertex_list'])

        if not wasAppended:        
            records[origRecordNum]['vertex_list'] = vertexList
            return (skipNum, records[origRecordNum])
        else:
            vertexList = appendedVertextList
            skipNum = skipNum + 1        

def duplicatePointsAndCircles(records):
    """Find points and circles with multiple vertexes and move each to its own record.

    Rarely we will get a record with a circle that has multiple vertexes. This could
    also happen with points (although never seen). If we find this, duplicate the
    record and move each vertex into its own record for more uniform handling.

    Args:
        records (list): Lest of all geometry records.

    Returns:
        list: All the records with possibly new records for the separated
        vertexes.
    """
    newRecords = []

    for record in records:
        overlayGeoOptions = record['overlay_geometry_options']

        if (overlayGeoOptions in [7, 8, 9, 10]):
            # Circles and points. Usually (except in 1 case seen in the wild with circles)
            # only have one vertext. If more, duplicate the record and add extras
            # one per record.
            if len(record['vertex_list']) == 1:
                newRecords.append(record)
            else:
                vertexList = copy.deepcopy(record['vertex_list'])                
                for v in vertexList:
                    recordCopy = copy.deepcopy(record)
                    recordCopy['vertex_list'] = [v]
                    newRecords.append(recordCopy)
        else:
            newRecords.append(record)
        
    return newRecords        

def geometryPrePass(records):
    """Append any polyline or polygon records that span more than 1 record.

    Polygons and polylines can have large numbers of coordinates that
    exceed the maximum of 64 vertexes per record. This routine will
    append them and return only one record per polygon or polyline.

    Args:
        records (list): List of records containing geometry objects.
          Some of these might be large polygons or polylines that 
          need to be merged.

    Returns:
        dict: The records we were given as an argument, with any large
        polygons or polylines merged into a single set of coordinates.
    """
    # Simple case if only one record
    recordsLen = len(records)
    lastRecord = recordsLen - 1
    
    if recordsLen == 1:
        return records

    skipNum = 0
    recordNum = -1
    
    newRecords = []
    for record in records:
        recordNum = recordNum + 1

        # Skip over records we already appended        
        if skipNum > 0:
            skipNum = skipNum - 1
            continue
        overlayGeoOptions = record['overlay_geometry_options']
        if (overlayGeoOptions in [3, 4]) and (recordNum != lastRecord):
            # Polygon
            skipNum, updatedRecord = polyAppend(True,records, recordNum, recordsLen)
            newRecords.append(updatedRecord)
        elif (overlayGeoOptions in [11, 12]) and (recordNum != lastRecord):
            # Polyline
            skipNum, updatedRecord = polyAppend(False,records, recordNum, recordsLen)
            newRecords.append(updatedRecord)
        else:
            newRecords.append(record)
            skipNum = 0

    return newRecords

def geometryOverlayOperatorPass(records):
    """Called only for TMOA, TRA to merge any operator overlays of 1.

    Not all TMOA or TRA's use operator overlays of 1. But if they do,
    the standard promises to send only one geometry, so there should
    only be two records (after any merging of long vectors which has
    already been done). This will merge the altitude and altitude
    type information into standard form. It also performs some sanity
    checks to make sure we haven't been thrown a curveball.

    Args:
        records (dict): Records (up to two) with TMOA or TRA data.

    Returns:
        dict: Single record. Either the record that was the argument or
        a merged record from the two that were sent.
    
    Raises:
        GeoTypeMismatchException: If this isn't a polygon or circle.
        UnequalVertexLengthsException: If the overlay operator is ``1`` but
          the records have different vertex lengths.
        BadOverlayTypeException: If the geometries do not match.
    """
    if len(records) != 2:
        return records

    # See if overlay operator present
    if records[0]['overlay_operator'] != 1:
        return records

    # What we do is to only return record[0], but sneak some
    # metadata in it that is used later to fix the altitudes
    # and altitude types

    # Determine if polygon or circle
    overlayGeoOptions = records[0]['overlay_geometry_options']

    altType0, geoType0 = getAltitudeAndGeoType(overlayGeoOptions)
    altType1, geoType1 = getAltitudeAndGeoType(records[1]['overlay_geometry_options'])

    if (geoType0 != geoType1):
        raise ex.GeoTypeMismatchException('geometryOverlayOperator not polygon or circle')

    # Sanity check. Make sure same number of vertexes in each vertex_list
    if len(records[0]['vertex_list']) != len(records[1]['vertex_list']):
        raise ex.UnequalVertexLengthsException('Overlay operator == 1 records have different vertex lengths')

    if geoType0 == 'POLYGON':
        records[0]['override_altitudes'] = [records[0]['vertex_list'][0][2], \
            altType0, \
            records[1]['vertex_list'][0][2], \
            altType1]
    elif geoType0 == 'CIRCLE':
        # For a circle, we can change the altitude on the spot. No further processing
        # required
        records[0]['vertex_list'][0][4] = records[1]['vertex_list'][0][4]
    else:
        raise ex.BadOverlayTypeException('geometryOverlayOperator not polygon or circle')
    
    return [records[0]]
    
    
def processGeometry(records, referenceIso, productId):
    """Produce a geometry list for inclusion in the final message.
    
    Args:
        contentsGraphics (list): List of all records from a ``contents_graphics`` section.
        referenceIso (str): This is an ISO time (usually ``start_of_activity_time``) which
            is used as a reference to provide parts of dates that are not provided.
        productId (int): Product ID.
    Returns:
        list: Geometry list information for message inclusion.
    """

    recordsList = duplicatePointsAndCircles(records)
    recordsList = geometryPrePass(recordsList)

    # Special check for TRA, TMOA overlay_operator merges.
    if productId in [16, 17]:
        recordsList = geometryOverlayOperatorPass(recordsList)

    gList = []

    for record in recordsList:
        recDict = populateCommonItems(record, referenceIso)
        shapeBasedDispatch(recDict['type'], \
                record['vertex_list'], recDict)

        # Fix-up for TMOA, TRA
        if 'override_altitudes' in record:
            recDict['altitudes'] = record['override_altitudes']

        gList.append(recDict)

    return gList

def processPoint(vertexList, recDict):
    """Create one point object.

    Will add its information to ``recDict``

    Args:
        vertexList (list): List with single vertex.
            Any multiple points have already been factored out into
            individual items.
        recDict (dict): Dictionary containing geometry information. Information
            will be added to this object.         
    """
    x = vertexList[0]

    alts = recDict['altitudes']
    alts[0] = x[2]
    alts[2] = 0

    recDict['altitudes'] = alts
    recDict['coordinates'] = [x[0], x[1]]

def processCircle(vertexList, recDict):
    """Create one circle object.

    Given a list containing a single FIS-B vertex from an Extended Range Circular Prism,
    convert it to a standardized list for output in messages.

    We only handle the single case of a circle with a simple radius.
    We don't handle ellipses, complex parallelepiped objects, or things that look
    like ice cream cones or kitchen trash cans. Generate an exception if
    we see one. We have never seen an example of anything other than a simple
    circle in the wild. Even the test messages don't have anything other than a
    simple circle or straight cylinder.

    Args:
        vertexList (list): List containing a single vertex. Each item is an Extended Range Circular
            Prism. Any other vertexes have already been factored out to their 
            own dictionary.
        recDict (dict): Dictionary containing geometry information. Information
            will be added to this object.         
    
    Raises:
        TwgoGeometryNotImplementedException: If this is not a simple circle with
            a radius.
        TooManyCirclesException: If there are  multiple circles. Should not see this.
    """
    if len(vertexList) != 1:
        raise ex.TooManyCirclesException('Multiple circles not implemented.')

    x = vertexList[0]

    # Make sure it is only the case of a circle with a simple radius.
    if (x[0] != x[2]) or \
        (x[1] != x[3]) or \
        (x[8] != 0) or \
        (x[6] != x[7]):
        raise ex.TwgoGeometryNotImplementedException("Fancy circular prisms not implemented")

    alts = recDict['altitudes']
    alts[0] = x[5]
    alts[2] = x[4]

    recDict['altitudes'] = alts
    recDict['coordinates'] = [x[0], x[1]]
    recDict['radius_nm'] = x[6]

def processPolygonPolyline(vertexList, recDict):
    """Process a polygon or polyline.

    Given a list of FIS-B vertexes from an Extended Range 3D Polygon
    or Extended Range 3D Polyline,
    add its information to the supplied ``recDict``.

    Each coordinate as it comes from FIS-B encodes an altitude. Sometimes
    they send two sets of identical coordinates with the only difference
    being the altitudes. This routine will factor out the altitudes and
    produce a single set of coordinates with one or two altitudes. We have
    only seen this situation. However, if the coordinate sets aren't identical
    or they send more than two altitudes, we will generate an exception.

    Args:
        vertexList (list): List of vertexes. Each item is an Extended Range 3D
            Polygon or an Extended Range 3D Polyline.
        recDict (dict): Dictionary containing geometry information. Information
            will be added to this object.         
    
    Raises:
        AltitudesDontMatchException: If the two sets of vertex altitudes do not match.
        TooManyAltitudesException: For more than 2 altitudes in vertex list.
    """
    # The altitude is actually a part of each polygon's coordinates.
    # We make a dictionary with the key being the altitude level and
    # the value being a list of vertex lat/long pairs.
    altVertDict = {}
    
    # We make an altitude list too, used later to see if we can
    # collapse two identical lists to one.
    altList = []
    
    for x in vertexList:
        longitude = x[0]
        latitude = x[1]
        alt = x[2]

        if alt not in altList:
            altList.append(alt)
            
        if alt not in altVertDict:
            altVertDict[alt] = [[longitude, latitude]]
        else:
            vertexList = altVertDict[alt]
            vertexList.append([longitude, latitude])
    
    # For reasons beyond me, if there are two altitudes sent,
    # they often send identical coordinates for each one.
    # If there are only two altitudes and the coordinates are identical,
    # we combine the two into a single list.
    # Altitudes are always sent with the high altitude first, so altList[0]
    # will always have the higher altitude.
    alLen = len(altList)

    if alLen == 1:
        alts = recDict['altitudes']
        alts[0] = altList[0]
        alts[2] = 0
        recDict['altitudes'] = alts
    elif alLen == 2:
        alts = recDict['altitudes']
        alts[0] = altList[0]
        alts[2] = altList[1]
        recDict['altitudes'] = alts

        # If we have two sets of altitudes, they need to match
        if altVertDict[altList[0]] != altVertDict[altList[1]]:
            raise ex.AltitudesDontMatchException('Two sets of vertex altitudes do not match')
    else: 
        raise ex.TooManyAltitudesException('More than 2 altitudes in vertex list')

    recDict['coordinates'] = altVertDict[altList[0]]

def blockNumberToLatLong(blockNumber, scaleFactor):
    """Convert FIS-B block number to latitude and longitude.

    Note: *This function isn't used anymore given that
    we use the 'alternate block number', but it
    is still a good function to keep around.*

    Take FIS-B block number and convert to a latitude and
    a longitude (defined as the bottom left of the block).
    In the US, this translates to the SW corner of the block.

    Background: FIS-B divides the earth into block numbers.
    Each block contains a 4 by 32 array of bins. Blocks in the
    southern hemisphere are negative numbers and are positive
    numbers in the northern hemisphere. Blocks start at the
    equator and each level of latitude has 450 blocks. Blocks
    start at the prime meridian for longitude.

    To get the latitude, you divide the block number by 450 and
    take the integer part. Each row of bins is 1 arc minute
    (also 1 nautical mile) or
    1/60th of a degree. Since each block has 4 rows of bins, 
    multiply by 4 to get the total degrees of latitude in
    the block. When the above is multiplied by the integer part
    of the 'block number / 450', you get the latitude.

    For longitude, use the fractional portion of dividing the block
    by 450. This is the percentage around the earth the block is
    from the prime meridian. Multiply by 360 to get the number of
    degrees. If the number is > 180, subtract 360.

    Note: Above 60 degrees, the default block is 3 minutes in 
    longitudinal width. That really isn't relevant to us, because
    above this latitude, FIS-B will only give you even numbered
    blocks.

    The height and width of each block in degrees is also
    returned.

    Args:
        blockNumber (int): Block Number to decode
        scaleFactor (int): DO-358 scale factor (0 High, 1 Medium, 2 Low)

    Returns:
        tuple: Four element tuple containing:

        1. Latitude of the block number
        2. Longitude of the block number
        3. Height of each bin in degrees
        4. Width of each bin in degrees
    """
    (fracPart, intPart) = math.modf(blockNumber / 450.0)

    latitude = intPart * 4.0 * (1.0/60.0)

    longitude = fracPart * 360

    if longitude > 180.0:
        longitude = longitude - 360.0

    # High resolution
    if scaleFactor == 0:
        # 1 minute (NM)
        binHeight = 1.0/60.0

        if latitude < 60.0:
            # 1.5 minutes
            binWidth = 1.5/60.0
        else:
            # 3 minutes
            binWidth = 3.0/60.0
            
    # Medium resolution
    elif scaleFactor == 1:
        # 5 minutes (NM)
        binHeight = 5.0/60.0
        
        if latitude < 60.0:
            # 7.5 minutes
            binWidth = 7.5/60.0
        else:
            # 15 minutes
            binWidth = 15.0/60.0

    # Low resolution
    elif scaleFactor == 2:
        # 9 minutes (NM)
        binHeight = 9.0/60.0
        
        if latitude < 60.0:
            # 13.5 minutes
            binWidth = 13.5/60.0
        else:
            # 27 minutes
            binWidth = 27.0/60.0
    else:
        raise ex.ScaleFactorException('Illegal Scale factor')

    # Set consistent resolutions
    latitude = float(round(latitude, 6))
    longitude = float(round(longitude, 6))
    binHeight = float(round(binHeight, 6))
    binWidth = float(round(binWidth, 6))

    return (latitude, longitude, binHeight, binWidth)

def secondsToMMSS(secs):
    """Convert number of seconds to the string ``mm:ss``.

    Note: If the number of minutes is greater than 100, it will
    be displayed as such.

    Args:
        secs (int): Number of seconds.
    
    Returns
        str: String in the format of ``mm:ss``.
    """
    secs = int(secs)

    minutes, seconds = divmod(secs, 60)

    return '{:02d}:{:02d}'.format(minutes, seconds)

def twgoExpirationFacts(msg):
    """Used by :func:`twgoExpirationTime` to find latest stop time,
    and if all records have one.

    Finds the latest stop time in a message and also if all
    records have a stop time (if all records don't have a stop
    time, knowing the latest is moot).

    Args:
        msg (dict): Message to be evaluated.

    Returns:
        tuple: Tuple:

        1. (str) Latest stop time in the message. Will return
           ``None`` if there are no stop times in the message.
        2. (bool) ``True`` if all records have a stop time.
           Else ``False``.
    """
    latestStopTime = None
    allRecordsHaveStopTime = True

    if 'geometry' not in msg:
        return (latestStopTime, False)

    geoDicts = msg['geometry']

    for x in geoDicts:
        if 'stop_time' in x:
            if latestStopTime == None:
                latestStopTime = x['stop_time']
            elif x['stop_time'] > latestStopTime:
                # Bonus: ISO datetime sorts correctly as strings!
                latestStopTime = x['stop_time']
        else:
            allRecordsHaveStopTime = False

    return (latestStopTime, allRecordsHaveStopTime)

def twgoExpirationTime(msg, rcvdTime, notamExpirationTime=None):
    """Make a best guess to the expiration time for this message.

    TWGO messages have the requirement that they be sent for 60
    minutes after the last reception unless they have a stop
    time from the APDU header. However, there are cases where
    there is more than one record and thus more than one stop time.

    This routine will use the latest stop time if all
    the records have a stop time (not all records have a stop
    time). Otherwise it will use ``cfg.TWGO_DEFAULT_EXPIRATION_TIME``
    (usually set at 61 minutes).

    Test messages don't always follow this standard. For testing
    set ``cfg.BYPASS_TWGO_SMART_EXPIRATION`` to ``True`` to only
    expire ``cfg.TWGO_DEFAULT_EXPIRATION_TIME`` minutes after the
    last reception.

    In normal use, it's best to set ``cfg.BYPASS_TWGO_SMART_EXPIRATION``
    to ``False`` so that NOTAMs will use its expiration time if present.
    This is always the best time for NOTAMs. If the NOTAM's expiration time
    is ``PERM``, don't use it-- just use the default. If you do use it, you
    won't be able to tell when the system stops sending the message (which
    is one way the system expires messages if it doesn't outright cancel it).
    The routines processing NOTAMs follow this rule.

    Args:
        msg (dict): Message being evaluated. Needed to look at stop times.
        rcvdTime (str): ISO time the message was received.
        notamExpirationTime (str): ISO NOTAM expiration time.

    Returns:
        str: ISO expiration time to use.
    """
    if not cfg.BYPASS_TWGO_SMART_EXPIRATION:
        # If the NOTAM gives you an expiration time, just use it. It's the best and
        # in a multi-record message the latest expiration time will also be the
        # NOTAM expiration time. Don't use a PERM time here though.
        if notamExpirationTime is not None:
            return notamExpirationTime

        latestStopTime, allRecordsHaveStopTime = twgoExpirationFacts(msg)

        # Simple case: all records have stop time, use the latest
        if allRecordsHaveStopTime:
            return latestStopTime

    # Otherwise use default value added to received time
    return addMinutesToIso8601(rcvdTime, cfg.TWGO_DEFAULT_EXPIRATION_TIME)

CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

CHARS_LEN_MINUS_1 = len(CHARS) - 1

def randomname(length, postfix = ''):
    """Create a random name of the specified length, add a postfix string
    if desired.

    Random name is created from the string in ``CHAR`` which consists of
    upper and lower alphabetic characters and digits. Mostly, this routine
    is used for creating filenames.

    Args:
        length (int): Number of characters to generate.
        postfix (str): String to append to the end. Usually an extension
            like ``'.png'``

    Returns:
        str: Random string with any ``postfix`` added to it.
    """
    name = ''
    for _ in range(0, length):
        name += CHARS[random.randint(0, CHARS_LEN_MINUS_1)]
    
    return name + postfix
