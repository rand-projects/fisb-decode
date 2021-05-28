"""Harvest configuration information.
"""

#: Where to write error messages.
ERROR_FILENAME = 'HARVEST.ERR'

#: Messages will be read and then deleted from this directory.
HARVEST_DIRECTORY = '../runtime/harvest'

#: Number of seconds to run routine maintenance tasks
MAINT_TASKS_INTERVAL_SECS = 10

#: MONGO URI
MONGO_URI = 'mongodb://localhost:27017/'

#: Number of seconds between retrying failed database connection
RETRY_DB_CONN_SECS = 60

#: Normally ``True``, set to ``False`` to prevent messages from being
#: expired. This is useful for testing old messages.
EXPIRE_MESSAGES = True

#: If ``True``, CRL messages will attempt to reconcile the report
#: with whether or not it is in the database. Each report will
#: get an '*' appended to the name if it is present. If you are
#: not interested in this, set to ``False``. It does generate a bunch
#: of queries.
ANNOTATE_CRL_REPORTS = True

#: Set to ``True`` if you want to process and store images, otherwise ``False``
PROCESS_IMAGES = True

#: Set to the directory you want to store files in. Make sure the directory
#: exists.
IMAGE_DIRECTORY = '../runtime/images'

#: Set to ``True`` to have images smoothed. Smoothing the images results in a
#: nicer image, but the images are about 4 times the size (image width is
# multiplied by 2). Images are smoothed using a bilinear interpolation.
SMOOTH_IMAGES = False

#: Where the ``sync.fisb`` file lives. This file provides an offset in 
#: seconds (as a float) from the current time to the simulated time.
#: Used for coordinating Harvest with Trickle during testing.
SYNC_FILE = '../runtime/misc/sync.fisb'

#: Each test group needs a specific start date. These are found here.
#: Used only for testing.
TG_START_DATES = '../tg/triggers/start-dates.csv'

#: Directory where the trigger files are.
#: Used only for testing.
TG_TRIGGER_DIR = '../tg/triggers'

#: location of the 'tg' directory.
TG_DIR = '../tg'

#: For standard compliance set this to ``True``. This will
#: update the CRL status of incoming reports that have 
#: a CRL status (NOTAM-TFR, AIRMET, SIGMET, WST,
#: CWA, G_AIRMET). If you aren't using CRLs, this can be set to
#: ``False`` and save some processing time.
IMMEDIATE_CRL_UPDATE = True

#: Number of seconds we have to receive no new image data
#: before creating an image. Set to 0 for testing.
IMAGE_QUIET_SECONDS = 10

#: Sometimes messages that arrive are already past
#: their expiration date. There are a number of reasons
#: for this: a) you may be processing a large batch of
#: old messages, or b) there might be some other problem
#: (or not). Set this to ``True`` to print these to stdout
#: when they occur, or ``False`` to hide them.
PRINT_IMMEDIATE_EXPIRATIONS = False

#: Set to ``True`` if you have the location database filled
#: with location data and wish to add location information
#: to METARs, TAFs, and WIND data.
#: Set to ``False`` for testing, but doesn't really have any
#: effect.
TEXT_WX_LOCATION_SUPPORT = True

#: Set to ``True`` if you have the location database filled
#: with location data and wish to add location information
#: to PIREPS. Note: PIREP location augmentation is 
#: problematic at best since it relies on human input data.
#: Set to ``False`` for testing, but doesn't really have any
#: effect.
PIREP_LOCATION_SUPPORT = True

#: If ``True``, store the contents of any unmatched PIREP to
#: the file in SAVE_UNMATCHED_PIREPS_FILE.
SAVE_UNMATCHED_PIREPS = True

#: If SAVE_UNMATCHED_PIREPS is ``True``, append the contents of
#: PIREP to this file. Full path must be supplied.
SAVE_UNMATCHED_PIREPS_FILE = '../runtime/misc/PIREPS-UNMATCHED.txt'

#: Define values for the 'Not included' color in images.
#: Not included colors happen around the borders of some images
#: that have other than rectangular data in them. All images
#: made by Harvest are rectangles. A 'No data' value is different.
#: These are unknown values that should be in the image, but FIS-B
#: doesn't know them. There are 3 parts of the RBG pixel to define.
NOT_INCLUDED_RED = 0xEC
NOT_INCLUDED_GREEN = 0xDA
NOT_INCLUDED_BLUE = 0x96

#: Set the type of image map you want to display.
#: Setting this to 1 (testing) forces a set of color 
#: maps. For ``GENERAL``` and ``SHOW_NO_DATA`` it only
#: changes the behavior of 'no-data' and 'no-information'
#: values.
#:
#: GENERAL (0)
#:   For general ground use. Doesn't display NO-DATA areas.
#: TESTING (1)
#:   Maps specifically for testing. Shows all values.
#: SHOW_NO_DATA (2)
#:   Same as ``GENERAL``, but shows areas of NO-DATA.
IMAGE_MAP_CONFIGURATION = 2

#: Set the cloudtop map colors to use (this doesn't apply when
#: performing test group tests).
#:
#: 0 - map used for testing
#: 1 - gray scale
#: 2 - colorful
#: 3 - red gradient
#: 4 - brown gradient
CLOUDTOP_MAP = 4

#: Set the radar map colors to use (this doesn't apply when
#: performing test group tests).
#:
#: 0 - map used for testing and the general FIS-B scale values.
#:     Tends to make any rainstorm look intense.
#: 1 - more conventional scale (basically takes each color down a notch
#:     to look more like a conventional radar).
RADAR_MAP = 1
