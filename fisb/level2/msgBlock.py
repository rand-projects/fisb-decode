"""Decode and create messages from block data messages.

The following messages are produced by this module:

* NEXRAD_REGIONAL
* NEXRAD_CONUS
* TURBULENCE
* ICING
* CLOUD_TOPS
* LIGHTNING
"""

import sys, os, json, time, re, copy, pprint

import fisb.level2.level2Config as cfg
import fisb.level2.utilities as util
import fisb.level2.level2Exceptions as ex

# 128 0 characters (for detecting empty bins for NEXRAD)
ZEROS_128 = chr(0) * 128

# States for filling empty block messages
LOOKING_FOR_1 = 0
IN_1s = 1

def alternateBlockNumber(blockNumber, scale_factor):
    """Convert blockNumber to alternate blockNumber.

    Standard FIS-B block numbers divide the globe into 450 different sections
    along the equator (longitudinally) and 1 arc minute sections latitudinally.
    Block numbers just increase as you go around the globe.

    Just by looking at them, it's hard to determine the area of latitude and
    longitude they are describing. It is also hard to realize which
    blocks align
    vertically on top of one another, especially if one is trying to coalesce
    blocks in a vertical (*x* or latitudinal) direction.

    Fisb-decode abandons this system and converts the supplied block numbers
    to '*Alternate Block Numbers*', This is much easier to conceptualize and
    implement.
    
    What this routine does is to take the standard block number
    and reinterpret
    it into one which shows the 'row' of latitude (0-based starting at the
    equator) and 'column' of longitude (0-based starting at the
    prime meridian).
    Each alternate block number is essentially a '*y*' and '*x*' coordinate.

    The 'column' number is converted to a 3 digit number with leading zeros.
    The 'row' number is then prepended to that. Another way of
    thinking about this is to format the number 
    by multiplying the row by 1000 and adding the column.
    For example, high resolution block 276640 has a row of 614 and a column of
    340 (276640/450 is 614 with remainder 340). So the alternate block number
    is 614340.
    
    Note that column numbers will always be less than 450 so will fit into
    3 digits.
    Row numbers can exceed 3 digits and that is why they are the first part of
    the number.

    Numbers will vary based on the scale factor. There are 3 possible scale
    factors,
    only two of which are used: high and medium. High (0) has 450 blocks in 
    one row of latitude, and medium (1) has 90 blocks per row. This
    routine will
    also convert the never used low resolution, which has 50 blocks per row.

    Each High resolution block encodes 4 mins of latitude and 48 mins of
    longitude.
    Medium resolution blocks encode 20 mins of latitude and 240/60 or
    4 degrees
    of longitude. Low resolution blocks encode 36 mins of latitude and 432/60
    or 7.2 degrees of longitude.

    Above 60 degrees of latitude, FIS-B starts sending only even block
    numbers. To
    make the concept of 'each column can be stacked above and below to each
    same numbered column', some manipulation (splitting into two and doubling)
    is required. That
    doesn't have anything to with this routine (``normalizeBins()`` does that),
    but needs to be considered when dealing with actual data blocks.

    Args:
        blockNumber (int): Default FIS-B blocknumber.
        scale_factor (int): DO-358B scale factor. 0 (high), 1 (medium), 2
          (low).

    Returns:
        int: An integer representing the alternate block number.
    """
    blockOffset = 0
    divFactor = 1

    if scale_factor == 1:
        blockOffset = 1800
        divFactor = 5
    elif scale_factor == 2:
        blockOffset = 3600
        divFactor = 9

    row, col = divmod((blockNumber - blockOffset), blockOffset + 450)
    col = col / divFactor
    
    altBlockNumber = (row * 1000) + col

    return int(altBlockNumber)

def normalizeBins(altBlockNumber, scaleFactor, bins):
    """Normalize bins > 60 degrees of latitude

    Above 60 degrees latitude, FIS-B only sends 
    even-numbered blocks.

    To maintain the row and column numbers we used,
    each block above 60 deg is split in to a left
    half and a right half. The left half is the
    even column, and the right half is the odd column.

    Since we are getting only half the resolution,
    we double each bin.

    If the ``altBlockNumber`` isn't above 60 degrees, we just
    return the original bins.

    Args:
        altBlockNumber (int): Alternate block number to consider.
        scaleFactor (int): High (0), Medium (1), or Low (2).
        bins (str): Bin string to convert.

    Returns:
        tuple: Tuple:

          * (bool) ``True`` if we made a conversion (> 60 degrees) or
            ``False`` if we didn't.
          * (str) Bin string to use.
    """
    altRow = int(altBlockNumber / 1000)
    
    # First row at 60 degs: High-> 900, Med-> 180, Low-> 100
    if (scaleFactor == 0) and (altRow < 900):
        return (False, [bins])
    elif (scaleFactor == 1) and (altRow < 180):
        return (False, [bins])
    elif (scaleFactor == 2) and (altRow < 100):
        return (False, [bins])

    # If here, we are higher than 60 degs

    # bin value of '0' is sent by emptyBlockMessages()
    # as a shame. Just return True. The return value of
    # ['0'] is ignored.
    if bins == '0':
        return (True, ['0'])

    # We take a single block and make a left hand and
    # right hand block.
    leftBins = ''
    rightBins = ''

    for i in range(0,4):
        for j in range(0, 16):
            lpixel = bins[(i * 32) + j + 16]
            rpixel = bins[(i * 32) + j]
            leftBins = leftBins + lpixel + lpixel
            rightBins = rightBins + rpixel + rpixel

    return (True, [leftBins, rightBins])

