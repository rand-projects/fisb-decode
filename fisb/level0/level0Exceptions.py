"""Contains exceptions for level0 classes.
"""

class GroundUplinkLengthException(Exception):
    """Thrown if Ground Uplink Message not 432 bytes.
    """
    pass

class GroundUplinkBadRecordException(Exception):
    """Thrown if Ground Uplink Message doesn't start with '@' or '+'.
    """
    pass

class ApduUnknownProductException(Exception):
    """Thrown if trying to dispatch on illegal product number.
    """
    pass

class ApduUnknownVertexTypeException(Exception):
    """Thrown if we try to handle an unknown vertex type.
    """
    pass

class ApduTooManyBinsException(Exception):
    """Thrown if we get an illegal bin count.
    """
    pass

class ApduLightningBinsException(Exception):
    """Thrown if we get an illegal bin count for lightning run length.
    """
    pass

class ApduUnimplementedOverlayOperatorException(Exception):
    """Thrown if we get an unimplemented overlay operator type.
    """
    pass


class BadBitHeaderException(Exception):
    """Thrown if the normalized bit header length not 99.
    """
    pass

class BadApduProductIdException(Exception):
    """Thrown if we got a bad APDU type.
    """
    pass

class BadTestNumberException(Exception):
    """Thrown if we get a bad test number (out of range)
    """
    pass
