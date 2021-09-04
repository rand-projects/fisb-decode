"""Create a text summary of a level 0 message.
"""

import time, pprint
import json
import sys

# Default text for product ids. Some of these are used as
# is, but some are modified to provide more detailed information.
PRODUCT_TYPES = {
    413:    'GENERIC TEXT',
    63:     'REGIONAL NEXRAD',
    64:     'NEXRAD CONUS',
    70:     'ICING',
    71:     'ICING',
    84:     'CLOUD TOPS',
    90:     'TURBULENCE',
    91:     'TURBULENCE',
    103:    'LIGHTNING',
    8:      'NOTAM',
    13:     'SUA',
    11:     'AIRMET',
    12:     'SIGMET',
    14:     'G-AIRMET',
    15:     'CWA',
    16:     'NOTAM-TRA',
    17:     'NOTAM-TMOA'
}

def detectGraphicsTwgoCancelled(frame):
    """Return an empty string if there is no cancelled message in this
    graphical TWGO frame. Otherwise return string with cancellation details.

    Args:
        frame (dict): Contains a graphics TWGO frame.

    Returns:
        (str):  '' if there is no cancellation associated
            with this frame, otherwise will be a string
            with information about the cancellation.
    """
    if 'records' in frame['contents']:
        records = frame['contents']['records']
        for x in records:
            if 'object_status' in x:
                if x['object_status'] == 13:
                    return ' [CANCELLED {}-{}]'.format(x['report_year'],\
                        x['report_number'])    
    return ''
    
def detectTextTwgoCancelled(frame):
    """Return an empty string if there is no cancelled message in this
    text TWGO frame. Otherwise return string with cancellation details.

    Args:
        frame (dict): Contains a text TWGO frame.

    Returns:
        (str):  '' if there is no cancellation associated
            with this frame, otherwise will be a string
            with information about the cancellation.
    """

    location = ''
    if 'location' in frame['contents']:
        location = (frame['contents']['location']).strip()
        if len(location) > 0:
            location = '-' + location

    if 'records' in frame['contents']:
        records = frame['contents']['records']
        for x in records:
            if 'report_status' in x:
                if x['report_status'] == 0:
                    return ' [CANCELLED {}-{}{}]'.format(x['report_year'],\
                        x['report_number'], location)    
    return ''
    
def detectEmptyTFR(frame):
    """'Empty' TFRs are NOTAM-TFRs which are NOTAM-TFRs that have been
    sent previously, and are active, but which every other cycle is sent
    with no text-- Just with it's number, an empty text field, and an
    indication that it is still active.

    Args:
        frame (dict): Frame with product id of 8.

    Returns:
        Empty string if this cannot be an empty TFR. Otherwise, a
        frame-string indicating that it is an EMPTY TFR.
    """
    if 'records' in frame['contents']:
        records = frame['contents']['records']
        for x in records:
            # Skip cancelled messages
            if ('report_status' in x) and (x['report_status'] == 0):
                continue
            
            if ('text' in x) and (x['text'] == ''):
                return ' [EMPTY TFR {}-{}]'.format(x['report_year'],\
                    x['report_number'])
    return ''
    
def makeNotamTypeMoreSpecific(frame):
    """Attempt to make product-ids of 8 (NOTAM) more specific.

    Args:
        frame (dict): Dictionary containing a NOTAM frame.

    Returns:
        (str):  String containing a more specific type of NOTAM
            (if possible). NOTAM-D and NOTAM-FDC are the most
            common upgrades. Usually NOTAM-TFRs are multi-segmented
            and don't show up in level 0 messages. We do note if a
            NOTAM-D is associated with SUA.
    """
    if 'records' in frame['contents']:
        records = frame['contents']['records']
        for x in records:
            if 'text' in x:
                text = x['text']
                if text.startswith('NOTAM-FDC'):
                    return 'NOTAM-FDC'

                if text.startswith('FIS-B'):
                    return 'FIS-B UNAVAILABLE'

                if text.startswith('NOTAM-D'):
                    if '!SUA' in text:
                        return 'NOTAM-D/SUA'
                    else:
                        return 'NOTAM-D'

    return 'NOTAM'

