"""Level1 configuration information.
"""

#: Number of minutes the message can sit in the Unsegmenter
#: before it is expunged.
SEGMENT_EXPIRE_TIME = 60

#: Number of minutes non-matched TWGO parts are held.
TWGO_EXPIRE_TIME = 720  # 12 Hours

#: We call the expunger every so many minutes. This is NOT
#: when things will get expunged, just the interval when we
#: call the specific item expungers.
EXPUNGE_CHECK_MINUTES = 30

#: Where to write error messages.
ERROR_FILENAME = 'LEVEL1.ERR'

#: If ``False``, messages will be read from standard input.
#: If ``True``, messages are assumed to have been written by level0 in a
#: directory. Messages
#: will be read and processed from ``READ_MESSAGES_DIRECTORY``.
READ_MESSAGES_FROM_FILE = False

#: Messages will be read and then deleted from this directory.
READ_MESSAGES_DIRECTORY = '/share/uat-messages'
