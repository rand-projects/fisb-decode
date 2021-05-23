"""Contains a ServiceStatus frame.

Service Status frames holds the aircraft currently being tracked by
UAT ADS-B (i.e. the planes that get a hockey puck).

Originally, information for this section was based on
*SRT-047 Rev 01 (2011) section 3.3.4.1.2*. This seems to be accurate.

Currently, information is based on Doc 9861 AN/460 '*Manual on the Universal
Access Transceiver (UAT)*'.

This data is typically sent out every 20 seconds. Each message may have
different aircraft listed. This implies that you simply can't replace
one message with another-- you need to keep track of each aircraft and
expire the entry if it is not refreshed. 40 seconds seems to be a reasonable
expiration time.

Each frame is 4 bytes long:

====== ========================================
 BYTE  VALUE
 [0]   ttttsqqq
        t = reserved

        s = SIGNAL_TYPE (always 1)

        q = address qualifier

          - 0 ICAO aircraft address broadcasting ADS-B msg.
          - 1 Reserved for national use
          - 2 ICAO aircraft address broadcast by ground station
          - 3 Address other than ICAO aircraft broadcast by ground station
          - 4 Vehicle address
          - 5 Fixed ADS-B beacon address
          - 6 ADS-R target with non-ICAO address
          - 7 Reserved

 [1-3] 24-bit address (ICAO)
====== ========================================
"""

import sys, os

import fisb.level0.level0Exceptions as ex

def decodeServiceStatusFrame(ba, frameLength, reserved_2_24, isDetailed):
    """Decode a Service Status frame.

    Args:
        ba (byte array): Contains all the bytes of the frame.
        frameLength (int): Holds the current length of this frame.
        reserved_2_24 (byte): Reserved bits in frame header.
        isDetailed (bool): ``True`` if a full blown decode is to be done. ``False``
            is normal decoding for the usual FIS-B products. Detailed
            includes those items not normally needed for routine decoding.

    Returns:
        dict: Dictionary with decoded data.

    Raises:
        ServiceStatusException: Got a service type of 0 which should
            not happen.
    """

    # Dictionary to store items
    d = {}

    # List with planes being followed
    planeList = []

    d['frame_type'] = 15

    if isDetailed:
        d['frameheader_2_24'] = reserved_2_24

        
    # Loop for each plane being followed. Each set of 4 bytes is an
    # entry.
    for x in range(0, int(frameLength/4)):
        x4 = x * 4
        byte0 = ba[x4]
        addr = (ba[x4 + 1] << 16) | \
               (ba[x4 + 2] << 8) | \
               (ba[x4 + 3])
        byte1_1_4 = (byte0 & 0xF0) >> 4  
        signalType = (byte0 & 0x08) >> 3
        addrType = byte0 & 0x07

        entry = {}

        if isDetailed:
            entry['byte1_1_4'] = byte1_1_4
            entry['signal_type'] = signalType # always 1

        # See definitions above. This is pretty much always 0.
        entry['address_type'] = addrType

        # ICAO address in hex
        entry['address'] = '{:06x}'.format(addr)

        planeList.append(entry)
            
    d['contents'] = planeList
    
    return d
