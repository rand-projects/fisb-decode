"""Decode APDU 413 Generic DLAC Text Messages

``413`` messages include ``METAR``, ``TAF``, ``PIREP``, and ``WINDS & TEMP``
messages. These are stored as just plain DLAC text.
"""

import sys, os

import fisb.level0.utilities as util

def apdu_413(ba):
    """Return text contents of APDU 413 Generic Text Message.

    Args:
        ba (byte array): byte array with ``ba[0]`` pointing to the
            start of the DLAC text.

    Returns:
        str: String containing DLAC contents.
    """
    return util.dlacToText(ba, 0, len(ba))
