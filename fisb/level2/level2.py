#!/usr/bin/env python3

"""Produce individual complete messages.

Level2 takes the messages you got and makes them the messages
you wish you got.

This is the first level that breaks messages out of the FIS-B
standard message structure into individual complete messages
organized by content.

Much work is done to go on scavenger hunts to track down information
to make complete timestamps for all time values. This is why we
need timestamps showing when a message was received. FAA 
times usually have only the day of the month and hour in
UTC. For APDUs, you can get even less: maybe just an hour and minute.
If we are receiving these messages in real time, we can
figure out the rest. However, for testing and debugging, we 
store up large amounts of messages and process them in bulk. In this
case, knowing the message received time is essential, since the
current time may be very different.

There is no check for duplication at this level. However, in level
3, the messages are hashed and stored so
that duplicate messages can be detected easily.

Any messages that should not be decoded (according to DO-358B)
will be flushed at this level (unless you have the configuration files
set to allow ``SUA`` messages).
"""
import sys, os, json, time, argparse, traceback, pprint

import fisb.level2.level2Config as cfg
import fisb.level2.level2Exceptions as ex
import fisb.level2.utilities as util

from fisb.level2.msgBlock import msgBlock
from fisb.level2.msg413 import msg413
from fisb.level2.msgCrl import msgCrl
from fisb.level2.msgServiceStatus import msgServiceStatus
from fisb.level2.msg8_16_17 import msg8_16_17
from fisb.level2.msg11_12_15 import msg11_12_15
from fisb.level2.msg14 import msg14
from fisb.level2.msg13 import msg13

def dumpRecord(reason, frame):
    """Write current frame to the error file for any decoding issues.

    Args:
        reason (str): Error description.
        frame (dict): Dictionary containing frame to display.
    """
    with open(cfg.ERROR_FILENAME, "a") as f:
        f.write("-------------------------------------------------------------\n")
        f.write("#" + reason + "\n")
        msgJson = json.dumps(frame, indent = 2)
        f.write(msgJson + "\n\n")

def TwgoSanityCheck(frameSection, frame):
    """Return ``True`` if TWGO message contains valid values, else ``False``.

    We check that the 'record format' is 2 or 8 and the 'record reference point' is 0 or 255.

    Args:
        frameSection (str): One of '``contents``', '``contents_text``' or '``contents_graphics``'
        frame (dict): TWGO message frame.

    Returns:
        bool: True if passes checks, else False.
    """
    # Standard says ignore record_format if not 2 or 8
    framePart = frame[frameSection]
    recordFormat = framePart['record_format']
    if not ((recordFormat == 2) or \
                (recordFormat == 8)):
        return False

    # Standard says ignore record_reference_point if not 0 or 255
    recordReferencePoint = framePart['record_reference_point']
    if not ((recordReferencePoint == 0) or \
                (recordReferencePoint == 255)):
        return False

    return True

