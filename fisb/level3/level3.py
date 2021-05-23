#!/usr/bin/env python3

"""Deduplicate messages and send to standard output or file.

Level3 exists solely to decrease the workload for backend
processors like Harvest. It will store certain messages
and send then only once if they have not changed.

Level3 accepts level2 messages as input. **It makes no changes
to level2 messages.** It just stores them if indicated.

The basic concept is that FIS-B will send a message out when
it is new, but it will also send a message every so many
minutes as a retransmission. These are the messages level3
is trying to stop. If you are receiving messages from more than
one station, level3 will also help.

See the comments for the ``Deduplicator`` class on how all this
works (spoiler alert: message digests).

Messages that always get stored in level3:

* METAR
* TAF
* WINDS
* Any Image (messages with blocks). By the time any
  image block gets here, it has been expanded from its
  empty block form by level 2. Each block is considered
  its own message. So if some portions of an image are 
  not received during the first transmission, they will
  be picked up during subsequent transmissions and send along. If you
  are getting images from more than one station, level3
  will block the duplicates.
* SUA (if not blocked per standard recommendations)
  
Messages that never get stored in level3 (basically
any message with an associated CRL and a few
extra types):

* NOTAM
* NOTAM_TFR
* AIRMET
* SIGMET
* WST
* CWA
* CRL
* SERVICE_STATUS
* FIS-B UNAVAILABLE
* RSR (RSR never makes it here. It goes to the database from level0.)

Messages that may or may not get stored in level3:

* PIREP 
  Except for running the test messages,
  it is recommended PIREP messages get stored. This decreases
  having to rerun the code to add location information for 
  each retransmission (if you have that turned on in Harvest).
  ``cfg.PIREP_STORE_LEVEL3`` controls this.
"""
import sys, os, json, time, argparse, traceback

import fisb.level3.level3Config as cfg
import fisb.level3.utilities as util

from fisb.level3.Deduplicator import Deduplicator

# If True will print to standard output, otherwise not.
# Initially taken from config, but can be over-ridden by
# '--todir'
print_to_stdout = cfg.PRINT_TO_STDOUT

# If True will write output to directory, otherwise not.
# Initially taken from config, but can be over-ridden by
# '--todir'
write_to_file = cfg.WRITE_TO_FILE

# Directory to write files to if specified.
# Initially taken from config, but can be over-ridden by
# '--todir'
output_directory = cfg.OUTPUT_DIRECTORY

# Initialize Deduplicator object
deduplicator = Deduplicator(cfg.EXPIRE_MSG_TIME_MINS, \
                            cfg.EXPUNGE_HASHTABLE_MINS)

def bypassLevel3(msg):
    """Determine if supplied message should bypass level3 (i.e. not get stored)

    Uses the message's ``type`` key to make this determination.

    Args:
        msg (dict): Message to be evaluated.
    
    Returns:
        bool: ``True`` if this message should be bypassed (not stored).
          Else ``False`` if it should be stored.
    """
    msgType = msg['type']

    if msgType == 'FIS_B_UNAVAILABLE':
        # Always bypass FIS_B_UNAVAILABLE
        return True
        
    elif msgType == 'PIREP':
        # PIREPS are safe to store and let them expire based on the
        # initial expiration time. The standard demands expiration 
        # 75 minutes (or more) after last transmission.
        return False if cfg.PIREP_STORE_LEVEL3 else True

    elif (msgType in ['NOTAM', 'NOTAM_TFR', 'AIRMET', 'SIGMET', 'WST', 'CWA']) \
            or (msgType.startswith('G_AIRMET')):
        # TWGO. Standard says keep for 60 minutes after last transmission, with
        # option to use stop_time as expiration. Don't store.
        return True
        
    elif (msgType in ['CRL', 'SERVICE_STATUS']):
        return True

    return False
    
def level3(msg, ppIndent):
    """Process message and check if duplicate. Write to STD_OUT or file.

    Args:
        msg (str): JSON string of a message from level2.
        ppIndent (int): Number of characters to indent for pretty printing.
    """
    try:
            
        # See if we need to bypass level3 for this message.
        jmsg = json.loads(msg)            
        if bypassLevel3(jmsg) or deduplicator.okToSendMsg(msg):
            if print_to_stdout:
                # Message is a string. It we want it pretty printed
                # we need to convert to a json message
                if ppIndent is not None:
                    print(json.dumps(jmsg, indent = ppIndent),flush=True)
                else:
                    print(msg, flush=True)

            if write_to_file:
                util.writeToFile(msg, output_directory)

    except Exception as _:
        # Error, place in errored-out message file
        errList = traceback.format_exc(limit=10)
        errStr = errList.replace("\n", "\n# ")
        dumpRecord(errStr)
            
def dumpRecord(reason):
    """Write exception to the error file for any decoding issues.

    Args:
        reason (str): String describing the error.
    """
    with open(cfg.ERROR_FILENAME, "a") as f:
        f.write("-------------------------------------------------------------\n")
        f.write("#" + reason + "\n\n")

if __name__ == "__main__":
    ## --- Script Code ---##
    parser = argparse.ArgumentParser(description= \
                                     """
                                     Deduplicate FIS-B messages.
                                     """)
    parser.add_argument('--pp', \
        help="Pretty Print output. Can't be set if it will be parsed by JSON." + \
            " Will force printing to stanadard output and not write to a file.", \
        action='store_true')   
    parser.add_argument('--dir', \
        help="Send output to directory specified.", \
        type=str)
    args = parser.parse_args()

    # ppIndent -- number of spaces to indent JSON string. 2 for indenting 2, None for no indent.
    # Note: To feed the output to another level, indent must be None. Python JSON can't read a
    # JSON string if it isn't on a single line.
    ppIndent = None
    if args.pp:
        ppIndent = 2

        # If we are pretty printing, force output to the terminal
        print_to_stdout = True
        write_to_file = False

    # --toDir is normally used when producing output stored in directories waiting to be harvested
    # into a database. Overrides cfg.PRINT_TO_STDOUT and cfg.WRITE_TO_FILE.
    if args.dir:
        print_to_stdout = False
        write_to_file = True

        output_directory = args.dir

        # Strip any trailing /
        if output_directory[-1] == '/':
            output_directory = output_directory[:-1]

    # Main loop
    for line in sys.stdin:
        line = line.strip()

        # Pass along any comments. Mostly used for testing.
        if line[0] == '#':
            print(line, flush = True)
            continue

        level3(line, ppIndent)
