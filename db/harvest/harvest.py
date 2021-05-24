#!/usr/bin/env python3

"""Harvest reads FIS-B messages from a directory and updates a database.

"""

import sys, os, json, time, argparse, traceback, glob
import dateutil.parser, subprocess, pprint
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo import errors
from bson.objectid import ObjectId

import db.harvest.testing as test
import db.harvest.harvestConfig as cfg
import db.harvest.harvestExceptions as ex
from db.harvest.MsgMETAR import MsgMETAR
from db.harvest.MsgTAF import MsgTAF
from db.harvest.MsgCRL import MsgCRL
from db.harvest.MsgPIREP import MsgPIREP
from db.harvest.MsgSUA import MsgSUA
from db.harvest.MsgWINDS_06_HR import MsgWINDS_06_HR
from db.harvest.MsgWINDS_12_HR import MsgWINDS_12_HR
from db.harvest.MsgWINDS_24_HR import MsgWINDS_24_HR
from db.harvest.MsgNOTAM import MsgNOTAM
from db.harvest.MsgNOTAM_TFR import MsgNOTAM_TFR
from db.harvest.MsgCANCEL_NOTAM import MsgCANCEL_NOTAM
from db.harvest.MsgSIGWX import MsgSIGWX
from db.harvest.MsgSERVICE_STATUS import MsgSERVICE_STATUS
from db.harvest.MsgG_AIRMET import MsgG_AIRMET
from db.harvest.MsgCANCEL_G_AIRMET import MsgCANCEL_G_AIRMET
from db.harvest.MsgCANCEL_CWA import MsgCANCEL_CWA
from db.harvest.MsgFIS_B_UNAVAILABLE import MsgFIS_B_UNAVAILABLE
from db.harvest.MsgBLOCK import MsgBLOCK

# ------- GLOBALS

# Directory where Harvest fetches messages from
harvestDir = cfg.HARVEST_DIRECTORY

# URL of MongoDB
mongoUrl = cfg.MONGO_URL

# Active database connection for MongoDB ('fisb')
dbConn = None

# Location database connection for MongoDB ('fisb_location')
dbConnLocation = None

# Handle to the block message (image) object. This is here so that the
# testing module can call the function for producing an image report.
msgBLOCK = MsgBLOCK()

# List of all the message types handled. Each is a subclass of MsgBase.py
msgHandlerList = [MsgMETAR(), MsgTAF(), MsgCRL(), MsgPIREP(), \
                  MsgSUA(), MsgWINDS_06_HR(), MsgWINDS_12_HR(), \
                  MsgWINDS_24_HR(), MsgNOTAM(), MsgNOTAM_TFR(), \
                  MsgCANCEL_NOTAM(),MsgG_AIRMET(), MsgSERVICE_STATUS(), \
                  MsgSIGWX(), MsgCANCEL_G_AIRMET(), MsgCANCEL_CWA(), \
                  MsgFIS_B_UNAVAILABLE(), msgBLOCK]

# ------- End of globals

def createMsgHandlerDict():
    """Given the ``msgHandlerList``, create dictionary to associate 'type' value from a level 2
    message with a handler object.
    
    Each level 2 message has a ``type`` slot which defines the type of message it is.
    :class:`db.harvest.MsgBase`
    objects may handle one of more types. For example, :mod:`db.harvest.MsgBLOCK` handles all the image objects.
    This function returns a dictionary whose key is a ``type`` field from a level 2
    message and whose value
    is the object to call to handle it.

    This function is actually called at the time the module is loaded. It needs to be
    immediately available. It will be stored in the global ``msgHandlerDict``.
    
    Returns:
        dict: Dictionary as described above.
    """
    d = {}

    for x in msgHandlerList:
        for y in x.getTypesList():
            d[y] = x

    return d

# Create the message handler dictionary at module load time
msgHandlerDict = createMsgHandlerDict()

