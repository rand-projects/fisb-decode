"""Decode APDU TWGO messages.

Process all TWGO (Text with Graphic Overlay) objects.

TWGOs encompass the following product types:

- (8)     NOTAM-D, NOTAM-FDC, NOTAM-TFR, Unavail FIS-B Products
- (11)    AIRMET
- (12)    SIGMET, Convective SIGMET (WST)
- (13)    SUA
- (14)    G-AIRMET
- (15)    CWA
- (16)    NOTAM-TRA
- (17)    NOTAM-TMOA

Not all TWGO objects have both text and graphic parts.

TWGO text only:

- SUA
- Unavailable FIS-B products

TWGO graphics only:

- G-AIRMET

TWGO has at least text and maybe graphics:

- NOTAM-D, NOTAM-FDC, NOTAM-TFR
- AIRMET
- SIGMET
- WST
- CWA

TWGO always has both text and graphics:

- NOTAM-TRA
- NOTAM-TMOA

The general rule is that for TWGO items that might have both
text and graphics, and you get the graphics part first, you squirrel
it away until the text part arrives. If the text part arrives first,
you send it off immediately and keep it around in case a graphics
part shows up. If you have both the text and graphics part, you send
it again as a complete message.
"""

import sys, os

from fisb.level0.utilities import dlacToText
from fisb.level0.utilities import convertRawLongitudeLatitude
from fisb.level0.utilities import GEO_19_BITS
from fisb.level0.utilities import GEO_18_BITS
from fisb.level0.level0Exceptions import ApduUnknownVertexTypeException
from fisb.level0.level0Exceptions import ApduUnimplementedOverlayOperatorException

def apdu_twgo(ba, productId, isDetailed):
    """Decode Text with Graphic Overlay (TWGO) messages.
    
    Will create a dictionary of all data in a TWGO payload, and all TWGO
    records.

    Args:
        ba (byte array): Byte array containing the TWGO data. ``ba[0]`` is
            position at the first byte of the TWGO payload header.
        productId (int): Needed for G-AIRMET which has
            different behavior for its specific product type.
        isDetailed (bool): If ``True``, provided more detailed information in the
            dictionary, not needed for normal FIS-B decoding.

    Returns:
        dict: Dictionary with the decoded data.
    """

    # Dictionary to contain decoded TWGO message
    d = {}

    # Parse header information

    # Tells whether graphic or text
    # 2 - Text
    # 8 - Graphic
    # other values reserved
    recordFormat = (ba[0] & 0xF0) >> 4
    d['record_format'] = recordFormat
    
    # Location
    d['location'] = dlacToText(ba, 2, 3)
    
    # Number of records to process
    recordCount = (ba[1] & 0xF0) >> 4
    d['record_count'] = recordCount

    # Means location is valid. Ignore if not 0x00 or 0xFF
    # For history... 0x00 is a FACILITY and 0xFF is EXTERNAL. Others
    # values (not used) are off the end of a runway. Values
    # other than 0x00 and 0xFF should cause the record to be
    # ignored.
    d['record_reference_point'] = ba[5]

    if isDetailed:
        # Product version number
        d['product_version'] = ba[0] & 0x0F

        d['reserved_2_58'] = ba[1] & 0x0F

    recordList = []
    
    # Split the work up depending if text records or graphical
    if recordFormat == 2:
        recordList = textRecords(ba[6:], recordCount, isDetailed)
    elif recordFormat == 8:
        recordList = graphicRecords(ba[6:], recordCount, \
                                     productId, isDetailed)

    d['records'] = recordList

    return d

