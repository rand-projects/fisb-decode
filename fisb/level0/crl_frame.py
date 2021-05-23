"""Decodes a Current Report List frame.

The following messages have associated CRLs:

- (8)     NOTAM-TFR
- (11)    AIRMET
- (12)    SIGMET, Convective SIGMET (WST)
- (14)    G_AIRMET
- (15)    CWA
- (16)    NOTAM-TRA
- (17)    NOTAM-TMOA

"""
import sys, os

import fisb.level0.utilities as util

def decodeCrlFrame(ba, frameLength, reserved_2_24, isDetailed):
    """Decode CRL (Current Report List) frame.

    Args:
        ba (byte array): Byte array containing all the bytes of the frame.
        frameLength (int): Length, in bytes, of this frame.
        reserved_2_24 (int): Reserved bits in frame header.
        isDetailed (bool): ``True`` if a full blown decode is to be done. ``False``
            is normal decoding for the usual FIS-B products. Detailed
            includes those items not normally needed for routine decoding.

    Returns:    
        dict: Dictionary with decoded data.
    """
    # Dictionary to store CRL items
    d = {}

    # List of CRLs. May be empty because it is possible to have 0
    # reports listed
    crlList = []

    d['frame_type'] = 14
        
    # Process CRL header (7 bytes)

    # Following products are used:
    #  8, 11, 12, 14, 15, 16, 17
    d['product_id'] = (ba[0] << 3) | \
                      ((ba[1] & 0xE0) >> 5)

    # Product range is in 5NM increments. We multiple by 5 to get
    # the actual NMs
    d['product_range_nm'] = ba[2] * 5

    # 1 - Specifies that the CRL is for a TFR notam. These are the only kind
    #     sent currently.
    d['tfr_notam'] = (ba[1] & 0x10) >> 4

    # 0 - No overflow
    # 1 - more than 138 items in the list. All items may not be listed
    d['o_flag'] = (ba[1] & 0x02) >> 1

    # Location may be in bytes 4-6 (index 3-5) if lFlag is 1. Otherwise,
    # location is not present. We need to know this for indexing.
    #
    # Because it is not currently sent, it is not certain the location
    # (or if its even DLAC) will decode properly if they decide
    # to send them.
    lFlag = ba[1] & 0x01
    d['l_flag'] = lFlag

    if lFlag:
        numberOfReports = ba[6]
        locationOffset = 7
        location = util.dlacToText(ba, 3, 3)
        d['location'] = location
    else:
        numberOfReports = ba[3]
        locationOffset = 4
            
    # Number of items in the list (0 - 138)
    d['number_of_reports'] = numberOfReports

    if isDetailed:
        d['reserved_2_56'] = (ba[1] & 0x0C) >> 2
        d['frameheader_2_24'] = reserved_2_24


    for x in range(0, numberOfReports):
        offset = (x * 3) + locationOffset

        entry = {}

        # Matches year of the report in actual message.
        # For TMOA and TRA this will be the month of the report
        entry['report_year_or_month'] = ba[offset] & 0x7F

        # Matches report_number in actual message.
        entry['report_number'] = ((ba[offset + 1] & 0x3F) << 8) | \
                                 ba[offset + 2]

        # 1 - Textual message
        entry['text_flag'] = (ba[offset + 1] & 0x80) >> 7

        # 2 - Graphical message
        entry['graphics_flag'] = (ba[offset + 1] & 0x40) >> 6

        if isDetailed:
            entry['reserved_1_1'] = (ba[offset] & 0x80) >> 7

        crlList.append(entry)

    d['reports'] = crlList

    return d
