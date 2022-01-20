"""Decode APDU Global Block Messages.

APDU Global Block messages  encompass the following product types:

- (63)    Regional NEXRAD
- (64)    Conus NEXRAD
- (70)    Icing (low)
- (71)    Icing (high)
- (84)    Cloud Tops
- (90)    Turbulence (low)
- (91)    Turbulence (high)
- (103)   Lightning

"""

import sys, os

import fisb.level0.level0Exceptions as ex

# Match digit to hex digit
idxToHex = '0123456789ABCDEF'

# Dictionary for matching number of strikes to
# the strike encoding
strikeDict = {0: '(0)    ',\
    1: '(1)    ',
    2: '(2)    ',
    3: '(3-5)  ',
    4: '(6-10) ',
    5: '(11-15)',
    6: '(>15)  ',
    7: 'ND     '}

def apdu_global_block(ba, productId, isDetailed):
    """Handle all Global Block Messages.

    Processes a Global Block Message and returns a dictionary
    holding its contents.

    Args:
        ba (byte array): A byte array holding the raw global block
            message data. ``ba[0]`` points to the head of the block reference
            indicator.
        productId (int): Product ID of this object. Different
            run length encoding schemes are used based on the product ID.
        isDetailed (bool): ``True`` if we desire detailed data not needed
            for normal decoding. ``False`` for normal level of detail.

    Returns:
        dict: Dictionary describing this object.
    
    Raises:
        ApduUnknownProductException: For an unknown product.
    """
    d = {}

    # Parse block reference indicator

    # Block Number
    blockNumber = ((ba[0] & 0x0F) << 16) | \
                  (ba[1] << 8) | \
                  ba[2]
    d['block_number'] = blockNumber
    
    # 0 - Empty block encoding
    # 1 - Run Length encoding
    elementId = (ba[0] & 0x80) >> 7
    d['element_id'] = elementId

    # Product specific bytes
    # The world is broken down into NEXRAD, lightning, cloud
    # tops into 'encoding type 1', and icing and turbulence into
    # 'encoding type 2'. Only encoding type 2 will get the altitude
    # level.
    #
    # Deviating slightly from the actual data, I encode the resolution
    # and N/S hemisphere into both products (it is implied for encoding
    # type 2.
    productSpecificBits = (ba[0] & 0x70) >> 4

    if productId in [63, 64, 84, 103]:
        scaleFactor = productSpecificBits & 0x03
        hemisphere = (productSpecificBits & 0x04) >> 2
    elif productId in [70, 71, 90, 91]:
        scaleFactor = 1  # Medium resolution
        hemisphere = 0   # always northern hemisphere

        # Two values based on 'low' or 'high' level products
        #
        # Low:  alt = (n * 2000) + 2000 feet
        # High: alt = (n * 2000) + 18000 feet
        #   For high values n can only be 0 to 4.
        #   Other values are reserved.
        altitude = productSpecificBits * 2000
        if productId in [70, 90]:
            # Low level
            altitude += 2000
        else:
            # High level
            altitude += 18000
        
        d['altitude_level'] = altitude
    else:
        raise ex.ApduUnknownProductException("Unknown Global Block product {}".format(productId))
    
    # 0 - high resolution
    # 1 - medium resolution
    # 2 - low resolution
    # 3 - reserved
    d['scale_factor'] = scaleFactor

    # 0 - Northern hemisphere
    # 1 - Southern hemisphere
    d['hemisphere'] = hemisphere

    # Deal with empty blocks and return
    if elementId == 0:
        # Make an empty block bitmap and return
        # Note that the block number is assumed to be
        # empty. The bitmap items are for blocks after
        # the starting block number
        d['empty_blocks'] = emptyBlockBitmap(ba)

        return d

    # de-run-length the run length bins
    if productId in [63, 64]:
        d['bins'] = nextradRL(ba)
        
    elif productId in [90, 91, 84]:
        d['bins'] = turbRL(ba)
        
    elif productId in [70, 71]:
        d['bins'] = icingRL(ba)

    elif productId in [103]:
        d['bins'] = lightningRL(ba)
        
    return d

