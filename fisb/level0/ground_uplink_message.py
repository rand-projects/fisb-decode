"""Decodes a single Ground Uplink Message.

Parses, as much as is possible, a ground uplink message from
dump978-fa (`FlightAware version <https://github.com/flightaware/dump978>`_)
and returns it as a Python dictionary. You need to use the FlightAware
version as the older original version has a different output format.

Based on the DO-358B Draft standard.

No special processing of incomplete segmented messages, or determining
the actual times of products (other than what is in the APDU
header) is done. This is just what they sent, the way they
sent it. Any exceptions to this are documented in the code.
The completed object is expected to be sent
through additional layers to reconstruct messages,
store things in a database, determine actual message times, etc.
"""

import time, pprint
import json
import sys
import fisb.level0.level0Config as cfg
import fisb.level0.level0Exceptions as ex
import fisb.level0.utilities as util
from datetime import timezone, datetime, timedelta
from fisb.level0.service_status_frame import decodeServiceStatusFrame
from fisb.level0.reserved_frame import decodeReservedFrame
from fisb.level0.apdu_frame import decodeApduFrame
from fisb.level0.crl_frame import decodeCrlFrame

# Only import if harvest requirements are installed.
if cfg.ALLOW_DECODE_TEST:
    import db.harvest.testing as test

DIGIT_TO_HEX = '0123456789ABCDEF'

# Lookup for the kind of FIS-B station we are.
# There are 4 levels:
#               Floor           Ceiling         Power
#               -------         -------        -------
#   Surface     surface         surface           N/D
#   Low         0               3050  ft AGL     7-18W
#   Medium      surface         13800 ft AGL    16-40W
#   High        surface         FL240 ft AGL   100-250W
#
# Appendix D in DO-358B contains more information on tiering.
# The look-ahead of the various levels are found in Table 7-1-2
# of the AIM. This appendix implies no surface tiers
# are in use, but other data shows otherwise.
#
# Value of 0 implies no TIS-B information transmitted. See
# ACP-WGW01-WP08-R1-UAT Tech Manual.
TISB_TIER_LOOKUP = ["NO-TISB", "S4", "S3", "S2", "S1", "L5", "L4", \
                    "L3", "L2", "L1", "M3", "M2", "M1", "H3", \
                    "H2", "H1"]

