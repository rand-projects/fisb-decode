"""Level3 configuration information
"""
#: Filename used to record frames that error out during decoding.
ERROR_FILENAME = 'LEVEL3.ERR'

#: Expire messages that have not been seen in this many minutes
#: The longest interval time between sending is 15 minutes for some
#: image products, so time should be greater than this.
EXPIRE_MSG_TIME_MINS = 45

#: Run the process to clean out the hash table every this number
#: of minutes.
EXPUNGE_HASHTABLE_MINS = 10

#: For the standard, PIREPs should expire >= 75 minutes after the time of last reception.
#: To be standard compliant, set this to ``False```.
#: Setting this to ``True`` decreases processor
#: time and doesn't really affect desired behavior. This is especially
#: true if using PIREP augmentation to add location information. It 
#: will greatly decrease database lookups.
PIREP_STORE_LEVEL3 = False

#: Set to ``True`` if the message should be printed to standard output.
#: If you use pretty printing (``--pp``) this will be forced to True.
PRINT_TO_STDOUT = False

#: Set to ``True`` to write the message to the ``OUTPUT_DIRECTORY``.
#: Both ``PRINT_TO_STDOUT`` and ``WRITE_TO_FILE`` can be ``True``.
#: This should be set to ``True`` if feeding Harvest with data.
#: If you use pretty printing (``--pp``) this will be forced to False.
WRITE_TO_FILE = True

#: Directory to store processed files to when ``WRITE_TO_FILE`` is
#: ``True``. This is mostly for processing by Harvest.
OUTPUT_DIRECTORY = "../runtime/harvest"
