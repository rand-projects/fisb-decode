"""Decode and create messages from 413 (DLAC Text) frames.

The following messages are produced from 413 frames:

* METAR
* TAF
* WINDS_06_HR
* WINDS_12_HR
* WINDS_24_HR
* PIREP
"""

import sys, os, json, time, re

import fisb.level2.level2Config as cfg
import fisb.level2.utilities as util
import fisb.level2.level2Exceptions as ex

# Parse PIREP
PIREP_RE = re.compile('^(PIREP) ([^ ]+) ([0-9]{6})Z ([^ ]+) (UA|UUA) (.+)')

# Valid PIREP fields. Note the space after /OV. This helps prevents a 
# bad parse when someone uses '/OVC' in a remark or something.
PIREP_FIELDS_FROM = ['/OV ', '/TM', '/FL', '/TP', '/TB', '/SK', '/RM',\
     '/WX', '/TA', '/WV', '/IC']
PIREP_FIELDS_TO = ['~OV', '~TM', '~FL', '~TP', '~TB', '~SK', '~RM',\
     '~WX', '~TA', '~WV', '~IC']

# Parse METAR location and time
METAR_RE = re.compile('^(METAR|SPECI) ([0-9A-Z]{4}) ([0-9]{6})')

# Parse WINDS location and valid time
WINDS_RE = re.compile('^(WINDS) ([0-9A-Z]{3}) ([0-9]{6})Z')

# Parse TAF location and time
TAF_RE = re.compile('^(TAF|TAF\\.AMD|TAF COR) ([0-9A-Z]{4}) ([0-9]{6})Z ([0-9]{4})/([0-9]{4})')

# Some TAF doesn't have a Zulu time (i.e. TAF KNSE 1815/1915 ...)
# These seem to be peculiar to Naval Air Stations.
TAF_RE_NO_Z_TIME = re.compile('^(TAF|TAF\\.AMD|TAF COR) ([0-9A-Z]{4}) ([0-9]{4})/([0-9]{4})')

# WIND_MATRIX determines type of forecast based on the
# product available time (APDU) vs valid time (message)
#
#   Prod Avail | 0600  1200  1800  0000  <-- Valid Times
#  +-----------+-----------------------+
#  |   0200    |   6    12    NA    24 |
#  |   0800    |  24     6    12    NA |
#  |   1400    |  NA    24     6    12 |
#  |   2000    |  12    NA    24     6 |
#  +-----------+-----------------------+
#
WIND_MATRIX = [[6, 12, -1, 24], \
               [24, 6, 12, -1], \
               [-1, 24, 6, 12], \
               [12, -1, 24, 6]]


def msg413(frame, rYear, rMonth, rDay, rHour, rMin, \
           hour, minute, rcvdTime):
    """Dispatch 413 text messages for appropriate processing

    Args:
        frame (dict): Frame with 413 message.
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        hour (int): APDU hour.
        minute (int): APDU minute.
        rcvdTime (str): Message received in ISO format.
    
    Returns:
        dict: Dictionary with completed message.

    Raises:
        Unknown413MessageTypeException: If we are handed some text
            we can't decode.
    """

    # FAA text is full of trailing whitespace. Get rid of it.
    contents = util.cleanFAAText(frame['contents'])

    # If a message isn't handled, will return None and be skipped over.
    # Otherwise, holds returned dictionary.
    newMsg = None

    # Dispatch based on type
    if contents.startswith('METAR') or \
       contents.startswith('SPECI'):
        newMsg = metar(contents, rYear, rMonth, rDay)
    elif contents.startswith('TAF'):
        newMsg = taf(contents, rYear, rMonth, rDay)
    elif contents.startswith('WINDS'):
        newMsg = winds(contents, rYear, rMonth, rDay, \
                        hour, minute)
    elif contents.startswith('PIREP'):
        newMsg = pirep(contents, rYear, rMonth, rDay, rcvdTime)
    else:
        raise ex.Unknown413MessageTypeException("Got unknown 413 message: '{}'".format(contents))

    return newMsg
    
