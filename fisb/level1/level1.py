#!/usr/bin/env python3

"""Level1 attempts to match related messages together.

Level1 is related to two things:

1. Humpty Dumpty repair
2. Parents without Partners

Humpty Dumpty repair...
Takes segmented messages (mostly types 8 and 14) and stores
them in a queue until all the segments are received, then
sends out a single message.

Parents without Partners...
Processes TWGO message types 8, 11, 12, 15, 16 and 17, which
have a text portion and an optional graphics portion.
If the graphics portion comes in first we just hold onto it.
If the text portion comes in first, we send it out, but still
hold onto it. When both portions come in, we will send out a 
single message with both the text and graphic parts. The standard
demands that for certain types of messages we send out the text part
whenever it arrives. However, since the message gets retransmitted
periodically, we don't want to have a text portion sent out all
by itself again. See the documentation for :mod:`fisb.level1.TwgoMatcher`
for more details.

What comes out of level1.py?

All messages going into level1.py will come out of it, except for a number
of exceptions. A message is really a collection of frames. What actually
changes in level1.py are frames. Frames may be removed, added, or modified.
The outer message will be delivered intact except for changes to frames.

Frame changes:

1. TWGO messages of types 11, 12, 15, 16, and 17 will put any text contents
   inside the ``contents_text`` key in the output message and any 
   graphics contents as the ``contents_graphics`` key. Messages with both
   text and graphics will have both keys.

2. Segmented messages (``s_flag`` = 1) will not come out until all the segments
   are received and a complete message is produced.
"""

import sys, os, json, time, argparse, traceback, glob

import fisb.level1.level1Config as cfg
import fisb.level2.utilities as util2
from fisb.level1.Unsegmenter import Unsegmenter
from fisb.level1.TwgoMatcher import TwgoMatcher

# Last time we expunged items. Usually happens every 10 minutes
GLOBAL_lastExpungeTime = -1

# Results from frameAction
IGNORE = 0 # Don't add anything to the frame list
KEEP_NEW = 1 # Add returned frame to the frame list
KEEP_CURRENT = 2 # Add current frame to the frame list

# Initialize Unsegmented instance
unsegmenter = Unsegmenter(cfg.SEGMENT_EXPIRE_TIME)

# Initialize TWGO instance
twgoMatcher = TwgoMatcher(cfg.TWGO_EXPIRE_TIME)

def level1(msg, ppIndent):
    """Take FIS-B message and attempt to match it properly.

    Args:
        msg (dict): JSON string containing the message contents.
        ppIndent (int): This is the indent value handed to JSON.
            Usual values are 2 and ``None`` (for no indenting).

    Returns:
        dict: message dictionary, or ``None`` if message should be skipped.
    """
    global GLOBAL_lastExpungeTime

    # Decode the JSON message into a dictionary
    msgDict = json.loads(msg)

    currentTime = util2.iso8601ToSeconds(msgDict['rcvd_time'])

    # Get the list of frames
    frames = msgDict['frames']
        
    # See if there are any frames, if not just return the message
    numFrames = len(frames)
    if numFrames == 0:
        return msg

    # frameLoop goes through all the frames and
    # will return a modified list of frames. Removing
    # some, and adding others.
    # It is called one time for each of the message
    # types we need to try and group together.

    # Segmented frames need to happen first since they
    # may return frames needed for processes that happen
    # after.
    newFrameList = frameLoop(frames, \
                              frameTestSegmented, \
                              frameActionSegmented, \
                              currentTime)

    # TWGO  (type 8, 11, 12, 15, 16, 17).
    newFrameList = frameLoop(newFrameList, \
                              frameTestTwgo, \
                              frameActionTwgo, \
                              currentTime)

    # Update the message with the new frame list.
    msgDict['frames'] = newFrameList

    # See if time to expunge items
    if GLOBAL_lastExpungeTime != -1:
        if (currentTime - GLOBAL_lastExpungeTime) > \
           (cfg.EXPUNGE_CHECK_MINUTES * 60):

            # Run expunger for all message types
            unsegmenter.expungeItems(currentTime)
            twgoMatcher.expungeItems(currentTime)

            GLOBAL_lastExpungeTime = currentTime
    else:
        # Set once for each program run
        GLOBAL_lastExpungeTime = currentTime
        
    # Turn the modified object (or not) back into a JSON string.
    return json.dumps(msgDict, indent = ppIndent)

def frameTestSegmented(frame):
    """Test for segmented messages.

    Args:
        frame (dict): Frame to test
    
    Returns:
        bool: ``True`` if this is a segmented message, else ``False``.
    """
    # Ignore non-segmented messages
    if frame['s_flag'] != 1:
        return False
    return True

def frameActionSegmented(frame, currentTime):
    """Process segmented message.

    Args:
        frame (dict): Frame to process.
        currentTime (int): Current time, seconds since 1970.

    Returns:
        tuple: Tuple of two items. Either:
        
        * (``KEEP_NEW``, new-message) if we have
          reconstructed a segmented message. Or:
        * (``IGNORE``, ``None``) if no new message.
    """
    # newMsg is None if this msg didn't complete the series
    # or a new frame item for returning.
    newMsg = unsegmenter.processFrame(frame, currentTime)

    if newMsg is not None:
        return (KEEP_NEW, newMsg)
    else:
        return (IGNORE, None)