def dumpError(reason):
    """Write an error message to the error file.

    Args:
        reason (str): Explanation of the error.
    """
    with open(cfg.ERROR_FILENAME, "a") as f:
        f.write("-------------------------------------------------------------\n")
        f.write("#" + reason + "\n")

def dumpRecord(reason, jsonMsg = '*MISSING*'):
    """Write current msg to the error file for any decoding issues.

    Args:
        reason (str): Explanation of the error.
        jsonMsg (str): json message (as text) to dump (or '' if no message)
    """
    with open(cfg.ERROR_FILENAME, "a") as f:
        f.write("-------------------------------------------------------------\n")
        f.write("#" + reason + "\n")

        # Bad JSON will blow up here
        jsonText = ''
        try:
            if jsonMsg != '*MISSING*':
                jsonText = json.dumps(json.loads(jsonMsg), indent=2)
        except Exception as _:
            jsonText = "** Bad JSON in dumpRecord! Text was '" + jsonMsg + "' **"
            
        if jsonMsg != '*MISSING*':
            f.write(jsonText + "\n\n")

def dbConnect():
    """Connect to database

    Make a connection to the MongoDB database and store it in the global ``dbConn``.

    Since Harvest doesn't work without a database, this function will catch any 
    errors and wait for a certain amount of time before trying again. It will not
    return until it has an actual live database connection.    
    """
    global dbConn, dbConnLocation

    while True:
        try:
            client = MongoClient(cfg.MONGO_URL, tz_aware=True)

            # uUse the 'fisb' database and possibly location database
            dbConn = client.fisb
            dbConnLocation = client.fisb_location

            # Update dbConn in all message handlers
            for x in msgHandlerList:
                x.setDbConn(dbConn, dbConnLocation)
            break

        except Exception as _:
            dumpError('Failed to connect to database')

            # sleep for specified time
            time.sleep(cfg.RETRY_DB_CONN_SECS)

def convertDictISO(msgDict):
    """Change any '<xxx>_time' entries to ``datetime`` values.

    Messages that come out of level 2 fisb-decode have various time slots stored as ISO strings.
    To store in the database, we need to convert them to Datetime objects. This
    function takes a message and converts all the slots that end in '_time' into a
    Datetime object. These slots are only at the first level, no nesting is performed.
    It will also convert ``start_time`` and ``stop_time`` slots that occur
    as inside a ``geometry`` slot.

    This is meant to be called *BEFORE* conversion to a ``geojson`` slot.

    Args:
        msgDict: Dictionary containing a level 2 fisb message.
    
    Returns:
        dict: Dictionary with all time slots changed to Datetime objects.
    """

    keys = list(msgDict.keys())

    for k in keys:
        if k.endswith('_time'):
            msgDict[k] = dateutil.parser.parse(msgDict[k])
    
    # Add start_time and stop_time if geometry is present
    if 'geometry' in msgDict:
        geoDict = msgDict['geometry']
        for x in range(0, len(geoDict)):
            if 'start_time' in geoDict[x]:
                geoDict[x]['start_time'] = dateutil.parser.parse(geoDict[x]['start_time'])
            if 'stop_time' in geoDict[x]:
                geoDict[x]['stop_time'] = dateutil.parser.parse(geoDict[x]['stop_time'])
    
    return msgDict