def makeFrameStringTag(frame):
    """Make a string that represents the value of this frame.

    Frame strings are meant to mostly be generic, but we will
    make more specific ones for special cases.

    Args:
        frame (dict): Dictionary containing current frame.

    Returns:
        (str): Single line string describing frame.
    """
    frameType = frame['frame_type']

    # Service Status Frame.
    # Return number of targets.
    if frameType == 15:
        return 'SERVICE-STATUS (targets: {})'.format(len(frame['contents']))

    # CRL Frame.
    # Return number of reports and type of report.
    if frameType == 14:
        productId = frame['product_id']
        numberOfReports = frame['number_of_reports']
        return 'CRL for {} [{} reports]'.format(\
            PRODUCT_TYPES[productId], numberOfReports)

    # Regular FIS-B frame.
    if frameType == 0:
        productId = frame['product_id']

        # Get basic product-id.
        productIdText = PRODUCT_TYPES[productId]

        # Check for segmented APDU.
        # If it is, print status and return, there is no further information
        # contained within.
        if 'product_file_id' in frame:
            productIdText = '{} (segmented {}/{} of {})'.format(\
                productIdText, frame['product_file_id'], frame['apdu_number'],\
                frame['product_file_length'])
            return productIdText

        # Make generic text products more specific.
        if productId == 413:
            contents = frame['contents']

            if contents.startswith('WINDS'):
                return 'WINDS'
            if contents.startswith('METAR'):
                return 'METAR'
            if contents.startswith('SPECI'):
                return 'SPECI'
            if contents.startswith('PIREP'):
                return 'PIREP'
            if contents.startswith('TAF.AMD'):
                return 'TAF.AMD'
            if contents.startswith('TAF'):
                return 'TAF'

            return 'Generic Text Unknown Type'

        # Add altitude to Icing and Turbulence.
        if productId in [70, 71, 90, 91]:
            productIdText = productIdText + '-' + \
                str(frame['contents']['altitude_level'])

        # Add empty blocks to all images.
        if productId in [63, 64, 70, 71, 84, 90, 91, 103]:
            if 'empty_blocks' in frame['contents']:
                productIdText = productIdText + ' (empty blocks)'

        # Add (text) or (graphics) to TWGO
        if productId in [8, 11, 12, 14, 15, 16, 17]:
            if 'record_format' in frame['contents']:
                if frame['contents']['record_format'] == 8:
                    # Graphical Record.

                    productIdText += ' (graphics)'

                    # See if there is a cancelled record here.
                    productIdText += detectGraphicsTwgoCancelled(frame)
                else:
                    # Text Record.
                    
                    # Make NOTAM types more specific if possible
                    if productId == 8:
                        productIdText = makeNotamTypeMoreSpecific(frame)

                    productIdText += ' (text)'

                    # See if there is a cancelled record here.
                    productIdText += detectTextTwgoCancelled(frame)

                    # See if this is an empty TFR message (every other
                    # TFR sent is just a placeholder).
                    if productId == 8:
                        productIdText += detectEmptyTFR(frame)

        return productIdText

    # Should not reach here.
    return ('UNKNOWN FRAME')

def createSummary(msg):
    """Create and return a text summary of ``msg``.

    The first line of the message is the message timestamp, followed
    by a header line and then one line for each type of data in the message.
    Each line in the message starts with '#' so that these lines
    are considered comments.

    Args:
        msg (dict): Dictionary containing level 0 message.

    Returns:
        str:    String containing summary of ``msg``.

    """
    frameStringDict = {}

    frames = msg['frames']
    numFrames = len(frames)

    if numFrames == 0:
        frameString = '[no frames]'
    elif numFrames == 1:
        frameString = '[1 frame]'
    else:
        frameString = '[{} frames]'.format(numFrames)

    # Put message sequence in header if available (you must
    # have  DETAILED_MESSAGES set to True in the configuration
    # for this to work).
    secSeq = ''
    if 'sequence_this_second' in msg:
        secSeq = '/{}'.format(msg['sequence_this_second'])

    # Create header string.
    headerString = '# \n# ' + msg['rcvd_time'] + \
        secSeq + ' (' + msg['station'] + ') ' +\
        frameString + '\n'
    
    # Just return if no frames to process.
    if numFrames == 0:
        return headerString

    # Add title string.
    headerString += '#\n# ' + \
        'Count FT ProdId  Description\n# ' + \
        '----- -- ------  -----------------------------------\n'

    # For every frame, produce a frame-line. Put the line in a
    # dictionary whose 'key' is the frame-line and whose value
    # is the count of the number of times this line has appeared.
    for x in frames:
        # Create the frame string to use.
        frameStringTag = makeFrameStringTag(x)

        # Frame type 15 (SERVICE-STATUS) has no concept of 
        # product_id and this value will get over-ridden for all
        # other frame types (0 and 14).
        productIdString = 'N/A'
        if 'product_id' in x:
            productIdString = '{:3d}'.format(x['product_id'])

        frameString = '{:02d}    {}  {}'.format(x['frame_type'], productIdString, \
            frameStringTag)

        # Add to dictionary
        if frameString in frameStringDict:
            cnt = frameStringDict[frameString]
            frameStringDict[frameString] = cnt + 1
        else:
            frameStringDict[frameString] = 1

    # Loop through the dictionary and create a string with
    # one line for each unique frame-line and its count.
    itemString = ''
    for key, value in frameStringDict.items():
        itemString = itemString + '# ' + \
            '  {:3d} {}\n'.format(value, key)

    return headerString + itemString