def frameTestTwgo(frame):
    """Test for TWGO messages (type 8, 11, 12, 15, 16, 17)

    *G-AIRMET* (type 14) messages are also TWGO messages. But since
    they only have a graphics section, they are not worried about by 
    *level1*. *SUA* (type 13) have only text.

    Args:
        frame (dict): Frame to test
    
    Returns:
        bool: ``True`` if this is a TWGO message, else ``False``.
    """
    # Ignore non-TWGO messages
    if (frame['product_id'] in [8, 11, 12, 15, 16, 17]):
        return True
    return False

def frameActionTwgo(frame, currentTime):
    """Process TWGO message (types 8, 11, 12, 15, 16, 17)

    Args:
        frame (dict): Frame to process
        currentTime (int): Current time, seconds since 1970.

    Returns:
        tuple: Tuple of two items. Either:
        
        * (``KEEP_NEW``, new-message) if we have
          reconstructed a segmented message. Or:
        * (``KEEP_CURRENT``, ``None``) if no new message and we should keep
          the current one.
    """
    # newMsg is None if this wasn't a TWGO with
    # a matching graphic. Just send it along.
    newMsg = twgoMatcher.processFrame(frame, currentTime)

    if newMsg is not None:
        return (KEEP_NEW, newMsg)
    else:
        return (IGNORE, None)

def frameLoop(frames, frameTest, frameAction, currentTime):
    """Loop over all frames and process them, returning new frame list.

    Called for each type of message we wish to process.

    Args:
        frames (list): List of frames from message.
        frameTest (function): Function that tests if this message is
            a type of message ``frameAction`` should process.
        frameAction (function): Function that processes the frame and
            returns a tuple describing what to do with any message returned.
        currentTime (int): Current time, seconds since 1970.

    Returns:
        list: List of modified frames with changes.
    """
    newFrameList = []

    for frame in frames:
        # Only APDU frames are even considered. All others
        # just get passed through.
        if frame['frame_type'] != 0:
            newFrameList.append(frame)
            continue

        # See if frame passes our supplied test.
        if not frameTest(frame):
            newFrameList.append(frame)
            continue    

        # Did pass the test. Not process the message using
        # supplied function.
        (action, resultFrame) = frameAction(frame, currentTime)

        if action == IGNORE:
            pass
        elif action == KEEP_CURRENT:
            newFrameList.append(frame)
        elif action == KEEP_NEW:
            newFrameList.append(resultFrame)

    return newFrameList

def dumpRecord(reason, line):
    """Write current msg to the error file for any decoding issues.

    Args:
        reason (str): Explanation of the error.
        line (str): message to dump.
    """
    with open(cfg.ERROR_FILENAME, "a") as f:
        f.write("-------------------------------------------------------------\n")
        f.write("#" + reason + "\n")
        f.write(json.dumps(json.loads(line), indent = 2) + "\n\n")

def processLine(line, ppIndent):
    """Process a line through level1, catching exceptions.

    Args:
        line (str): String containing message.
        ppIndent (int): This is the indent value handed to JSON.
            Usual values are 2 and ``None`` (for no indenting).

    Raises:
        Exception: For any error.
    """
    try:
        print(level1(line, ppIndent), flush=True)

    except Exception as _:
        # Error, place in errored out message file
        errList = traceback.format_exc(limit=10)
        errStr = errList.replace("\n", "\n# ")
        dumpRecord(errStr, line)

if __name__ == "__main__":
    ## --- Script Code ---##
    parser = argparse.ArgumentParser(description= \
                                 """
                                 Filter FIS-B messages and perform the following:

                                 1) De-segment messages
                                 2) Join TWGO messages with graphics
                                 """)
    parser.add_argument('--pp', help="Pretty Print output. Can't be set if it will be parsed by JSON.", action='store_true')
    args = parser.parse_args()

    # ppIndent: Number of spaces to indent JSON string. 2 for indenting 2, None for no indent.
    # Note: To feed the output to another level, indent must be None. Python JSON can't read a
    # JSON string if it isn't on a single line.
    ppIndent = None
    if args.pp:
        ppIndent = 2

    if cfg.READ_MESSAGES_FROM_FILE:
        # Read all messages from file.
        path = os.path.join(cfg.READ_MESSAGES_DIRECTORY, '*.msg')

        while True:
            fileList = sorted(glob.glob(path))
            if len(fileList) == 0:
                time.sleep(1)
                continue
        
            for f in fileList:
                # Open and read contents. Contents are assumed
                # to be single line JSON string.
                with open(f, 'r') as fileIn:
                    line = fileIn.read()

                # Remove file from directory
                os.remove(f)

                # Process
                line = line.strip()
                processLine(line, ppIndent)
    else:
        # Read from stdin
        for line in sys.stdin:
            line = line.strip()

            # Skip over blank lines pass along comments
            if len(line) == 0:
                continue
            if (line[0] == '#'):
                print(line, flush=True)
                continue            

            processLine(line, ppIndent)
