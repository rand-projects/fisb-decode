"""Code for handling test group testing.

There are 27 test groups supplied by the standard creator and a few
defined by me. Each test group consists of a set of packets, each
with the time in seconds after midnight on a specified date
that it should be activated.

More specific information on how the testing is organized and how to
perform this in fisb-decode is found elsewhere.

Here are some important concepts:

- The file ``fisb-decode/tg/triggers/start-dates.csv`` contains
  the starting dates of each test group. All test groups have their times
  based on midnight on this date.
- Within the directory ``fisb-decode/tg/triggers`` is one file per
  test group with the name ``tgxx.csv`` where ``xx`` is the number of the 
  test group (``00``, ``01``, etc). These are trigger files. Trigger files
  tell Harvest when to perform a data dump of the current state of the database,
  image files, vector files, etc. The instructions for the test groups will
  tell you to check for this or that at some specified time. Triggers automate
  this process by creating a directory for each trigger point with a data dump.
  Each line of a trigger file contains:

  - The offset in seconds past midnight of the start date when it should occur.
    This is usually the number specified in the test group instructions.
  - An adjustment time, positive or negative in seconds from the offset time.
    Often the test group instructions will specify to check before or after a 
    certain time. The adjustment time provides an offset for this. When making
    this offset it is important to take into account Harvest's 
  - Number of the trigger (1, 2, 3, ...)
- Harvest reads the ``start-dates.csv`` and appropriate trigger file and will
  provide a data dump in a particular directory at the indicated times. This
  directory will be: ``fisb-decode/tg/results/tgxx/yy/`` where ``xx``
  is the test group number and ``yy`` is the trigger number.
- All times in Harvest go through :func:`datetimeNow`. If Harvest is in
  non-testing mode, you will get back the current time. If you are in testing
  mode then the time will be the time referenced to the current test time.
- :mod:`fisb.trickle.trickle` is the program that actually reads the test 
  group packets and sends it out in real time. When it starts, it creates a file
  called ``sync.fisb`` which contains the offset between 'message time' and 
  'actual time'. Harvest reads this file when it starts and offsets its time to
  correspond with 'message time'.
"""
import sys, os, json, time, glob, pprint
import subprocess
import dateutil.parser, csv, shutil, math
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from pymongo import errors
from tzlocal import get_localzone

import db.harvest.harvestConfig as cfg
import db.harvest.harvestExceptions as ex
import db.harvest.vectors as vec

# Allowable selections for testing
OPT_NONE = 0
OPT_DUMP = 1
OPT_CREATE = 2
OPT_TEST = 3

DB_TYPES = ['METAR', 'TAF', 'CRL_8', 'CRL_11', 'CRL_12', \
    'CRL_14', 'CRL_15', 'CRL_16', 'CRL_17', 'PIREP', \
    'SUA', 'WINDS_06_HR', 'WINDS_12_HR', 'WINDS_24_HR', \
    'NOTAM', 'NOTAM_TFR', 'AIRMET', 'SIGMET', \
    'WST', 'CWA', 'SERVICE_STATUS', \
    'G_AIRMET', 'FIS_B_UNAVAILABLE', 'RSR']

# Global variables set once at program startup
# --------------------------------------------

# True if we are in test mode of some sort. False for normal operations.
isTesting = False

# Test number we are running. 1-30.
testNumber = 0

# Test group string in the form tgxx. Used for directory
# names
tgStr = 'tg00'

# Ordered list with one entry per trigger.
# Each trigger is a list of form:
#  [time, trigger_id, trigger_name, trigger_offset_in_seconds]
triggerList = []

# Difference in float seconds between 'real time' and 'simulated time'
syncDiff = -1

# Local timezone
localTZ = get_localzone()

# Current trigger
currentTrigger = 0

# Database connection
dbConn = None

# Handle to MsgBLOCK object used to create image reports.
imageClass = None

# --------------------------------------------

