"""Contains an APDU frame

Holds an APDU header and associated data.

APDUs encompass the following product types:

- (8)     NOTAM-D, NOTAM-FDC, NOTAM-TFR, Unavail FIS-B Products
- (11)    AIRMET
- (12)    SIGMET, Convective SIGMET (WST)
- (13)    SUA
- (14)    G_AIRMET
- (15)    CWA
- (16)    NOTAM-TRA
- (17)    NOTAM-TMOA
- (63)    Regional NEXRAD
- (64)    Conus NEXRAD
- (70)    Icing (low)
- (71)    Icing (high)
- (84)    Cloud Tops
- (90)    Turbulence (low)
- (91)    Turbulence (high)
- (103)   Lightning
- (413)   METAR, TAF, PIREP, WINDS & TEMPS

"""
import sys, os

import fisb.level0.level0Exceptions as ex
import fisb.level0.level0Config as cfg

from fisb.level0.apdu_413 import apdu_413
from fisb.level0.apdu_twgo import apdu_twgo
from fisb.level0.apdu_global_block import apdu_global_block

# Bit array lookup
bitLookup = [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01]

def decodeApduFrame(ba, frameLength, reserved_2_24, isDetailed):
    """Decode APDU frame and return as dictionary.

    Note: If we get a product id we cannot handle, the ``contents``
    element in the returned dictionary will be an empty
    dictionary.

    Args:
        ba (byte array): Contains all the bytes of the frame. ``ba[0]`` is the first
            byte of the frame.
        frameLength (int): Length, in bytes, of this frame.
        reserved_2_24 (int): Reserved bits in frame header.
        isDetailed (bool): ``True`` if a full blown decoded is to be done. ``False``
            is normal decoding for the usual FIS-B products. Detailed
            includes those items not normally needed for routine decoding.

    Returns:
        dict: Dictionary with decoded information, or None if we are
        blocking a specific product type.

    Raises:
        BadApduProductIdException: For any APDU types we don't know about.
    """
    (productId, payloadStartingByte, timeOption, month, day, \
     hour, minute, sFlag, \
     productFileLength, apduNumber, \
     productFileId) = decodeApduHeader(ba)
    
    # One check against a trashed message is to check the
    # product ID.
    if productId not in [413, 8, 11, 12, 13, 14, 15, 16, 63, \
                         17, 64, 103, 84, 70, 71, 90, 91]:
        # Throw an exception
        raise ex.BadApduProductIdException("Unknown product id of {}."\
                                           .format(productId))

    # Block SUA messages if configured.
    if (productId == 13) and cfg.BLOCK_SUA_MESSAGES:
        return None

    d = {}

    # APDU frame type is 0
    d['frame_type'] = 0

    # Product id
    d['product_id'] = productId

    if isDetailed:
        # In past standards, there were an application flag,
        # a geographic flag, and a provider specific flag.
        # In DO-358B, these have been changed to reserved bits.
        # application method flag. We combine them together.
        d['agp_flag'] = (ba[0] & 0xE0) >> 5

        d['frameheader_2_24'] = reserved_2_24
            
    # t_opt is defined differently than DO-267A.
    # (DO-267A includes seconds, time flags have
    # changed meaning).
    # Currently only values 2 and 0 are sent.
    # Both includes hours and minutes. 2 includes
    # month and day.
    d['t_opt'] = timeOption

    if timeOption == 2:
        d['month'] = month
        d['day'] = day

    d['hour'] = hour
    d['minute'] = minute

    # segmentation flag
    d['s_flag'] = sFlag

    # The only items segmented are TWGO messages. If segmented,
    # store the contents for later processing. The TWGO
    # payload header is the same for each message segment.
    if (sFlag == 1):
        # This is essentially the 'report number' that links
        # other segments to this one. It doesn't come from an
        # actual report, but is unique for a particular FIS-B
        # reporting area.
        d['product_file_id'] = productFileId

        # Total number of segments for this 'product file'
        # I.e. 4 means there will be four segments with APDU
        # numbers 1,2,3,4 sent.
        d['product_file_length'] = productFileLength

        # Which part of the product file this is. I.e. 2
        # means this is the second segment.
        #
        # 0 is an illegal number here and should cause the
        # APDU to be ignored. DO-358B changed the above statement
        # slightly indicating that other APDU segments should
        # be retained for message reconstruction.
        d['apdu_number'] = apduNumber
        
        # Each segmented record will contain the same TWGO header
        # (6 bytes) that will need to be removed when unsegmenting.
        # This also implies that when storing a segment, you need to
        # also store APDU information (i.e. times) associated with at
        # least one of the segments. Probably better to store the entire
        # message until it is processed.

        # Store contents for later reconstruction
        d['contents'] = ba[payloadStartingByte:].hex()
        
        # No further processing to be done, so return
        return d

    # Handle each product
    if productId == 413:
        d['contents'] = apdu_413(ba[payloadStartingByte:])
    elif productId in [8, 11, 12, 13, 14, 15, 16, 17]:
        d['contents'] = apdu_twgo(ba[payloadStartingByte:], \
                                  productId, isDetailed)
    elif productId in [63, 64, 70, 71, 84, 90, 91, 103]:
        d['contents'] = apdu_global_block(ba[payloadStartingByte:], \
                                          productId, isDetailed)
    
    return d
    