def pirep(contents, rYear, rMonth, rDay, rcvdTime):
    """Process and returns a PIREP message.

    PIREP messages basically just take the PIREP and break it into
    its components and use the components as a key (like 'OV', 'RM',
    'FL', etc).

    It should be noted that the FIS-B PIREP report has the form: ::

        PIREP XXX ddhhmmZ yyy UA...
    
    Where 'XXX' is the navigation aid or airport referenced in the
    'OV' portion (total garbage, see below), and 'yyy' is the standard weather reporting location.
    The ``XXX`` location in the message is totally made up by the
    FIS-B producer (not the FAA).
    Do not trust it, do not use it-- it's made up garbage.
    FIS-B takes the ``/OV`` field and makes
    ``XXX`` up. Examples: ``/OV INT 3N`` becomes ``INTN``, ``/OV B NA315040``
    becomes ``NA3``, ``/OV 7KM SE`` becomes ``7KMSE``,
    ``/OV WITHIN 20 MILES CLE`` becomes ``WITHINMILESCLE``. ``/OV 2 E OF FIELD``
    becomes ``FIELD``. You get the picture: never use ``XXX`` from
    a PIREP.

    The hour and minute from 'ddhhmmZ' is taken from the 'TM' component.

    There is no latitude and longitude associated with the PIREP at this level.
    Harvest has an option where it will attempt to decode the ``/OV`` field
    and find a location for it. It's not always easy to do. While there is a
    well defined format as to what should be in this field, it is a hand
    entered field and is subject to total weirdness.

    Args:
        contents (str): Contents of the 413 text field.
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.

    Returns:
        dict: Dictionary with completed PIREP message.

    Raises:
        RegexDidNotMatchException: If the PIREP didn't match the template.
        PirepFieldTooSmallException: If the PIREP field length was too short.
    """
    parsed = PIREP_RE.match(contents)

    # PIREPs have some human input so are more prone to errors
    if parsed == None:
        raise ex.RegexDidNotMatchException('PIREP did not match template.')

    newMsg = {}
    newMsg['type'] = 'PIREP'
    newMsg['unique_name'] = parsed.group(5) + parsed.group(4) +\
            parsed.group(6).replace(" ", "")
    newMsg['report_type'] = parsed.group(5)
    newMsg['station'] = parsed.group(4)
    newMsg['contents'] = contents
    
    # Go through the actual report portion and divide into fields.
    # Note that fields are things like /OV, but that a slash is can also
    # be used in the contents of a field, so we must first replace field
    # names like /OV with ~OV and then split those.
    fieldsDefined = parsed.group(6)

    for idx, fieldName in enumerate(PIREP_FIELDS_FROM):
        if fieldName in fieldsDefined:
            fieldsDefined = fieldsDefined.replace(fieldName, PIREP_FIELDS_TO[idx])

    fields = fieldsDefined.split('~')
    
    for x in fields:
        x = x.strip()

        # The first '~' always generates a '' field. Just skip it.
        if x == '':
            continue

        # Field names are always 2 characters, so string needs at least this
        # length
        if len(x) < 2:
            raise ex.PirepFieldTooSmallException('PIREP field length too short')

        fieldName = x[0:2].lower()
        fieldContents = x[2:].strip()

        newMsg[fieldName] = fieldContents

    reportTime = util.dayHourMinToIso8601(rYear, rMonth, rDay, parsed.group(3))    
    newMsg['report_time'] = reportTime

    # Basing the expiration off the report time is the better option here,
    # but the standard mandates at least 75 minutes from last reception
    if cfg.PIREP_USE_REPORT_TIME_TO_EXPIRE:
        newMsg['expiration_time'] = util.addMinutesToIso8601(reportTime, \
                                                         cfg.PIREP_EXPIRATION_MINUTES)
    else:
        newMsg['expiration_time'] = util.addMinutesToIso8601(rcvdTime, \
                                                         cfg.PIREP_EXPIRATION_MINUTES)
    return newMsg

def metar(contents, rYear, rMonth, rDay):
    """Process and return new METAR message.

    Args:
        contents (dict): Contents of the 413 text field.
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.

    Returns:
        dict: Dictionary with completed METAR message.
    """
    # Returned message
    newMsg = {}

    parsed = METAR_RE.match(contents)
    location = parsed.group(2)

    newMsg['type'] = 'METAR'
    newMsg['unique_name'] = location
    newMsg['location'] = location
    newMsg['contents'] = contents

    observationTime = util.dayHourMinToIso8601(rYear, rMonth, rDay, parsed.group(3))
    newMsg['observation_time'] = observationTime

    # Add time to observation time based-on configuration parameter to
    # create expiration time.
    newMsg['expiration_time'] = util.addMinutesToIso8601(observationTime, \
                                                         cfg.METAR_EXPIRATION_MINUTES)
    return newMsg