def createTriggerList(testNumber):
    """Create a list containing trigger information for each trigger
    in this test group.

    Given the test group number, find
    the start date for this test group (in file ``start-dates.csv``) then
    read the trigger file (in file ``tgxx.csv``) and for each trigger in
    that file, create a list entry containing information about that trigger.

    Args:
        testNumber (int): Test group number we are running.

    Returns:
        list: List of one entry per trigger. Each item of a list is
        another list with the following values:

        0. Time of the trigger in UTC seconds (in 'message time', i.e. the
           time the message originally occurred)
        1. Trigger number (1, 2, 3, ...)
        2. Trigger name to print when trigger activated.
        3. Offset time of the test in seconds past midnight on the start date.
        4. Time offset directly from trigger file
        5. Time adjustment directly from trigger file

    Raises:
        TGNumberNotInStartDatesException: If we could not find TG number in
          ``start-dates.csv``')
    """
    # Get the starting time
    startYear = -1
    startMonth = -1
    startDay = -1

    with open(cfg.TG_START_DATES, newline='') as csvfile:
        csvReader = csv.reader(csvfile, delimiter=',')
        for row in csvReader:
            tgNum = int(row[0])
            if tgNum == testNumber:
                startYear = int(row[1])
                startMonth = int(row[2])
                startDay = int(row[3])
                break

    if startYear == -1:
        raise ex.TGNumberNotInStartDatesException('Could not find TG number in start-dates.')

    t = datetime(startYear, startMonth, startDay, 0, 0, 0, tzinfo=timezone.utc).timestamp()

    # This is used also by fisb.level0, so can't use value harvest makes at startup.
    tgStr = 'tg{:02d}'.format(testNumber)

    # Now read trigger file
    triggerFile = os.path.join(cfg.TG_TRIGGER_DIR, tgStr + '.csv')

    tlist = []

    with open(triggerFile, newline='') as csvfile:
        csvReader = csv.reader(csvfile, delimiter=',')
        for row in csvReader:
            timeOffset = int(row[0])
            timeAdj = int(row[1])
            triggerNum = int(row[2])
            triggerName = row[3]

            # Actual offset is the specified offset with suggested slop time
            # either positive or negative as suggested for the test.
            secondsOffsetAdjusted = timeOffset + timeAdj
            finalTime = t + secondsOffsetAdjusted

            tlist.append([finalTime, triggerNum, triggerName, secondsOffsetAdjusted, \
                timeOffset, timeAdj])

    return tlist

def getSyncTime():
    """Called at Harvest start up. Wait for :mod:`fisb.trickle.trickle` to
    create the ``sync.fisb`` file. Then read it and return the time difference.

    Returns:
        float: Time difference in seconds between the current time and the
        test group message time.
    """
    if not os.path.isfile(cfg.SYNC_FILE):
        print('Waiting for sync.fisb to be created by trickle.')
        while not os.path.isfile(cfg.SYNC_FILE):
            time.sleep(0.250)

    with open(cfg.SYNC_FILE) as file:
        line = file.readline()
        line = line.strip()
        sDiff = float(line)

    # Remove sync file
    os.remove(cfg.SYNC_FILE)

    return sDiff

def printTriggerTimes():
    """When a test is started, print to the console when the triggers will
    take place, both in actual time and message time.

    Running test groups is pretty much the same as watching paint dry (on a
    sunny day, paint dries faster). Much
    of the time you are waiting hours after the last packet was
    read to make sure that some file gets deleted. What this function does is
    to tell you when each trigger will be run so that you can plan your day.
    """
    print('Expect trigger events at:')

    for x in triggerList:
        futureTime = datetime.fromtimestamp(x[0] + syncDiff)
        futureTime = futureTime.replace(microsecond=0)
        print('  {:02d}: {} {:6d} -> {}'.format(x[1], \
            futureTime.astimezone(localTZ), x[3], \
            datetime.utcfromtimestamp(x[0])))

def pathForTrigger():
    """Create and return path to the trigger file using ``cfg.TG_DIR`` and
    the global ``tgStr``.

    Returns:
        str: Path to the trigger files.
    """
    return os.path.join(cfg.TG_DIR, 'results', tgStr, '{:02d}'.format(currentTrigger + 1))