def emptyBlockBitmap(ba):
    """Turn a bitmap block into an actual bitstring of 1's and 0's.

    Given a byte array that has its origin at the block reference
    indicator, read the bitmap information and return a string of 
    ones and zeros, with one indicating the block is zero. Note:
    the block corresponding to the block number for this block is
    NOT included in the bitmap. It is assumed to be empty.

    Args:
        ba (byte array): Byte array with its origin at the block reference
            indicator.

    Returns:
        str: String containing 1's and 0' as described above.
    """
    # set relative offset into ba
    ros = 3

    bitmap = ''
    bitmapLength = ba[ros] & 0x0F

    # Add top half of first word (shift 4 MSB to LSB)
    bitmap = addBits(ba[ros] >> 4, 4, bitmap)
    ros += 1

    # Add in the reset of the bits
    for _ in range(0, bitmapLength):
        bitmap = addBits(ba[ros], 8, bitmap)
        ros += 1
    
    return bitmap

def addBits(byte, numberOfBits, bitmap):
    """Used by ``emptyBlockBitmap`` to turn a byte or part of a byte into a bitstring.

    Turns MSB ``numberOfBits`` into a bitstring and appends it to 
    ``bitmap``.

    NOTE: bits are ordered from LSB to MSB for adding to bitstring. The
    result string has the blocks ordered left to right.

    Args:
        byte (byte array): Byte to turn into a bit string.
        numberOfBits (int): Number of bits (starting from the MSB) to
            convert. This is needed because there is one case where we only
            need to convert the lower half of a byte, instead of an
            entire byte. This is usually called with 4 or 8.
        bitmap (str): Current bitstring. This will be returned with the
            new bits appended.

    Returns:
        str: Bitmap with new bits appended to the end.
    """
    for _ in range(numberOfBits, 0, -1):
        if (byte & 0x01) != 0:
            bitmap = bitmap + '1'
        else:
            bitmap = bitmap + '0'

        byte = byte >> 1

    return bitmap
            
def nextradRL(ba):
    """Create the NEXRAD run lengths.

    NEXRAD Intensity values (in decibels relative to Z (dBZ)).
    **/R** is Regional and **/C** is CONUS:

    +---+-----------+----------+-------------+-------------------+
    |   | NEXTRAD/R | NEXRAD/C |    in/hr    | Intensity         |
    +===+===========+==========+=============+===================+
    | 0 |    < 5    |  No data |   < 0.01    | Hardly Noticeable |
    +---+-----------+----------+-------------+-------------------+
    | 1 |   5 - 19  |   < 20   | 0.01 - 0.02 | Very Light        |
    +---+-----------+----------+-------------+-------------------+
    | 2 |  20 - 29  | -> same  | 0.02 - 0.10 | Light to Moderate |
    +---+-----------+----------+-------------+-------------------+
    | 3 |  30 - 39  | -> same  | 0.10 - 0.45 | Moderate          |
    +---+-----------+----------+-------------+-------------------+
    | 4 |  40 - 44  | -> same  | 0.45 - 0.92 | Moderate to Heavy |
    +---+-----------+----------+-------------+-------------------+
    | 5 |  45 - 49  | -> same  | 0.92 - 1.90 | Heavy             |
    +---+-----------+----------+-------------+-------------------+
    | 6 |  50 - 54  | -> same  | 1.90 - 4.00 | Very Heavy        |
    +---+-----------+----------+-------------+-------------------+
    | 7 |   >= 55   | -> same  |    > 4.00   | Extreme           |
    +---+-----------+----------+-------------+-------------------+

    Args:
        ba (byte array): Byte array with ``ba[0]`` pointing to the first byte of the
            block reference indicator.

    Returns:
        Decoded run-length. Each run length is a 128 bytes, with values
        of 0-7. Note: the meaning of values 0 and 1 are different from NEXRAD
        Regional to NEXRAD CONUS.
    
    Raises:
        ApduTooManyBinsException: Found too many bins.
    """
    ros = 3
    bins = ''
    binTotal = 0
    
    # Only single byte runs are used. Count bins until 128.
    while (True):
        binCount = ((ba[ros] & 0xF8) >> 3) + 1
        binTotal += binCount
        binValue = chr(ba[ros] & 0x07)
        bins += binValue * binCount
        ros += 1

        if (binTotal == 128):
            return bins

        if (binTotal > 128):
            raise ex.ApduTooManyBinsException('Found too many bins (>128) in nextradRL')

