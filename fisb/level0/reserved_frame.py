import sys, os

"""Contains a Reserved Frame.

Reserved frames are frames that are normally not decoded. They
consist of a type 1 frame, which is used for development, and 
types 2-13 which are reserved for future use.

This is only called when detailed decoding is being done.
"""
def decodeReservedFrame(ba, frameLength, reserved_2_24, frameType):
    """Contains a Reserved Frame.

    Reserved frames contain data that is not yet part of the official
    standard.

    Args:
        ba (byte array): Byte array which contains all the bytes of the frame.
        frameLength (int): Number of bytes in the current frame.
        reserved_2_24 (int): Reserved bits in frame header.
        frameType (int): Type of reserved frame.

    Returns:
        dict: Dictionary with decoded data. The ``content`` key of the dictionary
        will contain the hex string of the contents for evaluation.
    """
    d = {}

    # frameType
    # Holds the number defining the type of frame. This will be one of:
    # 01        Development frame type
    # 02 - 13   Reserved frame types
    d['frame_type'] = frameType

    d['frameheader_2_24'] = reserved_2_24

    # frameContents
    # Holds the contents of the frame. Normally frames don't have to
    # save their contents-- they get fully decoded. For unknown frames,
    # we store the contents for future study.
    d['content'] = ba.hex()

    return d