def taf(contents, rYear, rMonth, rDay):
    """Process and return new TAF message.

    Note: TAFs from Naval Air Stations use a different format that doesn't
    have a Zulu time in the usual place. We detect that, and use the 
    ``valid_period_begin_time`` as the issued_time.

    Args:
        contents (str): Contents of the 413 text field.
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.

    Returns:
        dict: Dictionary with completed TAF message.

    Raises:
        RegexDidNotMatchException: If the TAF did not match any template.
    """
    newMsg = {}

    # Handles normal TAF except for Naval Air Stations.
    parsed = TAF_RE.match(contents)

    if not parsed:
        # Naval Air Stations don't have normal issued_time Zulu time
        parsed = TAF_RE_NO_Z_TIME.match(contents)

        # if everything fails
        if not parsed:
            raise ex.RegexDidNotMatchException('TAF did not match any template.')

        issuedTimeGroup = 3
        validPeriodBeginGroup = 3
        validPeriodEndGroup = 4

    else:
        issuedTimeGroup = 3
        validPeriodBeginGroup = 4
        validPeriodEndGroup = 5
        
    location = parsed.group(2)

    newMsg['type'] = 'TAF'
    newMsg['unique_name'] = location
    newMsg['location'] = location
    newMsg['issued_time'] = util.dayHourMinToIso8601(rYear, rMonth, rDay,\
        parsed.group(issuedTimeGroup))
    newMsg['valid_period_begin_time'] = util.dayHourMinToIso8601(rYear, rMonth, rDay,\
        parsed.group(validPeriodBeginGroup))

    validPeriodEnd = util.dayHourMinToIso8601(rYear, rMonth, rDay,\
        parsed.group(validPeriodEndGroup))

    newMsg['valid_period_end_time'] = validPeriodEnd

    newMsg['contents'] = contents

    # Expiration time is when the valid period is over.
    newMsg['expiration_time'] = validPeriodEnd
    
    return newMsg