def emptyBlockMessages(blockNumber, scale_factor, \
                       empty_blocks, productName, productAbbr, \
                       eventDate, expirationDate, \
                       dateLabel):
    """Create messages for empty blocks.

    Given a set of empty blocks, create one or more messages
    each containing a ``bins`` field of 128 zeros (chr(0)).

    The messages returned from this function are based on the empty
    block DO-258 messages which contains a run length set of empty blocks.
    Therefore, this function returns a list which will have 1 to n output
    empty-block messages.

    The resulting empty block(s) will use the alternate block number.

    Args:
        blocknumber (int): Starting blocknumber.
        scale_factor (int): DO-358B scale factor.
        empty_blocks (str): String containing a ``1`` for each empty block and
          ``0`` if the block is not empty.
        productName (str): Name to display as the product name of the message.
        productAbbr (str): Name to display as the product abbreviation
          of the message.
        eventDate (str): ISO datetime for the message (either when it occurred,
            or its forecast time).
        expirationDate (str): Expiration ISO datetime for the message.
        dateLabel (str): Label that either specifies ``observation_time`` 
            or ``valid_time`` depending on the message type.

    Returns:
        list: A list of messages specifing the empty blocks.
    """
    
    msgList = []

    # Make the empty block include the first block
    empty_blocks = '1' + empty_blocks 

    emptyBins = chr(0) * 128

    currentBlockNumber = blockNumber

    # Different resolutions get different block number increments
    blockIncr = 1
    if scale_factor == 1: # Medium res
        blockIncr = 5
    elif scale_factor == 2: # Low res (never seen)
        blockIncr = 9

    for x in empty_blocks:
        if x == '1':
        # Generate message and add to list
            newMsg = {}
            newMsg['type'] = productName
            newMsg['unique_name'] = productAbbr + '-' + eventDate
            altBlockNumber = alternateBlockNumber(currentBlockNumber, \
                scale_factor)
            newMsg['alt_bn'] = altBlockNumber
            newMsg['scale_factor'] = scale_factor

            # Check for blocks >= 60 degrees latitude. Each block at that level
            # gets two empty blocks.
            isAbove60Deg, _ = normalizeBins(altBlockNumber, scale_factor, '0')
            newMsg['bins'] = emptyBins
            newMsg[dateLabel] = eventDate
            newMsg['no_msg_digest'] = 't'
            newMsg['expiration_time'] = expirationDate
            msgList.append(newMsg)        

            if isAbove60Deg:
                # Make shallow copy
                msgCopy = copy.copy(newMsg)
                msgCopy['alt_bn'] = msgCopy['alt_bn'] + 1
                newMsg['bins'] = emptyBins
                msgList.append(msgCopy)

        # Special case for highres block numbers above 60 deg latitude
        if (currentBlockNumber >= 405000) and (scale_factor == 1):
            currentBlockNumber = currentBlockNumber + 2
        else:
            currentBlockNumber = currentBlockNumber + blockIncr

    return msgList