def textRecords(ba, recordCount, isDetailed):
    """Decode unformatted DLAC text entries.

    Given a byte array pointing to the first TWGO text record, decode
    all available records and return it as a list.

    Args:
        ba (byte array): Byte array where ``ba[0]`` is the first byte of a TWGO text record.
        recordCount (int): Number of text records to process.
        isDetailed (bool): Provide more detailed decoding if ``True``. This is not
            needed for normal record processing. If ``False``, just do the normal
            decoding.

    Returns:
        list: A list with one entry for every decoded text record.
    """
    recordList = []

    # ros -> relative offset into ba
    ros = 0
    
    for _ in range(0, recordCount):
        d = {}

        # Number of bytes in record, includes first 5 header bytes
        textRecordLength = (ba[ros] << 8) | \
                                  ba[ros + 1]
        d['text_record_length'] = textRecordLength

        # Report number for this report. This is not all that is needed
        # to uniquely identify a document.
        d['report_number'] = (ba[ros + 2] << 6) | \
                             (ba[ros + 3] >> 2)

        # Last two digits of the year of report, except for
        # NOTAM-TFR and NOTAM-D where only the last digit of the
        # year is sent.
        d['report_year'] = ((ba[ros + 3] & 0x03) << 5) | \
                           ((ba[ros + 4] & 0xF8) >> 3)

        # 0 - Cancelled
        # 1 - Active
        reportStatus = (ba[4] & 0x04) >> 2
        d['report_status'] = reportStatus

        if isDetailed:
            d['reserved_5_78'] = ba[4] & 0x03

        # Contents of the report (show only if not cancelled)
        if reportStatus == 1:
            d['text'] = dlacToText(ba, ros + 5, \
                                textRecordLength - 5)

        recordList.append(d)

        ros += textRecordLength

    return recordList