def winds(contents, rYear, rMonth, rDay, hour, minute):
    """Process and return new winds message.

    Producing the winds aloft forecast is crazy. It's like a puzzle from
    a Nancy Drew game. Instead of just telling you what forecast they sent you,
    you are made to deduce it from sparse clues.

    Your only clues are two times: 'Valid Time' in the message and 'Product Available Time'
    in the APDU header (hour and minute only). Helpful is table A-9 in DO-358B
    which provides a matrix view of what forecast is implied by the various times.
    
    The 'Valid Time' is always exact, and the APDU time ('Product
    Available Time') is usually off plus or minus a few minutes from the expected time.
    However, we can pick the correct 'Product Available Time' categories by estimation.

    Given the 'Product Available Time' and 'Valid Time', we use a matrix (``WIND_MATRIX``) to
    lookup the forecast type (6, 12, or 24 hours).

    After that, we base all other calculations on 'Valid Time' (because it is the
    only date with a day). We can calculate all other times off of it. At the very end
    we change the 'Product Availabile Time' to the exact value sent by APDU.
    
    FIS-B sends a header of altitude values for each winds aloft report. We get rid of
    it and only return the wind values. Header line is easy enough to put back later.

    Args:
        contents (text): Contents of the 413 text field.
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        hour (int): APDU hour.
        minute (int): APDU day.

    Returns:
        dict: Dictionary with completed message.

    Raises:
        IllegalWindProductException: If we get a forecast we aren't expecting.
    """
    newMsg = {}

    parsed = WINDS_RE.match(contents)
    location = parsed.group(2)
    validTime = parsed.group(3)

    # Contents have useless header line not needed after decoding
    # location and time. Remove it.
    contentsSplit = contents.split('\n')
    contents = contentsSplit[1].rstrip()

    # To figure out what type of forecast we are, we need to know
    # the product available time and the valid time. The product
    # available time is often not exact. The valid time is always
    # exact. The times are used to create indices that form an
    # index to WIND_MATRIX to determine what exact forecast (6, 12
    # or 24) this is.

    # First, figure out the product available time from
    # the APDU
    if (hour >= 1) and (hour < 3):     # 0200
        paIdx = 0
    elif (hour >= 7) and (hour < 9):   # 0800
        paIdx = 1
    elif (hour >= 13) and (hour < 15): # 1400
        paIdx = 2
    elif (hour >= 19) and (hour < 21): # 2000
        paIdx = 3
    else:
        raise ex.IllegalWindProductException("Hour of {} isn't valid.".format(hour))

    # Now figure out the valid time from the message.
    vTimeInt = int(validTime[2:])

    if vTimeInt == 600:
        vtIdx = 0
    elif vTimeInt == 1200:
        vtIdx = 1
    elif vTimeInt == 1800:
        vtIdx = 2
    elif vTimeInt == 0:
        vtIdx = 3
    else:
        raise ex.IllegalWindProductException("Valid time of {} isn't legal.".format(validTime))

    # Now try to match the prodAvail time with valid time to get
    # the forecast type.
    # Will return 6, 12, or 24 depending on type of forecast. -1 for illegal cases.
    product = WIND_MATRIX[paIdx][vtIdx]

    if product == -1:
        raise ex.IllegalWindProductException("Illegal Product Matrix values: {} {}.".format(paIdx, vtIdx))

    # The basic strategy is to start with the valid time. It is the
    # only one with a day. If we know that, and what forecast we are
    # dealing with, we can compute the other times.
    validTimeIsoStr = util.dayHourMinToIso8601(rYear, rMonth, rDay, validTime) 

    if product == 6:
        prodAvailIsoStr = util.addHoursToIso8601(validTimeIsoStr, -4)
        modelRunIsoStr = util.addHoursToIso8601(validTimeIsoStr, -6)
        forUseBegin = util.addHoursToIso8601(validTimeIsoStr, -4)
        forUseEnd = util.addHoursToIso8601(validTimeIsoStr, 3)
        prodName = 'WINDS_06_HR'
    elif product == 12:
        prodAvailIsoStr = util.addHoursToIso8601(validTimeIsoStr, -10)
        modelRunIsoStr = util.addHoursToIso8601(validTimeIsoStr, -12)
        forUseBegin = util.addHoursToIso8601(validTimeIsoStr, -3)
        forUseEnd = util.addHoursToIso8601(validTimeIsoStr, 6)
        prodName = 'WINDS_12_HR'
    elif product == 24:
        prodAvailIsoStr = util.addHoursToIso8601(validTimeIsoStr, -22)
        modelRunIsoStr = util.addHoursToIso8601(validTimeIsoStr, -24)
        forUseBegin = util.addHoursToIso8601(validTimeIsoStr, -6)
        forUseEnd = util.addHoursToIso8601(validTimeIsoStr, 6)
        prodName = 'WINDS_24_HR'
    else:
        raise ex.IllegalWindProductException("Illegal Product value: {}".format(product))        

    # Just to be accurate, we calculated the product available time from valid time.
    # Now go back and put the actual time from APDU back in. It's only
    # off a small amount and won't affect the day of the month (because
    # products aren't made available near 0000Z).
    prodAvailIsoStr = prodAvailIsoStr[0:11] + \
                      '{:02d}:{:02d}'.format(hour, minute) + \
                      prodAvailIsoStr[16:]

    newMsg['type'] = prodName
    newMsg['unique_name'] = location
    newMsg['location'] = location

    newMsg['issued_time'] = prodAvailIsoStr
    newMsg['valid_time'] = validTimeIsoStr
    newMsg['for_use_from_time'] = forUseBegin
    newMsg['for_use_to_time'] = forUseEnd
    newMsg['contents'] = contents
    newMsg['model_run_time'] = modelRunIsoStr

    if prodName == 'WINDS_06_HR':
        # Standard states you have to keep the last 6 hour wind around 
        # until the next one comes in. So we just add a day to the
        # 'forUseEnd' time. Other WIND forecast times don't have this requirement.
        newMsg['expiration_time'] = util.addDaysToIso8601(forUseEnd, 1)
    else:
        newMsg['expiration_time'] = forUseEnd    

    return newMsg