def getListOfImageFiles():
    """Create and return a list of paths to all image files.

    Returns:
        list: List of all image file paths. Possibly empty.
    """
    imageFiles = [os.path.join(cfg.IMAGE_DIRECTORY, f) \
        for f in os.listdir(cfg.IMAGE_DIRECTORY) if '.png' in f]
    return imageFiles
    
def prepareDirectories(testNumber):
    """Called at Harvest start when running a test. Performs various functions.

    The function does the following at the start of running a test group:

    - Delete all image files.
    - Delete any file in the directory where Harvest reads its messages.
    - Remove the directory tree for the test (``fisb-decode/tg/results/tgxx``)
      Then create a new one with subdirectories for each trigger.
    """
    # Delete all files in image directory
    imageFiles = getListOfImageFiles()
    for f in imageFiles:
        os.remove(f)
        os.remove(f + '.aux.xml')

    # Delete all files in harvesting directory
    deleteFiles = [os.path.join(cfg.HARVEST_DIRECTORY, f) \
        for f in os.listdir(cfg.HARVEST_DIRECTORY)]

    for f in deleteFiles:
        if 'README.txt' not in f:
            os.remove(f)

    # remove any existing directory (and subdirs), then make new tree
    path = os.path.join(cfg.TG_DIR, 'results', tgStr)
    try:
        shutil.rmtree(path, ignore_errors=True)
        os.mkdir(path)
    except Exception:
        print("Can't make directories in {}. This usually means you have something open there."\
            .format(path))
        sys.exit(1)

    for x in triggerList:
        newPath = os.path.join(path, '{:02d}'.format(x[1]))
        os.mkdir(newPath)
            
def emptyDatabaseTables():
    """Delete all data from the MSG collection before running a test.

    Empties out all the database table to start with a clean slate.
    """
    dbConn.MSG.delete_many({})

def datetimeNow():
    """Return 'current' datetime time. If running a test this is in 'message time'.

    Returns:
        datetime: Datetime object in UTC. Will be the current time if not
        running a test, or 'message time' if running a test.
    """
    if isTesting:
        return datetime.now(timezone.utc) - timedelta(0, syncDiff)
    else:
        return datetime.now(timezone.utc)

def timestampNow():
    """Return 'current' timestamp. Timestamp is the number of seconds and
    fractions of a second. If running a test, this is in 'message time'.

    Returns:
        float: Result of ``datetime.now(timezone.utc).timestamp()``
        Will be the current time if not running a test, or 'message time'
        if running a test.
    """
    return datetimeNow().timestamp()

def checkForTrigger():
    """Called periodically to see if it's time to do a trigger.

    Checks to see if the next trigger is due. If it is, it will perform
    the trigger, dumping the current state of the system to the proper
    directory.

    If we have performed the last trigger, will exit Harvest.
    """
    global currentTrigger

    dt = datetimeNow()
    ts = dt.timestamp()

    if ts >= triggerList[currentTrigger][0]:
        print('{:02d}:  {}'.format(triggerList[currentTrigger][1], \
            triggerList[currentTrigger][2].strip()))

        # Trigger to process
        triggerPath = pathForTrigger()

        dump(triggerPath, dt, triggerList[currentTrigger])

        # Progress to next trigger
        currentTrigger += 1
        if currentTrigger == len(triggerList):
            print('** done **')

            # Exit, nothing more to do.
            sys.exit(0)

