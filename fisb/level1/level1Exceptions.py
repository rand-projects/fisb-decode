"""Contains exceptions for level1 classes.
"""

class TwgoRecordsException(Exception):
    """Thrown if more than 1 TWGO record.
    """
    pass

class TwgoRecordFormatException(Exception):
    """Thrown if TWGO format not 2 or 8.
    """
    pass

class SegmentIdxOutOfBoundsException(Exception):
    """Thrown a segment index is greater than the number of segments.
    """
    pass

class TwgoUnexpectedCancellationException(Exception):
    """Thrown if cancellation in TWGO 11 or 12 types.
    """
    pass