def graphicRecords(ba, recordCount, productId, isDetailed):
    """Decode unformatted graphic entries.

    Given a byte array pointing to the first TWGO graphic record, decode
    all available records and return it as a list.

    Args:
        ba (byte array): Byte array where ``ba[0]`` is the first byte of a TWGO graphic record.
        recordCount (int): Number of graphic records to process.
        productId (int): Product id of the message.
        isDetailed (bool): Provide more detailed decoding if ``True``. This is not
            needed for normal record processing.

    Returns:
        list: A list with one entry for every decoded graphic record.

    Raises:
        ApduUnimplementedOverlayOperatorException: If we find an overlay operator
            we did not implement.
        ApduUnknownVertexTypeException: For unimplemented vertexes.
    """

    recordList = []

    # os points to the beginning of a record
    # At the end of each record it will get
    # incremented to the next record (by adding
    # overlayRecordLength).
    os = 0
    
    for _ in range(0, recordCount):
        d = {}

        # ros is the record offset for this record only.
        # It gets set to 'os', the beginning of the new
        # record.
        ros = os

        # Number of bytes in this overlay record
        overlayRecordLength = (ba[ros] << 2) | \
                                ((ba[ros + 1] & 0xC0) >> 6)
        d['overlay_record_length'] = overlayRecordLength

        # Report number for this report. This is not all that is needed
        # to uniquely identify a document.
        d['report_number'] = ((ba[ros + 1] & 0x3F) << 8) | \
                             ba[ros + 2]

        # Last two digits of the year of report, except for
        # NOTAM-TFR and NOTAM-FDC where only the last digit of the
        # year is sent.
        d['report_year'] = ba[ros + 3] >> 1

        # Applies to NOTAM-D, -TFR, -FDC, -TRA, and -TMOA. 
        # These are the number of years to add or subtract to the report year
        # to know when the NOTAM was in effect or will expire.
        # The record applicability options field may change the meaning of
        # these values.
        d['record_applicability_start_year'] = ((ba[ros + 3] & 0x01) << 1) | \
                                               ((ba[ros + 4] & 0x80) >> 7)
        
        d['record_applicability_end_year'] = ((ba[ros + 4] & 0x60) >> 5)

        # Number of overlay records
        d['overlay_record_id'] = ((ba[ros + 4] & 0x1E) >> 1) + 1
        
        # 0 - object label field is numeric
        # 1 - object label field is alphanumeric
        # For DO-258A and later, 0 means no object label and 1 is
        # an airport location id.
        labelFlag = ba[ros + 4] & 0x01
        d['label_flag'] = labelFlag

        # Set the offset to point to the object label. From here on
        # we enter places where the offset changes dependent on state.
        ros = os + 5

        # The object label 2 bytes are ignored if labelFlag is
        # 0. If 1, it is nine bytes of DLAC
        objectLabel = ''
        if (labelFlag == 0):
            ros += 2
        else:
            objectLabel = dlacToText(ba, ros, 9)
            ros += 9

        d['object_label'] = objectLabel
        
        # If 1, object element is used. Else no.
        d['element_flag'] = (ba[ros] & 0x80) >> 7

        # If 1, object qualifier field is used. Else not.
        qualFlag = (ba[ros] & 0x40) >> 6
        d['qual_flag'] = qualFlag

        # If 1, object parameter type and object parameter
        # value fields are present. Else not.
        paramFlag = (ba[ros] & 0x20) >> 5
        d['param_flag'] = paramFlag

        # 0 - TFR
        # 1 - TURB
        # 2 - LLWS
        # 3 - SFC
        # 4 - ICING
        # 5 - FRZLVL
        # 6 - IFR
        # 7 - MTN
        # 8-15 reserved
        # DO-358A and later also state that any object element
        #  associated with an aerodrome object type should be
        #  discarded.
        d['object_element'] = ba[ros] & 0x1F
        ros += 1
        
        # Object types
        # 00  - Airport
        # 14  - Airspace
        # 15  - Reserved
        #
        # Past values not used anymore
        # 01  - Runway
        # 02  - Taxiway
        # 03  - Apron
        # 04  - Frequency area
        # 05  - Signage
        # 06  - Approach lighting
        # 07  - Airport lighting
        # 08  - Obstruction
        # 09  - Construction
        # 10  - Communication equip.
        # 11  - Navigation equip.
        # 12  - Surveillance equip.
        # 13  - Weather equip.
        d['object_type'] = (ba[ros] & 0xF0) >> 4

        # State of the object
        # 13  - Cancelled
        # 15  - In effect
        #
        # Past values not used anymore
        # 00  - Closed
        # 01  - Conditionally closed
        # 02  - Arrival only
        # 03  - Departure only
        # 04  - Displaced
        # 05  - Braking action
        # 06  - Obscured/missing
        # 07  - Unmarked
        # 08  - Unlighted
        # 09  - In service
        # 10  - Inoperative
        # 11  - Unavailable
        # 12  - Surface condition
        # 14  - Unsafe
        d['object_status'] = ba[ros] & 0x0F
        ros += 1

        # 3 bytes of object qualifier only applies if qualFlag is 1 and
        # the product type is G-AIRMET (14)
        if (productId == 14) and (qualFlag == 1):
            # Items in the qualList contain attributes of the type of AIRMET,
            # such as smoke, fog, mist, etc. There can be up to 3 attributes.
            # This is actually a bitmap. See table A-54 in DO-358B.
            # You can also see '_decodeObjectQualifiersList()' in
            # level3/msg14.py where this is decoded.
            qualList = []
            qualList.append(ba[ros])
            qualList.append(ba[ros + 1])
            qualList.append(ba[ros + 2])
            d['object_qualifiers'] = qualList
            ros += 3

        # Per the standard, if paramFlag is set, the objectParameterType and
        # objectParameterValue should be ignored. In fact, the entire record
        # should be ignored.
        if paramFlag == 1:
            if isDetailed:
                d['object_parameter_type'] = (ba[ros] & 0xF8) >> 3
                d['object_parameter_value'] = ((ba[ros] & 0x07) << 8) | \
                                              ba[ros + 1]
            ros += 2

        # Gives information about start and end times
        # 0 - No times specified
        # 1 - Start time only
        # 2 - End time only
        # 3 - Both start and end times
        recordApplicabilityOptions = (ba[ros] & 0xC0) >> 6
        d['record_applicability_options'] = recordApplicabilityOptions
        
        # Defines the format of the record applicability fields
        # 0 - no date time format
        # 1 - month day hours and minutes
        # 2 - day, hours, minutes (not used, but we check for it anyway)
        # 3 - hours minutes
        #
        # Per DO-358B, if the record_applicability_options
        # is zero (no times), the date_time_format can be ignored.
        # If it is not 0, and date_time_format is 0 or 2, the record can
        # be discarded.
        dateTimeFormat = (ba[ros] & 0x30) >>4
        d['date_time_format'] = dateTimeFormat
        
        # Defines the type of geometry used
        #  3 - Extended Range 3D Polygon (MSL)
        #  4 - Extended Range 3D Polygon (AGL)
        #  7 - Extended Range Circular Prism (MSL)
        #  8 - Extended Range Circular Prism (AGL)
        #  9 - Extended Range 3D Point (AGL)
        # 10 - Extended Range 3D Point (MSL)
        # 11 - Extended Range 3D Polyline (MSL)
        # 12 - Extended Range 3D Polyline (AGL)
        #
        # Not used anymore:
        #  5 - Low resolution 2D Ellipse
        #  6 - High resolution 3D Ellipse
        #
        # other values reserved
        overlayGeometryOptions = ba[ros] & 0x0F
        d['overlay_geometry_options'] = overlayGeometryOptions
        ros += 1

        # Overlay operator values of 1 used in
        # NOTAM -TRA and -TMOA as of DO-358B.
        # 
        # 0 - Graphical overlay records independent
        # 1 - Graphical overlay records dependent and
        #     must be combined. In the past, this used to be
        #     called the 'AND' geometry operator.  
        #
        # Not used anymore:
        # 2 - 'NOT' geometry operator.
        #
        # 3 - Reserved
        d['overlay_operator'] = (ba[ros] & 0xC0) >> 6

        # For now, cause an exception if we get an overlay operator
        # other than 0. 0 is expected, and 1 is allowed in 
        # NOTAM-TMOA and NOTAM-TRA.
        if d['overlay_operator'] in [2, 3]:
            raise ApduUnimplementedOverlayOperatorException\
                ('Unimplemented Overlay Operator: {}'\
                .format(d['overlay_operator']))

        # Field only present if the overlay geometry option is
        # not zero. Can contain up to 64 polygon vertices. One is
        # added to get the correct count
        verticesCount = 0
        if overlayGeometryOptions != 0:
            verticesCount = (ba[ros] & 0x3F) + 1
            d['overlay_vertices_count'] = verticesCount
        ros += 1

        # Decode and record applicability start and stop times
        if (recordApplicabilityOptions == 1) | \
           (recordApplicabilityOptions == 3):
            # start times
            if dateTimeFormat == 1:
                d['start_month'] = ba[ros]
                d['start_day'] = ba[ros + 1]
                d['start_hour'] = ba[ros + 2]
                d['start_minute'] = ba[ros + 3]
                ros += 4
            elif dateTimeFormat == 2:
                d['start_day'] = ba[ros]
                d['start_hour'] = ba[ros + 1]
                d['start_minute'] = ba[ros + 2]
                ros += 3
            elif dateTimeFormat == 3:
                d['start_hour'] = ba[ros]
                d['start_minute'] = ba[ros + 1]
                ros += 2

        if (recordApplicabilityOptions == 2) | \
           (recordApplicabilityOptions == 3):
            # stop times
            if dateTimeFormat == 1:
                d['stop_month'] = ba[ros]
                d['stop_day'] = ba[ros + 1]
                d['stop_hour'] = ba[ros + 2]
                d['stop_minute'] = ba[ros + 3]
                ros += 4
            elif dateTimeFormat == 2:
                d['stop_day'] = ba[ros]
                d['stop_hour'] = ba[ros + 1]
                d['stop_minute'] = ba[ros + 2]
                ros += 3
            elif dateTimeFormat == 3:
                d['stop_hour'] = ba[ros]
                d['stop_minute'] = ba[ros + 1]
                ros += 2

        vertexList = []
        
        # Process any vertices
        for _ in range(0, verticesCount):
            # Decode based on geometry encoding
            # There used to be a bigger set of these.
            if overlayGeometryOptions in [7, 8]:
                (longitudeBottom, latitudeBottom, \
                 longitudeTop, latitudeTop, \
                 zBottom, zTop, \
                 rMajor, rMinor, \
                 alpha) = decode14ByteVertex(ba, ros)
                ros += 14

                vertexList.append([longitudeBottom, latitudeBottom, \
                                   longitudeTop, latitudeTop, \
                                   zBottom, zTop, rMajor, rMinor, \
                                   alpha])
                
            elif overlayGeometryOptions in [3, 4, 9, 10, 11, 12]:
                (longitude, latitude, z) = decode6ByteVertex(ba, ros)
                ros += 6

                vertexList.append([longitude, latitude, z])
            else:
                raise ApduUnknownVertexTypeException('Unknown vertex type {}'.format(overlayGeometryOptions))
            
        # Add vertices if we have any
        if verticesCount > 0:
            d['vertex_list'] = vertexList

        # Go to next record
        os += overlayRecordLength

        recordList.append(d)
        
    return recordList

