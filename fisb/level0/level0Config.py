"""Level0 configuration information.
"""

#: Filename used to record frames that error out during decoding.
ERROR_FILENAME = 'LEVEL0.ERR'

#: Set to ``True`` to skip empty frames (heartbeat).
SKIP_EMPTY_FRAMES = True

#: Set to ``True`` to output detailed messages. Detailed messages
#: contain fields not normally used in decoding.
DETAILED_MESSAGES = False

#: Set to ``True`` if SUA (Special Use Airspace, TWGO type 13) messages should be blocked.
#: Required to be ``True`` to pass test groups.
BLOCK_SUA_MESSAGES = False

#: Set to ``False`` if we block frame type 15 service status messages.
#: If ``True``, these messages will be passed.
#: Set to ``False`` for testing. *Service Status* lets you know
#: how many (and which) aircraft are getting TIS-B 'hockey puck'
#: assistance  from the ground station.
ALLOW_SERVICE_STATUS = True

#: Set to ``True`` to archive messages in a file. Storing
#: messages in an archive is a good thing if you want to keep
#: all messages you received in case you want to review them
#: or extract certain data. Each day (based on UTC) is stored
#: as a new file in the form ``YYYY-MM-DD.978``. It's a good idea
#: to compress old files as each file is about 155MB from a
#: medium tier (3 messages a second) station.
ARCHIVE_MESSAGES = False

#: Directory to store archived messages in.
ARCHIVE_DIRECTORY = '../runtime/msg-archive'

#: If ``False``, write to standard output (normal case).
#: If ``True``, write each message as an individual
#: file to the directory ``MESSAGE_DIRECTORY``. Not used
#: very much.
WRITE_MESSAGE_TO_FILE = False

#: Directory to store messages in if ``WRITE_MESSAGE_TO_FILE`` is ``True``.
MESSAGE_DIRECTORY = '/share/fis-b/level0-out'

#: Show the original message in the output. Useful for
#: creating a set of test messages. In normal use, should
#: be set to ``False``.
SHOW_MESSAGE_SOURCE = False

#: If ``True``, calculate the '*reception success rate*'.
#: The RSR is basically the number of messages we got from a particular
#: station, vs the number of messages we would expect to get (expressed
#: as a percentage). To be standard compliant, it needs to be set to ``True``
#: and needs to be calculated every second (``RSR_CALCULATE_EVERY_X_SECS``)
#: using the previous
#: 10 seconds (``RSR_CALCULATE_OVER_X_SECS``) of data. For ground use,
#: this is helpful if you have
#: problems with fading, but otherwise can be turned off, or at least set
#: to a higher value like every 30 seconds, vs every second.
#: Set to ``True`` for TG06 test. 
CALCULATE_RSR = True

#: Calculate and store the RSR every '*this
#: many seconds*'. For testing, set this to ``1``.
#: If you have a system that refreshes every
#: 30 seconds, set this to 30.
RSR_CALCULATE_EVERY_X_SECS = 30

#: Calculate the RSR over this many seconds.
#: This is different from ``RSR_CALCULATE_EVERY_X_SECS``.
#: That calculates and stores in the database every
#: so many seconds. This parameter defines over how many
#: past seconds must the RSR be calculated from.
#: For testing, this must be ``10``. If you have a
#: system that refreshes every 30 seconds,
#: set this to 30. That way the result will
#: include data over the entire interval.
RSR_CALCULATE_OVER_X_SECS = 30

#: Uses the expected packet count per second for 
#: calculating RSR instead of a count. This is
#: based on the tier of the station (SFC, low, medium
#: or high).
#: DO NOT use this for TG06 test. They alter the
#: packets and using the expected value doesn't
#: work.
RSR_USE_EXPECTED_PACKET_COUNT = True

#: MONGO URL (used only for RSR)
#: This won't be used at all if ``CALCULATE_RSR`` is ``False``.
MONGO_URL = 'mongodb://localhost:27017/'

#: Enable this only for test group testing.
#: Per the standard, you can use all 6 bits for a
#: DLAC tab, but the test samples seem to limit this 
#: to 4 bits.
#: Set to ``False`` for normal operation (if you don't
#: you run a risk of DLAC decoding not working).
DLAC_4BIT_HACK = False

#: Path to where the test group generated files are
#: located. Used only when using the --test option.
GENERATED_TEST_DIR = '../tg/tg-source/generated'