def lightningRL(ba):
    """ Decode run-length encoding for lightning data.

    Polarity is encoded as a 1 for positive polarity and 0 for
    negative polarity.

    +---+--------------+
    +   | Strike Count +
    +===+==============+
    + 0 |     0        +
    +---+--------------+
    + 1 |     1        +
    +---+--------------+
    + 2 |     2        +
    +---+--------------+
    + 3 |   3 to 5     +
    +---+--------------+
    + 4 |   6 to 10    +
    +---+--------------+
    + 5 |  11 to 15    +
    +---+--------------+
    + 6 |    > 15      +
    +---+--------------+
    + 7 |   No data    +
    +---+--------------+
  

    ``ba`` is a byte array with ``ba[0]`` at the top of the block reference
    indicator.
    
    Things have returned to normal, but there was a period of time
    when lightning data was seriously messed up. The following
    notes refer to those times (in case they come back). There is a lot
    of code to catch if the problem comes back and provide appropriate
    data for debugging.

    There were some serious issues with unknown causes here:

    1. Lightning data is crazy because lightning bins rarely add to
       128. Either I misunderstand something, have missed something obvious,
       or the FIS-B code isn't generating correct data, or data consistent
       with the standard. Trying to get to the bottom of this is why there
       is so much debugging code in this routine.
    2. There is an undocumented case where ``F8`` is used to denote
       32 bins (as opposed to the normal 16 bin max). Apparently, if the
       bin count is ``1111`` (16 bins), polarity is ``1``, and strike count is
       ``000``, this will count as 32 bins. It has only been seen in the wild
       as ``0xf8f8f8f8``. It is not known if the general case where bin count
       can be any allowed value with a polarity of one and zero strike count
       occurs in the wild. As of this time, only F8 is allowed and counted as
       32 bins. Other cases will cause an exception by having bin counts that 
       don't total to 128. Testing has not shown any consistant way to handle
       cases other than ``0xF8F8F8F8``.
    
    Args:
        ba (byte array): Byte array with ``ba[0]`` pointing to the first byte of the
            block reference indicator.
    
    Returns:
        str: 128 byte string with one byte for each bin. The MSB is
        the polarity, and the 3-LSBs are the strike count.

    Raises:
        ApduLightningBinsException: If the bins don't add to 128, or there are
            128 bins, but there is space left in the frame.
    """

    ros = 3
    binTotal = 0
    binstr = ''

    # Remember the length of the array for flagging errors if we have not
    # reached 128 bins by the time we have reached the end of the array.
    baLen = len(ba)

    errStr = '\nbytes to decode: {}\n{}\n'.format(baLen - 3, ba[3:].hex())
    errStr += 'idx total-bins byte     bins    pol strikes    spcl\n' +\
              '--- ---------- ----  ---------- --- ---------- ----\n'

    count = 1
    # Uses a single byte for each run.
    while (True):
        specialFlag = ' '

        # If here, the bins didn't total to 128 and we are out of array.
        if ros == baLen:
            errStr = '\n**** less than 128 bins\n' + errStr
            raise ex.ApduLightningBinsException(errStr)

        val = ba[ros]
        binValue = chr(val & 0x0F)
        
        strikes = val & 0x07
        polarity = (val & 0x08) >> 3
        bins = (val & 0xF0) >> 4

        binsToAdd = 0

        # It is really unknown what it means if the strike count
        # is zero and the polarity is 1. The case of 0xF8 is well
        # known... F8F8F8F8 is often sent to represent 128 bins.
        # But there are many cases where the bin counts don't equal
        # 128. For now, we handle the F8 case, and treat the other 
        # cases as non-special.
        if (strikes == 0) and (polarity == 1):
            specialFlag = '*'

            # Handle non standard case where F8 means 32 bins
            if val == 0xf8:
                binsToAdd += bins + 17
            else:
                binsToAdd += bins + 1
        else:
            binsToAdd += bins + 1

        binTotal += binsToAdd 

        # Handle zero strikes with negative polarity case
        if binValue == '8':
            binValue = '0'
            
        binstr += binValue * binsToAdd
        
        errStr += '{:03}     {:03}     {:02x}    {:02} -> {:02}   {:1}  {:1} {}   {}\n'.\
            format(count, binTotal, ba[ros], bins, binsToAdd, polarity,\
                strikes, strikeDict[strikes], specialFlag)

        count += 1
        ros += 1

        if (binTotal == 128):
            if (count - 1) != baLen -3:
                errStr = '\n**** 128 bins but not all of the array used\n' + errStr
                raise ex.ApduLightningBinsException(errStr)

            return binstr

        if (binTotal > 128):
            errStr = '\n**** more than 128 bins\n' + errStr
            raise ex.ApduLightningBinsException(errStr)