def getNthBit(ba, bit):
    """ Get the n'th bit of a byte array and return a ``'1'`` or ``'0'`` string.

    Args:
        ba (byte array): Byte array containing bits to find.
        bit (int): Bit index into ``ba``.
    
    Returns:
        str: Either a ``'0'`` or ``'1'`` string character.
    """
    byte = int(bit / 8)
    pos = bit % 8
    if ba[byte] & bitLookup[pos]:
        return '1'
    return '0'

def normalizeApduHeader(ba):
    """Normalize APDU header.

    APDU Header has a lot of places that are optional, making it hard to just pick
    bits off. We take the existing header and normalize it in to a full bit string,
    adding 0's to the optional parts we don't have.

    Args:
        ba (byte array): Byte array containing the APDU message.

    Returns:
        tuple: Tuple with two values:
        
        1. A bitstring containing 1 or 0s representing the complete
           expanded header, so you can find everything in the same spot.
        2. An integer which is the index into ``ba`` where the actual payload starts.
    """
        
    bitString = ''

    # First 14 bits are always there
    for i in range(0, 14):
        bitString += getNthBit(ba, i)
    nextBit = 14

    # Next bit is the sFlag
    sFlag = getNthBit(ba, nextBit)
    nextBit += 1
    bitString += sFlag

    # Next 2 bits are the time option
    t1 = getNthBit(ba, nextBit)
    t0 = getNthBit(ba, nextBit + 1)
    nextBit += 2
    bitString += t1 + t0
    
    timeOption = 0
    if t1 == '1':
        timeOption = 2
    if t0 == '1':
        timeOption += 1

    # Optional month and day (they always come as a pair)
    if timeOption >= 1:
        for i in range(nextBit, nextBit + 9):
            bitString += getNthBit(ba, i)
        nextBit += 9
    else:
        bitString += '000000000'

    # Required hours and minutes
    for i in range(nextBit, nextBit + 11):
        bitString += getNthBit(ba, i)
    nextBit += 11

    # Optional segmentation data block
    # As of DO-258, this is always the TWGO (Mitre) format
    # which is 28 bits.

    # Mitre (TWGO) version
    if sFlag == '1':
        for i in range(nextBit, nextBit + 28):
            bitString += getNthBit(ba, i)
        nextBit += 28
    else:
        bitString += '0000000000000000000000000000'

    # nextBit is the total number of bits seen + 1. 
    # subtract one bit (to point to the actual number 
    # bit processed, divide by 8 and add one for the 
    # payload starting byte
    payloadStartingByte = int((nextBit - 1) / 8) + 1

    return (bitString, payloadStartingByte)
    
def decodeApduHeader(ba):
    """Given an APDU message, decode and return the header information.

    Will not handle ``A``, ``G``, or ``P`` flags. We never see these and DO-358A says
    to ignore them (In DO-358B they are considered as a single group of
    reserve bits).

    The APDU header is a somewhat complicated beast. It's true format is
    found in DO-267A page D-23. In the current standard, only certain fields
    are used, the segmentation header is different, and the ``A``, ``G``, and ``P`` flags
    are not used at all.
        
    This code was written using the DO-267A standard since it is a superset
    of everything that has come since. It has been modified to conform to
    DO-358B.

    DO-358A/B states that there is only one form of the segmentation block that
    will be sent. This routine will decode all segmentation blocks that way,
    see comments in the code.
    
    Args:
        ba (byte array): Byte array with ``ba[0]`` being the start of the APDU header.

    Returns:
        tuple: 11 element tuple:
        
        1. ``productId`` (int)
        2. ``payloadStartingByte`` (int)
        3. ``timeOption`` (int)
        4. ``month`` (int)
        5. ``day`` (int)
        6. ``hour`` (int)
        7. ``minute`` (int)
        8. ``sFlag`` (int)
        9. ``productFileLength`` (int)
        10. ``apduNumber`` (int)
        11. ``productFileId`` (int)

    Raises:
        BadBitHeaderException: If we got the wrong number of bits in the header.
    """

    (bitHeader, payloadStartingByte)  = normalizeApduHeader(ba)

    if (len(bitHeader) != 65):
        raise ex.BadBitHeaderException('Bad bit header len. Got {}. {}'.format(len(bitHeader),\
                                                                            bitHeader))

    productId = int(bitHeader[3:14], 2)
    sFlag = int(bitHeader[14:15], 2)
    timeOption =  int(bitHeader[15:17], 2)
    month = int(bitHeader[17:21], 2)
    day = int(bitHeader[21:26], 2)
    hour = int(bitHeader[26:31], 2)
    minute = int(bitHeader[31:37], 2)

    # Segmentation blocks are different than DO-267A.
    # These blocks are normally seen in TWGO messages only [DO-358B: 8->17]
    # This is defined in DO-358A, but is different than in DO-267A.
    productFileId = int(bitHeader[37:47], 2)
    productFileLength = int(bitHeader[47:56], 2)
    apduNumber = int(bitHeader[56:65], 2)

    return (productId, payloadStartingByte, timeOption, \
            month, day, hour, minute, \
            sFlag, productFileLength, apduNumber, productFileId)
