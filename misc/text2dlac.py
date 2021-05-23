#!/usr/bin/env python3

"""Convert text strings to DLAC

Assumes the string contains valid dlac. Will throw an error
if it doesn't.

Used to develop patches for bad test group messages.

Put the messages in a file and ``cat`` them to this program
Comments are allowed in the form of ``#``.
"""
import sys, os

import fisb.level0.utilities as util

def text2dlac():
    """Convert text strings to DLAC.

    See module comments for details.
    """
    for line in sys.stdin:
        if (len(line) > 0) and (line[0] == '#'):
            continue
        line = line.rstrip()

        print(util.textToDlac(line))

if __name__ == "__main__":
    ## --- Script Code ---##
    text2dlac()
