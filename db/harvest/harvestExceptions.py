"""Contains exceptions for harvest.
"""

class TGNumberNotInStartDatesException(Exception):
    """The specified TG number not found in ``start-dates.csv``.
    """
    pass

class UnknownCrlException(Exception):
    """Got an unknown CRL type.
    """
    pass

class UndefinedImageFunctionException(Exception):
    """Passed an illegal image type.
    """
    pass

class UnknownGeometryType(Exception):
    """Geometry type not one of ``POLYGON``, ``POINT``, ``POLYLINE``, or ``CIRCLE``.
    """
    pass