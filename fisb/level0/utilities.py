"""Module containing level0 utility functions.
"""

import sys, os, time
from datetime import timezone, datetime

import fisb.level0.level0Config as cfg

# String for performing translation of dlac to text
#
# FIS-B uses a form of DLAC encoding. Some non-printing characters
# have been changed to printing characters (that do not otherwise
# appear in DLAC) as follows:
#
#   000000 ETX   ~ (End of Text Marker)
#   011011 NC    ~ (Null Character)
#   011100 TAB   \t (Tab) However, what this really means is that the next
#                         six-bit character is the number of spaces
#                         to insert (1-64)
#   011101 RS    ~ (Record Separator)
#   011111 CC    | (Change Cypher) Not used in FIS-B for that purpose.
dlacString = "~ABCDEFGHIJKLMNOPQRSTUVWXYZ~\t~\n| !\"#$%&'()*+,-./0123456789:;<=>?"

triggerList = []

def textToDlac(str):
    # Make sure string length is divisible by three.
    while (len(str) % 4) != 0:
        str = str + '~'

    # Make upper case
    str = str.upper()
    
    # Get number of bytes this will turn into (4 characters in 3 bytes)
    byteCount = int((len(str) / 4) * 3)
    
    # Number of bytes to encode.
    ba = bytearray(byteCount)

    # Loop for each 4 characters, make 1 3-byte set.
    baIdx = 0
    strIdx = 0
    for _ in range(0, int(byteCount / 3)):
        c1 = dlacString.index(str[strIdx])
        c2 = dlacString.index(str[strIdx + 1])
        c3 = dlacString.index(str[strIdx + 2])
        c4 = dlacString.index(str[strIdx + 3])

        strIdx += 4

        ba[baIdx] = (c1 << 2) | ((c2 & 0x30) >> 4)
        ba[baIdx + 1] = ((c2 & 0x0F) << 4) | ((c3 & 0x3C) >> 2)
        ba[baIdx + 2] = ((c3 & 0x3) << 6) | c4

        baIdx += 3

    return ba.hex()
    
def dlacToText(byteArray, startIndex, bytesToDecode):
    """Convert DLAC 6-bit string to text.
    
    Given an index into a byte array (containing DLAC characters)
    and the number of bits from the byte array (``bytesToDecode``), return
    a text string.

    ``bytesToDecode`` is the number of bytes, not the number of DLAC characters.

    Args:
        byteArray (byte array): Byte array to extract the DLAC text from.
        startIndex (int): Index into the byte array.
        bytesToDecode (int): Number of bytes to use for the encoding.

    Returns:
        str: Text string encoded from the DLAC characters.
        Will remove ETX, NC, and RS characters.
    """
    text = ''
    tab = False
    for i in range(0, bytesToDecode):
        m = i % 3
        if m == 0:
            j = (byteArray[startIndex + i] & 0xFC) >> 2
            (text, tab) = addDlacChar(text, tab, j)

        elif m == 1:
            j = ((byteArray[startIndex + i - 1] & 0x03) << 4) + ((byteArray[startIndex + i] & 0xF0) >> 4)
            (text, tab) = addDlacChar(text, tab, j)

        else:
            j = ((byteArray[startIndex + i - 1] & 0x0F) << 2) + ((byteArray[startIndex + i] & 0xC0) >> 6)
            (text, tab) = addDlacChar(text, tab, j)
            
            j = (byteArray[startIndex + i] & 0x3F)
            (text, tab) = addDlacChar(text, tab, j)

    return text.replace('~','')

# There are 3 forms of lat and long decoding, each with a different bit 
# length. These contants are used as the 'bitFactor' argument in
# convertRawLongitudeLatitude
GEO_24_BITS = 360.0/(2**24)
GEO_19_BITS = 360.0/(2**19)
GEO_18_BITS = 360.0/(2**18)

