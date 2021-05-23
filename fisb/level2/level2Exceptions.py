"""Contains exceptions for level2 classes.
"""

class SegmentedMessageException(Exception):
    """Thrown if we see a segmented message at level2.
    """
    pass

class BadYearException(Exception):
    """Thrown if supplied year is not what is expected.
    """
    pass

class FAADateOutOfRangeException(Exception):
    """FAA date more than 10 days from current date.
    """
    pass

class Unknown413MessageTypeException(Exception):
    """413 message not ``METAR``, ``SPECI``, ``TAF``, ``TAF.AMD``, ``PIREP``, or ``WINDS``.
    """
    pass

class IllegalWindProductException(Exception):
    """Problem decoding winds aloft.
    """
    pass

class TooManyRecordsException(Exception):
    """Product has too many records.
    """
    pass

class RegexDidNotMatchException(Exception):
    """A regular expression that was expected to match did not.
    """
    pass

class IllegalTwgoMessageException(Exception):
    """Some parameter not set correctly in TWGO message.
    """
    pass

class G_AirmetMessageException(Exception):
    """Some parameter not set correctly in TWGO message.
    """
    pass

class TwgoHeaderParseException(Exception):
    """TWGO text did not match regular expression.
    """
    pass

class TwgoGeometryNotImplementedException(Exception):
    """TWGO geometry not 3, 4, 11, or 12.
    """
    pass

class SuaException(Exception):
    """Problems with ``SUA`` messages.
    """
    pass

class ScaleFactorException(Exception):
    """Illegal scale factor.
    """
    pass

class BadProductIdException(Exception):
    """Product ID not legal.
    """
    pass

class PirepFieldTooSmallException(Exception):
    """PIREP field length too short.
    """
    pass

class BadBinLengthException(Exception):
    """Bin length not 128.
    """
    pass

class TooManyPointsException(Exception):
    """Vertex of points had more than 1 point.
    """
    pass

class TooManyCirclesException(Exception):
    """Vertex of circles had more than 1 circles.
    """
    pass

class TooManyAltitudesException(Exception):
    """More than 2 altitudes in a vertex list.
    """
    pass

class AltitudesDontMatchException(Exception):
    """Two altitudes in a vertex list don't match.
    """
    pass

class BadOverlayTypeException(Exception):
    """Non-polygon or circle using overlay operator == 1.
    """
    pass

class GeoTypeMismatchException(Exception):
    """GeoType doesn't match when overlay operator == 1.
    """
    pass

class UnequalVertexLengthsException(Exception):
    """When overlay operator == 1, both vertexes must have same length.
    """
    pass

class IllegalCrlException(Exception):
    """Both text_flag and graphics_flag are set to zero in ``CRL`` message.
    """
    pass

class BadCrlTypeException(Exception):
    """Got ``CRL`` message with bad product_id.
    """
    pass