def icingRL(ba):
    """De-run-length icing run lengths.

    To convert 3-bit altitude values to actual altitude, see
    ``turbRL()``-- they use identical altitudes.

    Icing actually encodes 3 values: supercooled large
    droplets (SLD), severity, and probability.

    Results are returned as a 3-byte string, in order of
    SLD probability, icing severity, and Icing probability
    (empty values are reserved or not used).
    
    +---+----------+----------+------------+
    +   + SLD Prob + Severity | Icing Prob |
    +===+==========+==========+============+
    + 0 | <= 5%    | None     |   <= 5%    +
    +---+----------+----------+------------+
    + 1 | <= 50%   | Trace    |   <= 20%   +
    +---+----------+----------+------------+
    + 2 | > 50%    | Light    |   <= 30%   +
    +---+----------+----------+------------+
    + 3 | No data  | Moderate |   <= 40%   +
    +---+----------+----------+------------+
    + 4 |          | Severe   |   <= 80%   +
    +---+----------+----------+------------+
    + 5 |          | Heavy    |   <= 60%   +
    +---+----------+----------+------------+
    + 6 |          |          |    > 80%   +
    +---+----------+----------+------------+
    + 7 |          | No data  |   No data  +
    +---+----------+----------+------------+

    I find it interesting that 'heavy' icing has a higher value than 'severe'
    in DO-358A/B ('severe' is 4 and 'heavy' is 5).
    In the 
    `5/7/2003 Federal Register (page 24542)
    <https://www.federalregister.gov/documents/2003/05/07/03-11237/icing-terminology/>`_,
    the FAA rates severe icing as more 
    intense than heavy. It appears that the icing severity does not appear in
    numeric order and *severe* is worse than *heavy* even though *severe* is
    4 and *heavy* is 5. The FAA can get away with this because *severe* is
    never used.
    
    ``ba`` is a byte array with ``ba[0]`` at the top of the block reference
    indicator.
    
    Args:
        ba (byte array): Byte array with ``ba[0]`` pointing to the first byte of the
            block reference indicator.

    Returns:
        str: 128 byte string with one byte for each bin. The bits are:
        ``ddsssppp`` where ``dd`` is the SLD (0-3), ``sss`` is the severity (0-7), and
        ``ppp`` (0-7) is the probability.

    Raises:
        ApduTooManyBinsException: If too many bins found.
    """
    ros = 3
    binCount = 0
    binTotal = 0
    bins = ''
    
    # Always uses two bytes. The first is the run length. 2nd byte is the
    # data for display.
    while (True):
        binCount = ba[ros] + 1
        binValue = chr(ba[ros + 1] & 0xFF)
        bins += binValue * binCount
        binTotal += binCount
        ros += 2

        if (binTotal == 128):
            return bins

        if (binTotal > 128):
            raise ex.ApduTooManyBinsException('Found too many bins (>128) in icingRL')

def turbRL(ba):
    """Return decoded run length for turbulence and cloud top blocks.

    To decode 3-bit altitude (all values in MSL): ::

        Low Level  = (byte + 1) * 2000
        High Level = 18000 + (byte * 2000) [only byte values 0-3 allowed]
    
    The data is encoded for a range of Eddy Dissipation Rates (EDRs). A value
    of 0 is less than 7 EDRs, and a value of 14 is >= 98 EDRs. 15 means no
    data. For values 1 to 13, the low value is <= to byte * 7, and the
    high value is < (byte + 1) * 7.

    ``ba`` is a byte array with ``ba[0]`` at the top of the block reference
    indicator.

    Args:
        ba (byte array): Byte array with ``ba[0]`` pointing to the first byte of the
            block reference indicator.

    Returns:
        str: 128 character string with one character for each bin.

    Raises:
        ApduTooManyBinsException: If too many bins found.
    """
    ros = 3
    binCount = 0
    binTotal = 0
    bins = ''
        
    # Uses 1 or two byte for the run. If the 4 MSB bits is 0xE0, the
    # next byte contains the number of bins. Else, the 4 MSB bits are
    # the number of bins - 1.
    while (True):
        byte1 = (ba[ros] & 0xF0) >> 4
        binValue = chr(ba[ros] & 0x0F)

        if byte1 == 0x0E:
            binCount = ba[ros + 1] + 1
            bins += binValue * binCount
            binTotal += binCount
            ros += 2
        else:
            # single byte
            binCount = byte1 + 1
            bins += binValue * binCount
            binTotal += binCount
            ros += 1

        if (binTotal == 128):
            return bins

        if (binTotal > 128):
            raise ex.ApduTooManyBinsException('Found too many bins (>128) in turbRL')