def convertRawLongitudeLatitude(rawLongitude, rawLatitude, bitFactor):
    """Convert raw coordinates to standard ones.

    Change native coordinates into normal longitude and latitude. The
    numbers are truncated to 6 decimal places since that approximates
    typical GPS coordinates.

    Args:
        rawLongitude (int): Longitude directly from data.
        rawLatitude (int): Latitude directly from data.
        bitFactor (float): Raw coordinates can be of different bit lengths.
            This is the conversion factor: the correct one is GEO_xx_BITS, where
            'xx' is the bit size of the raw data.

    Returns:
        tuple: Tuple of:
        
        1. longitude
        2. latitude
    """
    longitude = rawLongitude * bitFactor
    if longitude > 180:
        longitude = longitude - 360.0

    latitude = rawLatitude * bitFactor
    if latitude > 90:
        latitude = latitude - 180.0

    # Attempt to preserve only 6 places after the decimal (akin
    # to GPS precision)
    longitude = float('%.6f'%(longitude))
    latitude = float('%.6f'%(latitude))

    return (longitude, latitude)

def addDlacChar(str, tab, chr):
    """Add a DLAC character to the supplied ``str``.

    Tab characters in DLAC are actually a form of run-length encoding. The tab character is
    followed by the number of spaces to add.

    This is pretty much exclusively used by ``dlacToText()``.

    Args:
        str (str): Text string to add a character to.
        tab (bool): Boolean value, which if true, means ``tab`` contains the
            number of spaces to add (as opposed to adding the character ``chr``).
        chr (byte): DLAC character to add. If ``tab`` is ``True``, this is the number of
            spaces to add.

    Returns:
        tuple: Two values tuple return:
        
        1.  new string
        2.  new value of ``tab`` to be passed on the next
            call to ``addDlacChar()``.
    """
    if tab:
        # Test groups only seem to use 4 bits rather than 6 for tab
        if cfg.DLAC_4BIT_HACK:
            chr = chr & 0xF
        str += " " * chr
        tab = False
    elif chr == 28: #tab
        tab = True
    else:
        str += dlacString[chr]
    
    return (str, tab)

def createStationName(longitude, latitude):
    """Create station name from the station's longitude and latitude.

       For various purposes (ex: CRLs) we need the station the message
       came from. We also sometimes (for the standard) need to display
       the longitude and latitude of the station. This function justs
       appends the latitude to the longitude separated by a ``~``.
       It will work as a station ID and we can pull it apart for presenting
       the longitude and latitude of the station. 

       Note that both the ``longitude`` and ``latitude`` arguments will have
       their decimal points truncated to no more than 6.

       Args:
        longitude (float): Station's longitude
        latitude (float): Station's latitude

       Returns:
        str: Station string containing latitude concatinated to
        longitude, separated by a tilde (``~``).
    
    """
    # Just append the lat and long using '~'. That way, station
    # name can be used for coordinates (standard states you need
    # to show the coordinates at times).
    return str(latitude) + '~' + str(longitude)

def setTriggerList(trgrList):
    """Set the trigger list for testing.

    Args:
        trgrList (list): Trigger list to use. This is obtained from
            :func:`db.harvest.testing.createTriggerList`. See that
            function for the definition of list items.
    """
    global triggerList

    triggerList = trgrList

def checkForTrigger(utcSecs):
    """Check if any triggers have occurred before specified time.

        Will print any triggers that have occurred before specified
        time and remove them from the trigger list.

        Args:
            utcSecs (float): UTC time in seconds.
    """
    itemsToDelete = 0

    for triggerItems in triggerList:
        if triggerItems[0] < utcSecs:
            itemsToDelete += 1
            printTrigger(triggerItems)

    for _ in range(0, itemsToDelete):
        triggerList.pop(0)

def printAllTriggers():
    """Print any remaining triggers.

    Called at the end of a run to print any remaining triggers.
    """
    for triggerItems in triggerList:
        printTrigger(triggerItems)

def printTrigger(triggerItems):
    """Print a trigger item.

    Prints information about a trigger on standard output.
    
    Args:
        triggerItem (list)
    """
    dtTime = datetime.fromtimestamp(triggerItems[0], tz=timezone.utc)
    timeStr = dtTime.__format__('%Y-%m-%dT%H:%M:%S') +\
        '.{:03}Z'.format(int((triggerItems[0] % 1) * 1000))

    x = '#===========================================================' + \
        '\n# TRIGGER ({}): {} ({})\n#{}\n#'
    print(x.format(triggerItems[1], timeStr, triggerItems[3], triggerItems[2]), flush=True)