def augmentCrlStatus(msg):
    """Augment CRL message with status of ``COMPLETE`` or ``INCOMPLETE``.

    Check the CRL message for completeness.
    Will add a ``status`` field to the message with a value of 
    ``COMPLETE`` or ``INCOMPLETE``.

    ``COMPLETE`` messages meet the following criteria:

    - Doesn't have an overflow (i.e. has more the 138 reports).
    - Has no reports.
    - All reports are in the database (including both text and graphics if
      indicated).

    Args:
        msg (dict): CRL message dictionary to be augmented.

    Returns:
        dict: ``msg`` dictionary with new ``status`` field indicating
        completeness.
    """
    reports = msg['reports']

    # A no document report is a complete report.
    if len(reports) == 0:
        msg['status'] = 'COMPLETE'
        return msg

    # An overflow CRL is also incomplete
    if 'has_overflow' in msg:
        msg['status'] = 'INCOMPLETE'
        return msg
        
    for reportNumber in reports:
        if not ('*' in reportNumber):
            msg['status'] = 'INCOMPLETE'
            return msg
        
    msg['status'] = 'COMPLETE'
    return msg

def augmentTwgoStatus(msg, dt):
    """Augment TWGO message with status related to activity timing.

    Checks a TWGO message to see if the graphics section has timing
    information such as a ``start_time`` or ``stop_time``. If it does,
    will compare with message time and add a ``status`` field with one
    of the following values:

    - ``Daily``
    - ``Pending Activation``
    - ``Expired``
    - ``Active``

    This routine will only be sent messages that have a ``geojson`` section.

    Args:
        msg (dict): TWGO message dictionary to be augmented.
        dt (datetime): Current ``datetime`` object in 'message time'.

    Returns:
        dict: ``msg`` dictionary with new ``status`` field indicating
        completeness.
    """

    # Assumes message has a 'geojson' section
    geoList = msg['geojson']['features']

    for i in range(0, len(geoList)):
        geoItem = geoList[i]['properties']

        if ('stop_hour' in geoItem) or ('start_hour' in geoItem):
            geoList[i]['properties']['status'] = 'Daily'
            continue

        hasStartTime = False
        hasStopTime = False
        if 'start_time' in geoItem:
            hasStartTime = True
            startDatetime = geoItem['start_time']

        if 'stop_time' in geoItem:
            hasStopTime = True
            stopDatetime = geoItem['stop_time']            

        if hasStartTime and hasStopTime:

            if dt < startDatetime:
                geoList[i]['properties']['status'] = 'Pending activation'
            elif dt > stopDatetime:
                geoList[i]['properties']['status'] = 'Expired'
            else:
                geoList[i]['properties']['status'] = 'Active'
            continue

        if hasStopTime:
            if dt >= stopDatetime:
                geoList[i]['properties']['status'] = 'Expired'
            else:
                geoList[i]['properties']['status'] = 'Active'
            continue

        if hasStartTime:
            if dt < startDatetime:
                geoList[i]['properties']['status'] = 'Pending activation'
            else:
                geoList[i]['properties']['status'] = 'Active'
            continue

        # No time is same as active.
        geoList[i]['properties']['status'] = 'Active'

    return msg
    
def isoformatToZ(dt):
    """Change datatime to iso format string ending in Z.

    The standard conversion to an ISO string in UTC appends
    ``+00:00``. We convert the data and then change that to ``Z``.
    
    Args:
        dt (datetime): Datetime object to be converted.

    Returns:
        str: Datetime converted to ISO string.
    """
    return dt.isoformat().replace('+00:00', 'Z')

def convertDatetimeToIsoString(msgDict):
    """Change any '<xxx>_time' entries to ISO string values.
                                                                                                 
    Messages are stored in the database as ``datetime`` objects. For printing
    to files, we convert these back to ISO string values. This
    function takes a message and converts all the slots that end in '_time' into an
    ISO string. These slots are only at the first level, no nesting is performed.
    It will also convert ``start_time`` and ``stop_time`` slots that occur                       
    inside a ``geojson`` slot.                                                               
                                                                                                 
    Args:                                                                                        
        msgDict (dict): Dictionary containing message.

    Returns:
        dict: Dictionary with all time slots changed to ISO strings.
    """
    keys = list(msgDict.keys())

    for k in keys:
        if k.endswith('_time'):
            msgDict[k] = isoformatToZ(msgDict[k])
    
    # Add start_time and stop_time if geometry is present
    if 'geojson' in msgDict:
        geoDict = msgDict['geojson']['features']
        for x in range(0, len(geoDict)):
            if 'start_time' in geoDict[x]['properties']:
                geoDict[x]['properties']['start_time'] = isoformatToZ(geoDict[x]['properties']['start_time'])
            if 'stop_time' in geoDict[x]['properties']:
                geoDict[x]['properties']['stop_time'] = isoformatToZ(geoDict[x]['properties']['stop_time'])
    
    return msgDict