def processMessage(msg, currentUtc):
    """ Process a message and dispatch it to the appropriate message handler.

    Takes a message and send it to the appropriate message handler after some
    preprocessing.

    If there are any exceptions, will dump the error and the message to the
    error file.

    If ``cfg.EXPIRE_MESSAGES`` is ``True``, messages will be checked to see if they
    have already expired before being put in the database. If you want to see what
    messages theses are, also set ``cfg.PRINT_IMMEDIATE_EXPIRATIONS`` to ``True`` and
    the messages will be printed on the console.

    Args:
        msg (dict): Level 2 fisb message.
        currentUtc (str): Current UTC time used to see if messages have already expired.
    """
    # Catch and log errors

    try:
        # Decode the JSON message into a dictionary
        # Rarely, we get '' for msg. Skip these.
        if msg == '':
            return
        msgDict = json.loads(msg)

        # Change any _time fields from ISO strings to datetime
        msgDict = convertDictISO(msgDict)

        # Ignore any already expired message
        if cfg.EXPIRE_MESSAGES and ('expiration_time' in msgDict):
            if cfg.PRINT_IMMEDIATE_EXPIRATIONS:
                if msgDict['expiration_time'] < currentUtc:
                    # expired
                    print('** DOA **')
                    print('Expired at:',msgDict['expiration_time'], 'Current UTC:', currentUtc)
                    print('Message follows:')
                    pprint.pprint(test.convertDatetimeToIsoString(msgDict))
                    print()
                    return

        # Dispatch and process the message
        msgType = msgDict['type']

        if msgType in msgHandlerDict:
            msgHandlerDict[msgType].processMessage(msgDict)
            
    except errors.ConnectionFailure as _:
        dbConnect()

    except Exception as _:
        # Error, place in errored out message file
        errList = traceback.format_exc(limit=10)
        errStr = errList.replace("\n", "\n# ")
        dumpRecord(errStr, msg)

def doMaintTasks(maintCounter):
    """Performs periodic maintenance tasks.

    1. Remove any expired messages.
    2. Call the :class:`db.harvest.MsgBLOCK` object to maintain the images.

    If a database connection failure occurs, will reconnect (even if it takes a while),

    Will log any other errors that occur processing messages to the error file.

    Is called by :func:`harvest`, which determines how often it is called.
    
    Args:
        maintCounter: Integer counter of the number of times we have been called. This
          can be used to perform tasks every 'n' times it is called.

    Returns:
        int: ``maintCounter`` incremented by one.
    """
    # Catch and log errors
    try:
        # ** TASKS TO RUN EVERY INTERVAL **

        # Expire messages
        if cfg.EXPIRE_MESSAGES:
            for x in msgHandlerList:
                x.expireMessages()

        # Maintain the current state of images.
        msgBLOCK.periodicUpdate()

        #-------------------------------------
        # ** TASKS TO RUN EVERY 2 INTERVALS **
        if (maintCounter % 2) == 0:
            pass

        #-------------------------------------
        # ** TASKS TO RUN EVERY 3 INTERVALS **
        if (maintCounter % 3) == 0:
            pass

        #-------------------------------------
        # ** TASKS TO RUN EVERY 4 INTERVALS **
        if (maintCounter % 4) == 0:
            pass

        return maintCounter + 1
        
    # Catch database connection errors and wait until database is reconnected.
    except errors.ConnectionFailure as _:
        dbConnect()
        return maintCounter + 1
        
    except Exception as _:
        # Error, place in errored out message file
        errList = traceback.format_exc(limit=10)
        errStr = errList.replace("\n", "\n# ")
        dumpRecord(errStr)
        return maintCounter + 1

