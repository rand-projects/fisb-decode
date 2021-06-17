"""Module containing harvest utility functions.
"""

import sys, os, time, random
from datetime import timezone, datetime

CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

CHARS_LEN_MINUS_1 = len(CHARS) - 1

def randomname(length, postfix = ''):
    """Create a random name of the specified length, add a postfix string
    if desired.

    Random name is created from the string in ``CHAR`` which consists of
    upper and lower alphabetic characters and digits. Mostly, this routine
    is used for creating filenames.

    Args:
        length (int): Number of characters to generate.
        postfix (str): String to append to the end. Usually an extension
            like ``'.png'``

    Returns:
        str: Random string with any ``postfix`` added to it.
    """
    name = ''
    for _ in range(0, length):
        name += CHARS[random.randint(0, CHARS_LEN_MINUS_1)]
    
    return name + postfix

def removeFilesWithExtension(dirPath, lastPart, olderThan = 0):
    """Remove all files ending with ``lastPart`` from the directory
    specified by ``dirPath``. If ``olderThan`` is greater than
    zero, only files older than ``olderThan`` seconds will be 
    deleted.

    If ``olderThan`` is zero (the default), all files ending in
    ``lastPart`` will be deleted. Typical usage to delete **all** files
    ending in ``'.png'`` from the web images directory would be: ::

        removeFilesWithExtension(cfg.WEB_IMAGE_DIRECTORY, '.png')

    To remove files only older than 110 minutes would be: ::

        removeFilesWithExtension(cfg.WEB_IMAGE_DIRECTORY, '.png', 110 * 60)

    Args:
        dirPath (str): Directory path the files must reside in.
        lastPart (str): Filename must end with this string in order to be
            deleted.
        olderThan (int): Number of seconds this file must not have been
            modified in order to be deleted. I.e.: the file must be older
            than this number of seconds.
    """
    
    # Get list of all files in dirPath
    filelist = os.listdir(dirPath)

    for item in filelist:
        fullPath = os.path.join(dirPath, item)
        if item.endswith(lastPart):

            # If file older than 'olderThan' seconds, remove it if
            # 'olderThan' has a positive value.
            if olderThan > 0:

                # Don't delete files that don't meet the criteria
                if os.stat(fullPath).st_mtime >= (time.time() - olderThan):
                    continue
            
            os.remove(fullPath)