def getProductSpecificInfo(productId, contents, isoDate):
    """Housekeeping chores for all block types.

    Args:
        productId (int): Message product Id for block type.
        contents (dict):  Dictionary of the 'contents' slot for the message.
        isoDate (str): ISO date string for the message. Will be used to
            calculate the expiration date.

    Returns:
        tuple: A 5 item tuple containing:

        1. (str) Expiration date for this message based on type.
        2. (str) Product name (``type`` key)
        3. (str) Product abbreviation (used to create ``unique_name`` key).
        4. (bool) ``True`` if the message has no active blocks. This can
           either be from an empty block message (``element_id``
           is zero).
        5. (str) What to label the product date. Will be ``valid_time``
           for forecast types and ``observation_time`` for
           observations.

    Raises:
        BadProductIdException: If we get an unknown product id.
    """
    # applies to all block products
    isEmpty = False
    
    if contents['element_id'] == 0:
        isEmpty = True

    if productId == 63:
        productName = 'NEXRAD_REGIONAL'
        productAbbr = 'NR'        
        expirationDate = util.addMinutesToIso8601(\
            isoDate, cfg.REGIONAL_NEXRAD_EXPIRATION_MINUTES)
        dateLabel = 'observation_time'

    elif productId == 64:
        productName = 'NEXRAD_CONUS'
        productAbbr = 'NC'        
        expirationDate = util.addMinutesToIso8601(\
            isoDate, cfg.CONUS_NEXRAD_EXPIRATION_MINUTES)
        dateLabel = 'observation_time'

    elif productId in [90, 91]:
        productName = 'TURBULENCE_{:05}'.format(contents['altitude_level'])
        productAbbr = 'T' + str(contents['altitude_level'])
        expirationDate = util.addMinutesToIso8601(\
            isoDate, cfg.TURBULENCE_EXPIRATION_MINUTES)
        dateLabel = 'valid_time'

    elif productId in [70, 71]:
        productName = 'ICING_{:05}'.format(contents['altitude_level'])
        productAbbr = 'I' + str(contents['altitude_level'])
        expirationDate = util.addMinutesToIso8601(\
            isoDate, cfg.ICING_EXPIRATION_MINUTES)
        dateLabel = 'valid_time'

    elif productId == 84:
        productName = 'CLOUD_TOPS'
        productAbbr = 'CT'        
        expirationDate = util.addMinutesToIso8601(\
            isoDate, cfg.CLOUD_TOPS_EXPIRATION_MINUTES)
        dateLabel = 'valid_time'

    elif productId == 103:
        productName = 'LIGHTNING'
        productAbbr = 'LGT'        
        expirationDate = util.addMinutesToIso8601(\
            isoDate, cfg.LIGHTNING_EXPIRATION_MINUTES)
        dateLabel = 'observation_time'

    else:
        raise ex.BadProductIdException('Unknown Block product id')
    
    return (expirationDate, productName, productAbbr, isEmpty, \
        dateLabel)


def msgBlock(contents, productId, \
             rYear, rMonth, rDay, rHour, rMin, \
             hour, minute):
    """Process all block oriented image messages.

    Args:
        contents (dict): Contents of ``frame['contents']``
        productId (int): Product id.
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.
        rHour (int): Message received hour.
        rMin (int): Message received minute.
        hour (int): APDU hour.
        minute (int): APDU minute.

    Returns:
        list: List containing messages. It will usually contain
        only a single message. It will contain more than one message
        in the following cases:
        
          - Sets of empty blocks.
          - Blocks that are higher than 60 deg latitude. This will 
            produce a set of two blocks.
    """

    msgList = []
    
    # All messages for a single image have a single common time. This time
    # defines the product (i.e., all parts of the same
    # map have the same time). If a newer time arrives,
    # that is a different product. For some products,
    # the time is an issue time. For others, it is the 
    # valid time for a forecast.
    eventDate = util.iso8601FromApduHourMins(rYear, rMonth, \
                    rDay, rHour, rMin, \
                    hour, minute, True)

    # Get product specific items
    (expirationDate, productName, productAbbr, isEmpty, \
        dateLabel) = \
            getProductSpecificInfo(productId, \
            contents, eventDate)

    scale_factor = contents['scale_factor']

    if isEmpty:
        msgList = emptyBlockMessages(contents['block_number'], \
            scale_factor, \
            contents['empty_blocks'], productName, productAbbr, \
            eventDate, expirationDate, dateLabel)
    else:
        # Normal message with bins
        newMsg = {}
        newMsg['type'] = productName
        newMsg['unique_name'] = productAbbr + '-' + eventDate
        altBlockNumber = alternateBlockNumber(contents['block_number'], \
                                                scale_factor)            
        newMsg['alt_bn'] = altBlockNumber
        newMsg['scale_factor'] = scale_factor
        isAbove60Deg, bins = normalizeBins(altBlockNumber, scale_factor, \
                        contents['bins'])
        newMsg['bins'] = bins[0]
        newMsg['no_msg_digest'] = 't'

        newMsg[dateLabel] = eventDate
        newMsg['expiration_time'] = expirationDate
        msgList.append(newMsg)        

        if isAbove60Deg:
            # Make shallow copy
            msgCopy = copy.copy(newMsg)
            msgCopy['alt_bn'] = msgCopy['alt_bn'] + 1
            newMsg['bins'] = bins[1]
            msgList.append(msgCopy)

    return msgList