def harvest(tgTestNumber):
    """Main function for Harvest. Process messages.

    All image files are deleted at the start of execution.

    Messages are read from a directory which has file names that allows
    them to be read in the order they arrived. We read in a file and
    process and delete it. If we have no files we wait for 1/4 second
    and try again.

    Every ``cfg.MAINT_TASKS_INTERVAL_SECS`` we will call :func:`doMaintTasks`.

    If ``tgTestNumber`` is something other than zero, we are doing a test.
    In this case we start up a 'trickle' process and wait for it to produce
    a ``sync.fisb`` file which contains the difference in actual time and
    test time. All attempts to get the current time or do time manipulations
    from then on will use the test time. Each test will have a trigger file
    which tells us at what times we need to do a dump of the database,
    images and vectors.
    Otherwise, execution is normal.

    Args:
        tgTestNumber (int): Test number to run. Normal execution if ``0``.
    """
    isTesting = False

    # Harvest gets its messages from a directory.
    # Sanity check to see if the directory exists
    if not os.path.isdir(harvestDir):
        print("Directory '" + harvestDir + "' does not exist.")
        return

    # Get database connection and insert in message handler objects.
    dbConnect()

    # Setup for any testing.
    # Note: For actual testing, this will sit here until
    # the sync file is available and other files have been
    # read.
    if (tgTestNumber != 0):
        trickleProc = test.setup(tgTestNumber, dbConn, \
                    msgHandlerDict['NEXRAD_CONUS'])
        isTesting = True

    try:
        # Any exceptions in this part will just fail and exit.
        # If anything fails here, there is little to do to recover.
        # doMaintTasks() and processMessage() have error recovery.

        # Counter used by doMaintTasks so that some tasks (like
        # expire messages) are done every 'maintCounter' times.
        maintCounter = 1

        # Path to harvestDir which contains only .msg files (files
        # are written as .tmp files, then after closing are changed
        # to .msg)
        path = os.path.join(harvestDir, '*.msg')

        # Set initial value of oldTime
        oldTime = int(time.time())

        # Expire any old expired messages in db.
        maintCounter = doMaintTasks(maintCounter)

        # Loop through directory looking for files
        while True:

            # We run doMaintTasks() every cfg.MAINT_TASKS_INTERVAL_SECS
            # Will also check this again when processing files
            newTime = int(time.time())
            if (newTime - oldTime) >= cfg.MAINT_TASKS_INTERVAL_SECS:
                maintCounter = doMaintTasks(maintCounter)
                oldTime = newTime
            
            # Get a list of sorted filenames to be processed. Files are ordered
            # such that the earliest file is sorted first.
            fileList = sorted(glob.glob(path))

            # Check for testing triggers
            if isTesting:
                test.checkForTrigger()

            # if no files, wait for a quarter second
            if len(fileList) == 0:
                time.sleep(0.25)
                continue
        
            for f in fileList:
                # Skip README.txt
                if 'README.txt' in f:
                    continue
                
                # Open and read contents. Contents are assumed
                # to be single line JSON string.
                with open(f, 'r') as fileIn:
                    msg = fileIn.read()

                # Remove file from directory
                os.remove(f)

                # Get currentUtc to use to check all files for expiration in
                # this pass.
                currentUtc = test.datetimeNow()
        
                # Check for testing triggers
                if isTesting:
                    test.checkForTrigger()

                # Process
                msg = msg.strip()
                processMessage(msg, currentUtc)

                # Recheck for maintenance tasks while processing files
                newTime = int(time.time())
                if (newTime - oldTime) >= cfg.MAINT_TASKS_INTERVAL_SECS:
                    maintCounter = doMaintTasks(maintCounter)
                    oldTime = newTime

    except KeyboardInterrupt:
        if isTesting:
            # Send ^C to trickle
            trickleProc.send_signal(2)
            
            if trickleProc.poll() == None:
                trickleProc.wait(10)
        print()
        sys.exit()
                
if __name__ == "__main__":
    ## --- Script Code ---##
    parser = argparse.ArgumentParser(description= \
                                 """
                                 Harvest FIS-B messages and store in database.
                                 """)
    parser.add_argument('--dir', \
        help="Directory containing FIS-B messages.", \
        type=str)
    parser.add_argument('--db', \
        help="MongoDB URL.", \
        type=str)      
    parser.add_argument('--test', \
        choices=range(1,31), \
        help="Run specified test group and dump data.", \
        type=int)
        
    args = parser.parse_args()

    if args.db:
        mongoUrl = args.db

    if args.dir:
        harvestDir = args.dir

        # Strip any trailing /
        if harvestDir[-1] == '/':
            harvestDir = harvestDir[:-1]

    tgTestNumber = 0

    if args.test:
        tgTestNumber = args.test

    # Call main loop. Doesn't return unless problem
    harvest(tgTestNumber)
