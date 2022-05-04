"""Contains a ServiceStatus frame.

Service Status frames holds the aircraft currently being tracked by
UAT ADS-B (i.e. the planes that get a hockey puck).

Originally, information for this section was based on
*SRT-047 Rev 01 (2011) section 3.3.4.1.2*.

Currently, information is based on DO-282C.

With DO-282C, the previous reserved 4 MSB bits of byte [0] are to be used
for the type of service being provided. As of 1/19/22, this is not yet
implemented.

This data is typically sent out every 20 seconds. Each message may have
different aircraft listed. This implies that you simply can't replace
one message with another-- you need to keep track of each aircraft and
expire the entry if it is not refreshed. 40 seconds seems to be a reasonable
expiration time.

Each frame is 4 bytes long:

====== ========================================
 BYTE  VALUE
 [0]   ttttsqqq
        t = This was all reserved up until DO-282C (1/19/22: Not yet implimented)
          - 0       No services   
          - 1       TIS-B
          - 2       ADS-R
          - 3       TIS-B, ADS-R
          - 4       ADS-SLR (Same Link Rebroadcast, i.e. for aircraft on surface
                     which may be blocked by ground objects.)
          - 5       TIS-B, ADS-SLR
          - 6       ADS-R, ADS-SLR
          - 7       TIS-B, ADS-R, ADS-SLR
          - 8-15    Reserved

        s = SIGNAL_TYPE (always 1. If 0, is going out of service.)

        q = address qualifier

          - 0 ADS-B target (ICAO addr)
          - 1 ADS-B target (self assigned address)
          - 2 TIS-B, ADS-R, ADS-SLR (ICAO addr)
          - 3 TIS-B target (from tracking)
          - 4 Vehicle address
          - 5 Fixed ADS-B beacon address
          - 6 ADS-R, ADS-SLR target (non-ICAO address)
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
        services = (byte0 & 0xF0) >> 4  
        signalType = (byte0 & 0x08) >> 3
        addrType = byte0 & 0x07

        entry = {}

        if isDetailed:
            entry['signal_type'] = signalType # always 1

        # Make service list if services present
        if (services != 0) and (services < 8):
            services_string = ""
            if (services & 0x01) != 0:
                services_string += services_string("T")
            if (services & 0x02) != 0:
                services_string += services_string("R")
            if (services & 0x04) != 0:
                services_string += services_string("S")
        elif services == 0:
            services_string = "X"
        elif services >= 8:
            services_string = "?"
        
        entry['services'] = services_string

        # See definitions above. This is pretty much always 0.
        entry['address_type'] = addrType

        # ICAO address in hex
        entry['address'] = '{:06x}'.format(addr)

        planeList.append(entry)
            
    d['contents'] = planeList
    
    return d