def dumpDatabase(dumpPath, dt):
    """Dumps all database tables to ``dumpPath`` directory.

    TWGO database tables and CRL tables will get augmented. All dates
    are converted from ``datetime`` objects to ISO strings for easier
    reading.

    Args:
        dumpPath (str): Directory path to dump files to. The actual table
          name with an added ``.db`` extension will be the file name.
        dt (datetime): Current 'message time'. Used for TWGO augmentation.
    """
    for t in DB_TYPES:
        numDocs = dbConn.MSG.find({'type': t}).count()
        if numDocs > 0:

            cursor = dbConn.MSG.find({'type': t})
            collectionPath = os.path.join(dumpPath,t + '.db')
            with open(collectionPath, "w") as oFile:
                for doc in cursor:
                    # For TWGO files, augment them if possible to
                    # show status based on current time. Some TG's benefit from this.
                    if t in ['NOTAM', 'NOTAM_TFR', 'AIRMET', 'SIGMET', 'CWA', 'WST', 'G_AIRMET']:
                        if 'geojson' in doc:
                            doc = augmentTwgoStatus(doc, dt)

                    if t.startswith('CRL'):
                        doc = augmentCrlStatus(doc)

                    # Remove non-important fields
                    if 'digest' in doc:
                        del doc['digest']
                    if 'insert_time' in doc:
                        del doc['insert_time']

                    doc = convertDatetimeToIsoString(doc)

                    pprint.pprint(doc, stream=oFile, width=100)
                    oFile.write('\n')

def writeTimeAndOffsetAsFile(dumpPath, dtStr, secondsOffset, timeOffset, timeAdj, \
        triggerName):
    """Writes an (almost) empty file whose filename contains 'message time' and offset.

    Writes an essentially empty file to the dump directory. The whole purpose
    is to provide a filename which lists the 'message time' the dump was made
    and the offset in seconds (which is helpful when refering to the test group
    documentation).

    The filename form is: ``yyyy-mm-dd-hhmmss_<offset>=<timeoffset><+-><timeAdj>``. For example:
    ``2013-03-21-020140_7320=7300+20``. ``2013-03-21-020140`` is the time of the dump
    relative to the test group's execution. ``7320`` is the number of seconds
    past midnight on the 'message time' day the test was started (also known
    as the trigger time). ``7300`` is the time as referred in the documentation, and
    ``20`` is the offset from that time, either positive or negative. If there is no
    adjust, just the time and offset (no adjustment) is used.
    This number is usually a checkpoint in the documentation.

    Args:
        dumpPath (str): Directory path to place the file.
        dtStr (str): String representing the date/time of the dump.
          In the example above it would be ``2013-03-21-020140``.
        secondsOffset (int): Offset from midnight in seconds from when the 
          test was started. In the example above it would be ``7300``.
        timeOffset (int): Documentation trigger time.
        timeAdj (int): Adjustment to trigger time (positive or negative).
        triggerName (str): Name of the trigger. Will become the files contents.
    """
    # Don't print time adjustment if zero.
    if timeAdj == 0:
        fname = '{}_{}'.format(dtStr, secondsOffset)
    else:
        posNegStr = '+'
        if timeAdj < 0:
            posNegStr = '-'
            timeAdj = -timeAdj

        fname = '{}_{}~{}{}{}'.format(dtStr, secondsOffset,timeOffset, posNegStr, timeAdj)

    with open(os.path.join(dumpPath, fname), 'w') as oFile:
        oFile.write(triggerName + '\n')