def level2(msg, ppIndent):
    """Process level 2 messages.

    Takes level 1 messages and turns them into level 2 messages.
    
    Sends zero to many messages to standard output or a file
    depending on configuration (i.e. a single level 1
    message may become 0 to many level2 messages).

    The output from level 2 is then usually sent to level 3.

    Args:
        msg (str): JSON string of the message from level 1.
        ppIndent (int): Number of characters to indent for pretty printing.

    Raises:
        Exception: For any errors detected. All errors are placed in an error file.
    """
    msg = json.loads(msg)

    # Flush message if app_data_valid is not 1.
    if msg['app_data_valid'] != 1:
        return

    # There should also be a check here for 'position_valid'.
    # However, at my site this is always sent as '0' or
    # INVALID. If I handled this as per the standard,
    # no messages would be sent out. It is unknown how it is set
    # at other sites.
    ##if msg['position_valid'] != 1:
    ##    return

    # Get the time the message was received
    # Break it into rYear, rMonth, rDay, rHour
    # and rMin so we don't to reparse it for each frame.
    rcvdTime = msg['rcvd_time']
    station = msg['station']
    rYear = int(rcvdTime[0:4])
    rMonth = int(rcvdTime[5:7])
    rDay = int(rcvdTime[8:10])
    rHour = int(rcvdTime[11:13])
    rMin = int(rcvdTime[14:16])
    
    # rcvdTime is in microseconds, which we don't need at this point.
    # Convert to seconds
    rcvdTime = rcvdTime[0:19] + 'Z'

    frames = msg['frames']
        
    # See if there are any frames
    numFrames = len(frames)
    if numFrames == 0:
        return

    for frame in frames:
        # msg will get any completed message
        msg = None

        try:
            # Handle frame types 0 (APDU) and 14 (CRL) only
            frameType = frame['frame_type']
            if frameType == 0:
                # APDU

                # Collect the date/time info. There are a few cases
                # (like winds aloft forecast) where this is different
                # and important from time in FAA time strings.
                tOpt = frame['t_opt']

                if tOpt == 2:
                    month = frame['month']
                    day = frame['day']
                else:
                    month = -1
                    day = -1

                hour = frame['hour']
                minute = frame['minute']

                # Error if s_flag is not 0. That would imply someone
                # sent us level0 instead of level1 messages.
                if frame['s_flag'] != 0:
                    raise ex.SegmentedMessageException("Segmented messages illegal at level2")

                # Dispatch on product_id
                productId = frame['product_id']

                # TWGO Sanity checks
                if productId in [8, 11, 12, 13, 14, 15, 16, 17]:
                    if ('contents' in frame) and not TwgoSanityCheck('contents', frame):
                        continue
                    if ('contents_text' in frame) and not TwgoSanityCheck('contents_text', frame):
                        continue
                    if ('contents_graphics' in frame) and not TwgoSanityCheck('contents_graphics', frame):
                        continue

                # Process all frame type 0 messages based on product id.

                # Text messages
                if (productId == 413):
                    msg = msg413(frame, rYear, rMonth, rDay, \
                    rHour, rMin, \
                    hour, minute, rcvdTime)

                # G_AIRMET, SUA messages
                elif productId in [13, 14]:
                    
                    recordCount = frame['contents']['record_count']

                    if productId == 13:
                        msg = msg13(frame['contents']['records'][0], \
                                    rYear, rMonth, rDay)

                    elif productId == 14:
                        msg = msg14(frame['contents']['records'], \
                                    recordCount, productId, \
                                    rYear, rMonth, rDay, rHour, rMin, \
                                    month, day, hour, minute, station, rcvdTime)

                elif productId in [11, 12, 15]:
                    # Standard TWGO checks

                    msg = msg11_12_15(frame, \
                                          productId, \
                                          rYear, rMonth, rDay, rHour, rMin, \
                                          month, day, hour, minute, station, rcvdTime)                        

                # NOTAM type messages
                elif productId in [8, 16, 17]:
                    if 'contents_graphics' in frame:
                        contents_graphics = frame['contents_graphics']
                    else:
                        contents_graphics = None
    
                    msg = msg8_16_17(frame['contents_text'], \
                            contents_graphics, productId, \
                            rYear, rMonth, rDay, \
                            month, day, hour, minute, station, rcvdTime)
                            
                # Global Block messages
                elif productId in [63, 64, 103, 84, 70, 71, 90, 91]:
                    # Block messages are slightly different in that
                    # under certain circumstances, a single empty block
                    # message can generate multiple output messages.
                    # We output the messages here and set msg to
                    # None.
                    msgList = msgBlock(frame['contents'], productId, \
                                   rYear, rMonth, rDay, rHour, rMin,
                                   hour, minute)

                    for x in msgList:
                        msgJson = json.dumps(x, indent = ppIndent)
                        print(msgJson, flush=True)

                    msg = None
                else:
                    raise ex.BadProductIdException("Unknown product id of {}".format(productId))
            
            elif frameType == 14:
                # CRL
                msg = msgCrl(rcvdTime, frame, station)
            
            elif frameType == 15:
                # Service Status
                msg = msgServiceStatus(rcvdTime, frame, station)
            
        except Exception as _:
            # Error, place in errored out message file
            errList = traceback.format_exc(limit=10)
            errStr = errList.replace("\n", "\n# ")
            dumpRecord(errStr, frame)
            
        # Send any completed message out
        if msg is not None:
            msgJson = json.dumps(msg, indent = ppIndent)
            print(msgJson, flush=True)

if __name__ == "__main__":
    ## --- Script Code ---##
    parser = argparse.ArgumentParser(description= \
                                     """
                                     Filter FIS-B messages into forms suitable for storage.
                                     """)
    parser.add_argument('--pp', help="Pretty Print output. Can't be set if it will be parsed by JSON.", action='store_true')
    args = parser.parse_args()

    # ppIndent -- number of spaces to indent JSON string. 2 for indenting 2, None for no indent.
    # Note: To feed the output to another level, indent must be None. Python JSON can't read a
    # JSON string if it isn't on a single line.
    ppIndent = None
    if args.pp:
        ppIndent = 2

    # Main loop
    for line in sys.stdin:
        line = line.strip()

        if len(line) > 0:
            if line[0] == '#':
                # Pass along comments.
                print(line, flush=True)
                continue

        level2(line, ppIndent)
