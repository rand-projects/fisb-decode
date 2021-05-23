"""Module containing utility functions for level3
"""

import sys, os, time

# Just using the time as a filename does not provide enough
# granularity. 'appendedCounter' is a global that will vary 
# between 0 and 99. This will prevent the problem of fast
# arriving files (like images) overwriting themselves and 
# causing missing blocks.
appendedCounter = 0

def writeToFile(msg, outputDir):
    """Write contents of ``msg`` to disk file with time as filename.

    The filename is the ``time.time() * 10000`` with an added counter
    of 00 to 99. The initial extension will be
    ``.tmp`` which is renamed to ``.msg`` after the write is complete 
    and the file is closed.

    Args:
        msg (str): Message to write. This will be a json string.
        outputDir (str): Output directory
    """
    global appendedCounter

    currentTime = time.time()
    baseFilename = '{}-{:02d}'.format(int(currentTime * 10000), appendedCounter)
    tempFilename = baseFilename + '.tmp'
    renameFilename = baseFilename + '.msg'

    # appendedCounter goes between 0 and 99
    appendedCounter += 1
    if appendedCounter >= 100:
        appendedCounter = 0

    # Write file with .tmp extension and rename it to .msg
    with open(os.path.join(outputDir, tempFilename), "w") as oFile:
              oFile.write(msg + '\n')

              os.rename(os.path.join(outputDir, tempFilename), \
              os.path.join(outputDir, renameFilename))