def dumpImageReport(dumpPath, dt):
    """If there are any images, create a text file with metainformation.

    The ``.png`` files do not have metadata associated with them. To check for
    things like how old the file is, etc, we create an image report that contains
    a summary of information for each image file dumped. This is written to the same
    directory as other checkpointed information. Its name will be
    ``image-report.txt``. Sample contents are shown below: ::

        Current Image Report at 2013/05/21 02:27:02

        NEXRAD_REGIONAL
          observation_time: 2013/05/21 02:25:00
          newest_data: 2013/05/21 02:25:00
          image_age (mm:ss): 02:02
          last_changed: 2013/05/21 02:26:22
        NEXRAD_CONUS
          observation_time: 2013/05/21 02:25:00
          newest_data: 2013/05/21 02:25:00
          image_age (mm:ss): 02:02
          last_changed: 2013/05/21 02:26:13

    The data in this file is created by
    :py:meth:`db.harvest.MsgBLOCK.MsgBLOCK.createImageReport`. See there for details on contents.

    Args:
        dumpPath (str): Directory path to dump files to. The actual table
          name with an added ``.db`` extension will be the file name.
        dt (datetime): Current 'message time'.
    """
    hasReport, report = imageClass.createImageReport(dt)

    if hasReport:
        with open(os.path.join(dumpPath, 'image-report.txt'), "w") as oFile:
            oFile.write(report)

def dump(dumpPath, dt, triggerList):
    """Dump a set of data at a trigger point.

    Top level dump function. Calls individual routines to dump
    various pieces. Will do the following tasks and place the output in the
    dump directory:

    - Copy all the images.
    - Write an image report (if any images).
    - Dump all database tables.
    - Dump all vector graphics.

    Args:
        dumpPath (str): Directory path to place the files.
        dt (datetime): Current 'message time'.        
        triggerList (list): List with information about triggers.
    """

    dtStr = dt.strftime('%Y-%m-%d-%H%M%S')
    writeTimeAndOffsetAsFile(dumpPath, dtStr, triggerList[3], \
        triggerList[4], triggerList[5], triggerList[2])

    # Copy all files in image directory
    imageFiles = getListOfImageFiles()
    for f in imageFiles:
        shutil.copy(f, dumpPath)

    # Dump image report
    dumpImageReport(dumpPath, dt)
    
    # Dump database
    dumpDatabase(dumpPath, dt)

    # Dump vectors
    vec.dumpVectors(dumpPath, dbConn)

def setup(tgTestNumber, db, imageClassObj):
    """Called at the beginning of Harvest execution to set up testing.

    Performs the following tasks:

    - Create trigger list.
    - Create directories for dumping data at trigger points.
    - Starts ``trickle`` running as a subprocess and waits for
      ``sync.fisb`` file to be created.
    - Print a list of trigger times so the user can plan their
      day.

    Args:
        tgTestNumber (int): Test number to execute.
        db (object): MongoDB database object (``fisb`` database).
        imageClassObj (object): Pointer to :class:`db.harvest.MsgBLOCK`. This is used
          as a handle to create the image report.

    Returns:
        object: Subprocess object that is executing ``trickle``.
    """
    global isTesting, testNumber, tgStr, \
        triggerList, syncDiff, dbConn, \
        imageClass

    dbConn = db
    imageClass = imageClassObj

    print('*** Running Test {:02d} ***'.format(tgTestNumber))

    isTesting = True
    testNumber = tgTestNumber
    tgStr = 'tg{:02d}'.format(testNumber)
    triggerList = createTriggerList(testNumber)
    trickleArg = '../tg/tg-source/generated/' + tgStr + '.978'

    # Prepare directories
    prepareDirectories(testNumber)

    # Delete database contents
    emptyDatabaseTables()

    # Start trickle subprocess
    proc = subprocess.Popen(['./trickleToDir ' + trickleArg], shell=True)

    # Obtain the sync time
    syncDiff = getSyncTime()

    # Print when the user can expect triggers to occur
    printTriggerTimes()

    return proc
