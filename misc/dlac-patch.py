#!/usr/bin/env python3

"""Patch .978 file with DLAC changes.

This was used to patch the malformed data in TG13.
It is a one off hack.
"""
import sys, os

import fisb.level0.utilities as util

def dlacPatch():
    """Patch a bad testgroup. Specifically TG13.

    Reads a file called ``patch.dlac`` which contains a series
    of two lines. The first is the bad line to replace, and the
    second is the line to replace it with. There can be any number
    of these pairs. It makes a lot of assumptions that apply to TG13
    but not anything else.

    Will replace the text and also update the lengths in a couple of
    places.
    """
    
    # Read in patches and place in dictionary
    patchDict = {}

    with open('patch.dlac', 'r') as f:
        while True:
            # Read pairs of lines
            line1 = f.readline()
            if not line1:
                f.close()
                break

            line2 = f.readline()

            # Convert to DLAC
            line1 = util.textToDlac(line1.strip())
            line2 = util.textToDlac(line2.strip())

            # Key is what to search for. Value is what to change
            # it to.
            patchDict[line1] = line2

    patchKeys = list(patchDict.keys())

    # Now read lines from .978 packets to be converted.
    for line in sys.stdin:
        if (len(line) > 0) and (line[0] == '#'):
            continue
        line = line.strip()

        # See if we match
        for k in patchKeys:
            if k in line:
                # Update frame length
                addedNumChars = int(len(patchDict[k]) - len(k))
                newK = k + (addedNumChars * '0')
                #print(newK)

                line = line.replace(newK, patchDict[k])

                # Update frame length
                bytes12 = int(line[17:21], 16)
                currentFrameLength = (bytes12 & 0xFF80) >> 7
                newFrameLength = currentFrameLength + int( addedNumChars /2)
                newBytes12 = (newFrameLength << 7) | (bytes12 & 0x000F)

                newBytesAsString = '{:04X}'.format(newBytes12)
                line = line[0:17] + newBytesAsString + line[21:]

                # Now get TWGO record length
                bytesTwgo = int(line[43:47], 16)
                newBytesTwgo = bytesTwgo + int (addedNumChars/2)
                newBytesTwgoAsString = '{:04X}'.format(newBytesTwgo)
                line = line[0:43] + newBytesTwgoAsString + line[47:]

                break

        print(line)

if __name__ == "__main__":
    ## --- Script Code ---##
    dlacPatch()