def calculateRSR(rsrDict, timeInSecs, ba7, station):
    """Calculate current *Reception Success Rate* (RSR) and store it in the database.

    Operates according to the following configuration values:

    - ``cfg.RSR_CALCULATE_OVER_X_SECS`` Use 10 to follow standard. 

    - ``cfg.RSR_CALCULATE_EVERY_X_SECS`` Use 1 to follow the standard. Otherwise set
      this value and ``cfg.RSR_CALCULATE_OVER_X_SECS`` to the number of seconds
      you are checking for updates.

    - ``cfg.RSR_USE_EXPECTED_PACKET COUNT`` ``False`` to follow the standard. ``True``
      will get you a more accurate result (but not when using the test data-- its 
      rigged). The expected packet count comes from the type of station this is
      (encoded in the message header). High power stations send 4 messages a second,
      medium stations send 3 messages a second, low power stations send 2 messages
      a second, etc.

    RSR is done on a *per station* basis. That is, there is a separate RSR for each
    station.

    Args:
        rsrDict (dict): Dictionary with current state information about RSR (including
          current states and the database connection).
        timeInSecs (int): Current message time in seconds.
        ba7 (byte): Byte from raw message with info about station type.
        station (str): Station sending the message.
    """
    # Current time for this message
    cursec = int(timeInSecs)

    # Get timeDict
    timeDict = rsrDict['time_dict']
    totalSecs = rsrDict['total_secs']

    rsrDict['cur_sec'] = cursec

    if (cursec > rsrDict['last_sec']):
        # Do RSR only if we have a minimal number of seconds of data
        if (totalSecs > cfg.RSR_CALCULATE_OVER_X_SECS) and \
            ((totalSecs % cfg.RSR_CALCULATE_EVERY_X_SECS) == 0):

            # Each key is a station. The value is a list
            # of 3 items of the form: [0] total count, [1]
            # max expected count per second, [2] calculated RSR
            resultDict = {}

            # calculate the rsr on the last required number of seconds
            for i in range(cursec-1, cursec-(cfg.RSR_CALCULATE_OVER_X_SECS + 1), -1):
                if i in timeDict:
                    stationsInTimeDict = list(timeDict[i].keys())
                    for stationX in stationsInTimeDict:
                        packetCnt = timeDict[i][stationX]
                        if stationX in resultDict:
                            stationList = resultDict[stationX]
                            stationList[0] = stationList[0] + packetCnt

                            # We can either use the actual max packets per second
                            # or easily determine this from the message.
                            if cfg.RSR_USE_EXPECTED_PACKET_COUNT:
                                stationList[1] = expectedPacketsPerSecond(ba7)
                            elif packetCnt > stationList[1]:
                                stationList[1] = packetCnt
                            resultDict[stationX] = stationList
                        else:
                            resultDict[stationX] = [packetCnt, packetCnt, 0]

            # resultDict is complete. Go through and calculate RSR
            resultDictKeys = list(resultDict.keys())
            for i in resultDictKeys:
                stationList = resultDict[i]
                stationList[2] = round((stationList[0] / \
                    (stationList[1] * float(cfg.RSR_CALCULATE_OVER_X_SECS))) * 100.0)

            # Calculate expiration time which is the the time now plus
            # cfg.RSR_CALCULATE_EVERY_X_SECS + 10 seconds.
            # NOTE: For testing, we can't possibly know the test offset
            # so the expiration time will be way in the future (or for one
            # test where it doesn't matter-- possibly in the past). For real time
            # having an expiration time is nice since if the signal goes
            # away, the RSR will be removed.
            # insert_time is also only in the present (not reflected back in past for
            # tests). This doesn't affect anything.
            utcNow = datetime.utcnow()
            utcExpire = utcNow + timedelta(0, cfg.RSR_CALCULATE_EVERY_X_SECS + 10)

            msg = {'_id': 'RSR-RSR', \
                'type': 'RSR', \
                'unique_name': 'RSR', \
                'stations': resultDict, \
                'insert_time': utcNow, \
                'expiration_time': utcExpire}

            # Store in database
            rsrDict['db'].MSG.replace_one({'_id': 'RSR-RSR'}, \
                msg, \
                upsert=True)

        rsrDict['last_sec'] = cursec

        # cleanout old entries
        timeDictKeys = list(timeDict.keys())
        if len(timeDictKeys) > (cfg.RSR_CALCULATE_OVER_X_SECS + 2):
            for x in timeDictKeys:
                if x < (cursec - (cfg.RSR_CALCULATE_OVER_X_SECS + 2)):
                    del timeDict[x]

        # update total_sec
        rsrDict['total_secs'] = totalSecs + 1

    # update dictionary
    if cursec in timeDict:
        if station in timeDict[cursec]:
            cnt = timeDict[cursec][station]
            cnt += 1
            timeDict[cursec][station] = cnt
        else:
            timeDict[cursec][station] = 1
    else:
        timeDict[cursec] = {station: 1}