def decode6ByteVertex(ba, ros):
    """Turn a 6 byte vertex into latitude and longitude.

    Args:
        ba (byte array): Byte array containing the data.
        ros (int): Relative offset into ``ba``.

    Returns:
        tuple: 3 item tuple:
        
        1. longitude
        2. latitude
        3. alpha (in 100's of feet, so the raw answer is multiplied * 100).
    """

    longRaw = (ba[ros + 0] << 11) | \
              (ba[ros + 1] << 3) | \
              ((ba[ros + 2] & 0xE0) >> 5)
    latRaw = ((ba[ros + 2] & 0x1F) << 14) | \
             (ba[ros + 3] << 6) | \
             ((ba[ros + 4] & 0xFC) >> 2)
    alpha = ((ba[ros + 4] & 0x03) << 8) | \
            ba[ros + 5]

    (longitude, latitude) = convertRawLongitudeLatitude(longRaw, \
                                                        latRaw, \
                                                        GEO_19_BITS)

    # Alpha is in 100's of feet, so multiply x 100
    alpha *= 100
    
    return (longitude, latitude, alpha)

def decode14ByteVertex(ba, ros):
    """Turn a 14 byte vertex into latitude and longitude.

    Args:
        ba (byte array): Byte array containing the data.
        ros (int): Relative offset into ``ba``.
    
    Returns:
        tuple: Tuple containing the following:
        
        1. longitude bottom
        2. latitude bottom
        3. longitude top
        4. latitude top
        5. z bottom
        6. z top
        7. r major
        8. r minor
        9. alpha

        Z bottom and top are multiplied * 500 feet and r major
        and minor are multiplied by 0.2 for NM.
    """
    longBotRaw = (ba[ros + 0] << 10) | \
                 (ba[ros + 1] << 2) | \
                 ((ba[ros + 2] & 0xC0) >> 6)
    latBotRaw = ((ba[ros + 2] & 0x3F) << 12) | \
                (ba[ros + 3] << 4) | \
                ((ba[ros + 4] & 0xF0) >> 4)
    longTopRaw = ((ba[ros + 4] & 0x0F) << 14) | \
                 (ba[ros + 5] << 6) | \
                 ((ba[ros + 6] & 0xFC) >> 2)
    latTopRaw = ((ba[ros + 6] & 0x03) << 16) | \
                (ba[ros + 7] << 8) | \
                ba[ros + 8]

    (longitudeBottom, \
     latitudeBottom) = convertRawLongitudeLatitude(longBotRaw, \
                                                   latBotRaw, \
                                                   GEO_18_BITS)

    (longitudeTop, \
     latitudeTop) = convertRawLongitudeLatitude(longTopRaw, \
                                                latTopRaw, \
                                                GEO_18_BITS)

    zBottom = (ba[ros + 9] & 0xFE) >> 1
    zTop = ((ba[ros + 9] & 0x01) << 6) | \
           ((ba[ros + 10] & 0xFC) >> 2)
    rMajor = ((ba[ros + 10] & 0x03) << 7) | \
             ((ba[ros + 11] & 0xFE) >> 1)
    rMinor = ((ba[ros + 11] & 0x01) << 8) | \
             ba[ros + 12]
    alpha = ba[ros + 13]

    # z is in increments of 500 feet
    zBottom *= 500
    zTop *= 500

    # r is increments of 0.2 NM
    rMajor *= 0.2
    rMinor *= 0.2

    return (longitudeBottom, latitudeBottom, \
            longitudeTop, latitudeTop, \
            zBottom, zTop, rMajor, rMinor, alpha)
