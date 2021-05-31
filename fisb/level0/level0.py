#!/usr/bin/env python3

"""Process raw messages from FlightAware's dump978.

The majority of the code in this module is in the actual
script part of this file, not in a function.
"""

import os, io, sys, json, argparse, traceback

import fisb.level0.level0Config as cfg
import fisb.level0.level0Exceptions as ex
import fisb.level0.utilities as util

# Only import if harvest requirements are installed.
if cfg.ALLOW_DECODE_TEST:
    import db.harvest.testing as test

# Only import pymongo if using RSR
if cfg.CALCULATE_RSR:
    from pymongo import MongoClient
    from pymongo import errors

from fisb.level0.ground_uplink_message import groundUplinkMessage
from fisb.level3.utilities import writeToFile

def miniDump(payload):
    """For errors, display simple hex dump of message.

    For *level0*, where we are still dealing in bytes, 
    ``miniDump`` provides a very simple dump of the message that
    divides the message into hex parts. Specifically,
    the ground uplink header and frame pieces.

    The first line starts with an ``H`` and contains the
    ground uplink header (8 bytes).

    All lines after that start with ``F`` and contain the frame
    type as a decimal number (0-15) followed by the frame in
    hex. If the frame is of type 0 (APDU), that fact and the
    product id will be displayed on the next line.

    Args:
        payload (str): String from 978dump-fa decoder containing a FIS-B line.
          All other types are return a string showing they cannot be processed.

    Returns:
        str: String containing the mini dump.
    """
    result = ''

    # Make sure this is a valid FIS-B message
    if (len(payload) == 0) or \
        (payload[0] != '+'):
        return '*** Mini Dump not possible. Not FIS-B message.\n'

    payload = payload[1:payload.index(';')]

    # Create byte array containing entire message.
    try:
        ba = bytes.fromhex(payload)        
    except Exception:
        return '*** Mini Dump not possible. Payload contains non-hex characters.\n'

    # Better be 432 characters
    if len(ba) != 432:
        return '*** Mini Dump not possible. Wrong length. Malformed?\n'

    result += 'H    {}\n'.format(ba[0:8].hex())

    # relative offset
    ros = 8

    while (True):
        if ros >= 431:
            break

        frameLength = (ba[ros] << 1) | ((ba[ros+1] & 0x80) >> 7)

        if frameLength == 0:
            break

        frameType = ba[ros + 1] & 0x0F

        result += 'F {:2d} {}\n'.format(frameType, ba[ros:ros + frameLength + 2].hex())

        if frameType == 0:
            apduType = ((ba[ros + 2] & 0x1F) << 6) | \
                ((ba[ros + 3] & 0xFC) >> 2)
            result += '     APDU {}\n'.format(apduType)

        ros += frameLength + 2

    return result

def dumpRecord(reason, msg):
    """Write current msg to the error file for any decoding issues.

    Args:
        reason (str): Reason the message failed.
        msg (str): Failed message.
    """
    with open(cfg.ERROR_FILENAME, "a") as f:
        f.write("#--------------------------------------------------\n")
        f.write("#" + reason + "\n")
        f.write(msg + "\n\n")

if __name__ == "__main__":
    #----------------------------------------------------------------------------#
    # M A I N   C O D E   B L O C K
    #----------------------------------------------------------------------------#

    parser = argparse.ArgumentParser(description= \
                                     """
                                     Take dump978 messages and decode into JSON
                                     """)
    parser.add_argument('--pp', help="Pretty Print output", action='store_true')
    parser.add_argument('--dump', help="Dump for testing use", action='store_true')

    if cfg.ALLOW_DECODE_TEST:
        parser.add_argument('--test', \
            choices=range(1,31), \
            help="Dump specified test group.", \
            type=int)
    
    args = parser.parse_args()

    ppIndent = None
    if args.pp:
        ppIndent = 2

    dumpMode = False
    if args.dump:
        ppIndent = 2
        dumpMode = True

    testMode = False
    buffer = sys.stdin.buffer

    if cfg.ALLOW_DECODE_TEST and args.test:
        testNumber = args.test
        testMode = True

        if (testNumber < 1) or (testNumber > 30):
            raise ex.BadTestNumberException('Test Number {} out of range.'.format(testNumber))

        triggerList = test.createTriggerList(testNumber)
        util.setTriggerList(triggerList)
        testFilePath = os.path.join(cfg.GENERATED_TEST_DIR, 'tg{:02d}.978'.format(testNumber))
        buffer = open(testFilePath,'rb')

    inStream = io.TextIOWrapper(buffer, encoding='ISO-8859-1')

    isDetailed = cfg.DETAILED_MESSAGES

    # Initially set to false, the first time through this will force open the
    # file (then be set to True and never executed again).
    # We take the name of the file from the message, so we don't actually
    # know the name of the file ahead of time.
    archivingStarted = False

    # Holds the name of the file we are archiving to. Will be of the form
    # 'yyyymmdd'
    archiveFileName = ''

    # File handle for archive file
    archiveFile = None

    # items used for RSR that have to be present between messages
    rsrDict = None
    if cfg.CALCULATE_RSR:

        rsrDict = {'last_sec': -1, \
                    'cur_sec': -1, \
                    'total_secs': 0, \
                    'time_dict': {}}

        # Open mongo db
        client = MongoClient(cfg.MONGO_URI, tz_aware=True)
        rsrDict['db'] = client.fisb

    for line in inStream:
        line = line.strip()

        try:
            # Note: this will skip comments and blank lines (or lines
            # that don't start with a '+')
            if len(line) == 0:
                continue
            elif line[0] == '#':
                continue
            elif line[0] == '+':
                if dumpMode:
                    print(line, flush=True)

                msg = groundUplinkMessage(line, isDetailed, testMode, rsrDict)

                if msg is not None:
                    jsonMsg = json.dumps(msg, indent = ppIndent)

                    if cfg.WRITE_MESSAGE_TO_FILE:
                        #util3.writeToFile(jsonMsg, cfg.MESSAGE_DIRECTORY)
                        writeToFile(jsonMsg, cfg.MESSAGE_DIRECTORY)
                    else:
                        if cfg.SHOW_MESSAGE_SOURCE:
                            print('#' + line + '\n')
                        print(jsonMsg, flush=True)

                    # Save raw message in a file if archiving.
                    if cfg.ARCHIVE_MESSAGES:
                        if not archivingStarted:
                            # Happens once per run. Set initial conditions, open file
                            # and write raw message
                            archivingStarted = True
                            archiveFileName = msg['rcvd_time'][0:10]
                            archiveFile = open(os.path.join(cfg.ARCHIVE_DIRECTORY, \
                                                        archiveFileName + '.978'), "a")
                            archiveFile.write(line + '\n')
                        else:
                            # See if a day boundary happened. If so, close old file
                            # and open new one.
                            if (msg['rcvd_time'][0:10] != archiveFileName):
                                archiveFile.close()
                                archiveFileName = msg['rcvd_time'][0:10]
                                archiveFile = open(os.path.join(cfg.ARCHIVE_DIRECTORY, \
                                                            archiveFileName + '.978'), "a")

                            archiveFile.write(line + '\n')                        
                            archiveFile.flush()
                    
        except Exception as _:
            # Error, place in errored out message file
            errList = traceback.format_exc(limit=10)
            errList += errList + '\n' + miniDump(line)
            errStr = errList.replace("\n", "\n# ")
            dumpRecord(errStr, line)

    # If testing, print any remaining triggers.
    if testMode:
        util.printAllTriggers()