def groundUplinkMessage(payload, isDetailed, testMode, rsrDict = None):
    """Process a ground uplink message.

    Take a string from FlightAware's dump978 and parse it into a dictionary
    representing its contents.

    Calling with ``isDetailed`` equal to ``False`` will create
    a normal object with all fields needed for normal FIS-B use.
    Setting this to ``True`` decodes items not normally needed or useful,
    but helpful for understanding the entire contents of a message
    (like all the reserved bits).

    Args:
        payload (str): Contains a single line of a Ground Uplink message from 
            dump978-fa. This line starts with a '+'.
            ADS-B messages (these begin with '-') should be filtered
            out before calling groundUplinkMessage.
        isDetailed (bool): ``True`` if a full blown decoded is to be done. ``False``
            is normal decoding for the usual FIS-B products. Detailed
            decodes include unused fields, full Ground Uplink header
            decoding, UAT TIS-B/ADS-R Service Status Management Message
            decoding, etc. Useful for exploring everything in the message.
        testMode (bool): True is in 'test' mode (dump test groups), Else False.
        rsrDict (dict): Pass this in if using RSR. This contains state information
            used for computing RSRs.

    Returns:
        dict: Decoded message as a dictionary.

    Raises:
        GroundUplinkLengthException: Malformed message. Not 432 bytes.
    """
    # Dictionary to hold all message results
    d = {}
    
    # Records must start with '+'. These records come from dump978
    # by FlightAware and contain a time value at the end.
    # Dump978 also uses '-' for UAT ADS-B messages, but those messages
    # should be filtered out before attempting to process a
    # Ground uplink message.
    
    # Extract the data and convert the hex to a byte array
    semiColonIndex = payload.index(';')

    # Time the message was received from the base station. This is use
    # as an estimate for the message transmitted time. It is usually
    # added by addUTC.py
    #
    # It's importance comes in level2 if we are replaying messages
    # for debugging and testing. It is used to make complete ISO-8601
    # times from FAA time strings that only have day or month and hour.
    #
    # Time is converted into an ISO-8601 string
    # Find and extract the time value from the message (this is
    # encoded at the end of the message in a t=<time.ms> string)
    payloadTimeIndex = payload.find(';t=')

    # Usual case is we have the received time in the string. But if
    # not, use current time.
    if payloadTimeIndex == -1:
        timeInSecs = time.time()
    else:
        timeInSecs = float(payload[payloadTimeIndex + 3:-1])

    dtTime = datetime.fromtimestamp(timeInSecs, tz=timezone.utc)

    d['rcvd_time'] = dtTime.__format__('%Y-%m-%dT%H:%M:%S') +\
        '.{:03}Z'.format(int((timeInSecs % 1) * 1000))
    
    if testMode:
        # See if any dump needs to be printed
        util.checkForTrigger(timeInSecs)

        # If in test mode print packet arrival time.        
        x = '#-----------------------------------------------------------' + \
            '\n# PACKET: {}\n#'
        print(x.format(d['rcvd_time']), flush=True)
    
    # Uncomment the below line to print the received time
    # as each packet arrives. Useful as a quick check for
    # how many packets you are getting every second and
    # radio reception quality.
    #sys.stderr.write(d['rcvd_time'] + '\n')
    
    payload = payload[1:semiColonIndex]

    # Create byte array containing entire message.
    ba = bytes.fromhex(payload)

    # Each payload has 432 bytes. Generate an error if that is
    # not correct. All messages (should) come zero padded to that length.
    if len(ba) != 432:
        raise ex.GroundUplinkLengthException('Expected 432 bytes, got {}'.\
                                          format(len(ba)))
        
    # The ground uplink message consists of an 8 byte header with
    # the rest of the bytes being 0 to n UAT frames.
    
    # Unpack data from the header

    # app_data_valid is set to 1 if this is a valid operational
    # message. Else 0. Used for testing of new products.
    # Message should be ignored if this is 0.
    d['app_data_valid'] = (ba[6] & 0x20) >> 5

    # This was finally addressed in DO-358B.
    # If it represents a 1, the position is VALID. If 0, the 
    # position is INVALID. However, as of pre DO-358B adoption,
    # this is currently always sent as 0. Messages are supposed
    # to now ignore messages set to INVALID. I am ignoring this
    # for now, because 0 is always sent in this field. I have inspected
    # FIS-B messages from other sites and have also found that is
    # field is zero (have never seen it a one). This was
    # rechecked when DO-358B went into service, and
    # 'position_valid' is always set to zero at my site. It is
    # being ignored for now.
    d['position_valid'] = ba[5] & 0x01

    rawLatitude = (ba[0] << 15) | (ba[1] << 7) | \
                  (ba[2] >> 1)
    rawLongitude = ((ba[2] & 0x01) << 23) | \
                   (ba[3] << 15) | \
                   (ba[4] << 7) | (ba[5] >> 1)

    # Get longitude and latitude of station for making station name
    longitude, latitude = util.convertRawLongitudeLatitude(rawLongitude, \
                                                           rawLatitude, \
                                                           util.GEO_24_BITS)
    station = util.createStationName(longitude, latitude)
    d['station'] = station

    # Calculate RSR (Reception Success Rate) if desired
    if cfg.CALCULATE_RSR:
        calculateRSR(rsrDict, timeInSecs, ba[7], station)

    if isDetailed:
        # Longitude and Latitude of the sending station.
        # A useful link for finding FIS-B station locations is:
        #  http://towers.stratux.me
        #
        # Older, but useful:
        #  https://www.faa.gov/foia/electronic_reading_room/media/ADS-B_Ground_Stations_as_of_08-31-2018.pdf
        #
        d['longitude'] = longitude
        d['latitude'] = latitude
            
        # utc_coupled is true if the ground station's 1 PPS timing
        # is valid. Set to 1 if VALID, 0 if INVALID. Per the standard,
        # if the PPS is invalid, the message won't be transmitted, so
        # should always be 1.
        d['utc_coupled'] = (ba[6] & 0x80) >> 7

        # Transmission slot id defines the range of message start
        # opportunities (MSO). Adding 1 to slot_id gives you
        # the Transmission Time Slot ('transmission_time_slot')
        slot_id = ba[6] & 0x1F

        # Transmission time slot is a number from 1-32 which is where in the
        # ground segment portion of the message this data was transmitted. It is
        # the 'slot_id' + 1.
        d['transmission_time_slot'] = slot_id + 1

        # Message Start Opportunity (mso) is one of 3951 slices of a second
        # that a message will be transmitted at. FIS-B messages use MSOs 0
        # through 703. MSO 0 starts at 6ms after the UTC second. Each MSO
        # is 0.25 ms (250 us) long. Therefore, each FIS-B message gets 5.5 ms
        # of transmit time (22 MSOs). A typical ground uplink message is
        # 4 ms in length (so there is some clear space between slots).
        d['mso'] = slot_id * 22

        # This is the time in ms after the start of the UTC second that
        # the message was transmitted at.
        d['mso_utc_ms'] = (d['mso'] * 0.25) + 6.0

        # Data channel
        # Each second, a station will broadcast multiple data packets
        # in each 1 second frame. High power stations will send
        # 4 packets (1688 bytes), Medium power 3 (1266 bytes),
        # and Low power 2 (844 bytes). Even if there is no
        # data to transmit, an empty packet will be sent.
        #
        # What data channels are used is tied to the tisb_site_id.
        # A collection of data channels for a TIS-B site ID is called
        # a Data Channel Block (DCB).
        #
        # This table is taken from SBS-Description SRT-047-rev05 11/20/2020.
        # Way too long URL is split below. Rejoin the parts to use it:
        # "https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgTSO.nsf/0/
        # 45845cd583ad3cd686257d62006b3b3e/$FILE/MA%20SBS%20Description%20
        # Document%20SRT-047_V5_DCR-PMO-211_11202020signed18DEC20.pdf"
        #
        #  H1 (15-F) : 1, 9, 17, 25
        #  H2 (14-E) : 2, 10, 18, 26
        #  H3 (13-D) : 3, 11, 19, 27
        #  M1 (12-C) : 4, 12, 20
        #  M2 (11-B) : 5, 13, 28
        #  M3 (10-A) : 6, 21, 29
        #  L1 (09-9) : 14, 22
        #  L2 (08-8) : 7, 30
        #  L3 (07-7) : 15, 23
        #  L4 (06-6) : 16, 31
        #  L5 (05-5) : 8, 24
        #  S1 (04-4) : 32
        #  S2 (03-3) : 8
        #  S3 (02-2) : 16
        #  S4 (01-1) : 24
        #  Unallocated: 0
        #
        # There is a relationship between transmission time slot and
        # data channel, but they are not the same. See DO-358B Appendix G,
        # or (better) ICAO Doc 9861 for an explanation.
        #
        # We also don't handle leap seconds. How to do this
        # is documented in DO-358B.
        #
        # If we are not dealing with an accurate time, don't try to calculate
        # the data channel.
        if payloadTimeIndex != -1:
            # Get time in seconds past midnight (for data channel determination)
            secsPastMidnightMod32 = int((dtTime - dtTime.replace(hour=0, minute=0,\
                second=0)).total_seconds()) % 32

            dataChannel0Based = slot_id - secsPastMidnightMod32

            if dataChannel0Based < 0:
                dataChannel0Based += 32
            
            d['data_channel'] = dataChannel0Based + 1

        # Defines the FIS-B Tier for this station. This also implies
        # the look ahead range for many products.
        # Not required to be processed by the standard.
        #
        # FAA denoted this as a hex digit.
        tisbId = (ba[7] & 0xF0) >> 4
        d['tisb_site_id'] = DIGIT_TO_HEX[tisbId]

        d['tisb_site_id_type'] = TISB_TIER_LOOKUP[tisbId]

        # Reserved bit 2 in Ground uplink header byte 7
        d['reserved_7_2'] = (ba[6] & 0x40) >> 6

        # Reserved bits 5-8 in Ground uplink header byte 8
        d['reserved_8_58'] = ba[7] & 0x0F

    # Now examine the rest of the frame data for frames
    currentOffset = 8
        
    # Will contain all the frames in this message
    frameList = []

    # Loop for each frame in the message and add it to the framelist
    # after processing
    while True:
        # Reached end of full packet
        if (currentOffset >= 431):
            break

        frameLength = (ba[currentOffset] << 1) | \
                      ((ba[currentOffset + 1] & 0x80) >> 7)

        # If frameLength is zero, we are done
        if (frameLength == 0):
            break

        reserved_2_24 = (ba[currentOffset + 1] & 0x70) >> 4

        # Get frame type and process based on that
        frameType = ba[currentOffset + 1] & 0x0F

        # There are only 4 frames of interest:
        #   00 - APDU
        #   14 - CRL
        #   15 - TIS-B/ADS-R Service Status (only if isDetailed set)
        #   ?? - All the reserved frames (only if isDetailed set)
        #
        # Add a new object of the specified type to the frameList.
        #
        if frameType == 0:
            apduFrame = decodeApduFrame(ba[currentOffset + 2: \
                                           currentOffset + 2 + \
                                           frameLength], \
                                           frameLength, \
                                           reserved_2_24, \
                                           isDetailed)

            # Skip if we are blocking a product type (such as SUA)
            if apduFrame is not None:
                frameList.append(apduFrame)

        # CRL
        elif frameType == 14:
            frameList.append(decodeCrlFrame(ba[currentOffset + 2: \
                                                     currentOffset + 2 + \
                                                     frameLength], \
                                                     frameLength, \
                                                     reserved_2_24, \
                                                     isDetailed))

        # Service Status Frames
        elif cfg.ALLOW_SERVICE_STATUS and (frameType == 15):
            frameList.append(decodeServiceStatusFrame\
                             (ba[currentOffset + 2: \
                                 currentOffset + 2 + \
                                 frameLength], \
                                 frameLength, \
                                 reserved_2_24, \
                              isDetailed))

        # Unknown frames
        else:
            if isDetailed:
                frameList.append(decodeReservedFrame\
                                 (ba[currentOffset + 2: \
                                           currentOffset + 2 + \
                                           frameLength], \
                                           frameLength, \
                                           reserved_2_24, \
                                           frameType))

        currentOffset += frameLength + 2

    d['frames'] = frameList

    if len(frameList) == 0:
        if cfg.SKIP_EMPTY_FRAMES:
            return None

    return d

def expectedPacketsPerSecond(ba7):
    """Return the expected number of packets per second we can get from this station.

    Args:
       ba7 (byte): Holds encoded information about the class of station this is. That directly
                   translates into the number of packets per second that get sent.

    Returns:
       int: Number of packets per second.
    """
    tisbId = (ba7 & 0xF0) >> 4

    if tisbId >= 13:
        return 4
    elif tisbId >= 10:
        return 3
    elif tisbId >= 5:
        return 2
    else:
        return 1
