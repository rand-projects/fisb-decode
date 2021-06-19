"""Module containing image functions for harvest

All images are geolocated PNG files.

Images use an 'alternate block number' which is described better elsewhere (see
:func:`fisb.level2.msgBlock.alternateBlockNumber`),
The stock block number of the standard is somewhat difficult to use. The alternate
block number is simply an y,x coordinate system. The 1st three digits is the *y*
coordinate (latitude). The seconds 3 digits is the *x* coordinate (longitude).

The advantage of this system when making images is that it is trivial to compute 
max x and y bounds and thus the bounding block for an image.
"""

import numpy as np
import os
import db.harvest.imagemap as imap
import db.harvest.harvestConfig as cfg
from osgeo import gdal
from osgeo import osr

# Default values for pixels
NOT_INCLUDED_RED = cfg.NOT_INCLUDED_RED
NOT_INCLUDED_GREEN = cfg.NOT_INCLUDED_GREEN
NOT_INCLUDED_BLUE = cfg.NOT_INCLUDED_BLUE

# Byte Functions take a byte (pixel) from the image and
# returns the byte to map to an image map (color). For 
# most images this is simply the byte itself. However,
# lightning and icing data have 2 (lightning) or 3 (icing)
# data items per byte, so each of these needs more than 
# a single function.

def simpleByteFcn(c):
    """Return integer value of supplied pixel.

    Args:
        c (unicode): Unicode pixel.

    Returns:
        int: Value of pixel.
    """
    return ord(c)

def icingByteFcnSLD(c):
    """Return Super Large Droplet value of icing pixel.

    Args:
        c (unicode): Unicode icing pixel.

    Returns:
        int: Value of Super Large Droplet portion of icing pixel.
    """
    return (ord(c) >> 6) & 0x03

def icingByteFcnSEV(c):
    """Return severity value of icing pixel.

    Args:
        c (unicode): Unicode icing pixel.

    Returns:
        int: Value of severity portion of icing pixel.
    """
    return (ord(c) >> 3) & 0x07    

def icingByteFcnPRB(c):
    """Return probability value of icing pixel.

    Args:
        c (unicode): Unicode icing pixel.

    Returns:
        int: Value of probability portion of icing pixel.
    """
    return ord(c) & 0x07    

def lightningByteFcnALL(c):
    """Return lightning pixel with all strike values.

    Args:
        c (unicode): Unicode lightning pixel.

    Returns:
        int: Lightning pixel including positive and negative strikes.
    """
    # ignore polarity
    return ord(c) & 0x07    

def lightningByteFcnPOS(c):
    """Return lightning pixel with only positive strike values.

    Args:
        c (unicode): Unicode lightning pixel.

    Returns:
        int: lightning pixel including only positive strikes.
    """
    # only positive polarity
    x = ord(c)
    if (x & 0x08) != 0:
        x = x & 0x07
    else:
        x = 0

    return x

# Resolution. Primary index is
# FIS-B resolution (high=0, med=1, low=2).
# Within each row is:
#  0 resLatPerBin
#  1 resLongPerBin
#  2 blocks per revolution
RES = [[1.0, 1.5, 450], \
        [5.0, 7.5, 90], \
        [9.0, 13.5, 50]]

def mapFcnRadar(imageType):
    """Return the image map to use and byte function for radar images.

    Args:
        imageType (str): Type of image from the fisb level2 message ``type`` slot.

    Returns:
        tuple: Tuple:

        1. (dict) Radar image map.
        2. (function) Byte function to use (:func:`simpleByteFcn`).
    """
    return (imap.RADAR_MAP, simpleByteFcn)

def mapFcnTurb(imageType):
    """Return the image map to use and byte function for turbulence images.

    Args:
        imageType (str): Type of image from the fisb level2 message ``type`` slot.

    Returns:
        tuple: Tuple:

        1. (dict) Turbulence image map.
        2. (function) Byte function to use (:func:`simpleByteFcn`).
    """
    return (imap.TURB_MAP, simpleByteFcn)

def mapFcnCloudTops(imageType):
    """Return the image map to use and byte function for cloud tops images.

    Args:
        imageType (str): Type of image from the fisb level2 message ``type`` slot.

    Returns:
        tuple: Tuple:

        1. (dict) Cloud top image map.
        2. (function) Byte function to use (:func:`simpleByteFcn`).
    """
    return (imap.CLOUDTOP_MAP, simpleByteFcn)

def mapFcnLightning(imageType):
    """Return the image map to use and byte function for lightning images.

    Args:
        imageType (str): Type of image from the fisb level2 message ``type`` slot.

    Returns:
        tuple: Tuple:

        1. (dict) Image map to use. One of all strokes, or just positive strokes.
        2. (function) Byte function to use (either :func:`lightningByteFcnALL` or
           :func:`lightningByteFcnPOS`).
    """
    if 'ALL' in imageType:
        byteFcn = lightningByteFcnALL
    elif 'POS' in imageType:
        byteFcn = lightningByteFcnPOS

    return (imap.LIGHTNING_MAP, byteFcn)

def mapFcnIcing(imageType):
    """Return the image map to use and byte function for icing images.

    Args:
        imageType (str): Type of image from the fisb level2 message ``type`` slot.

    Returns:
        tuple: Tuple:

        1. (dict) Image map to use. One of the the SLD map, severity map,
           or probability map.
        2. (function) Byte function to use (One of :func:`icingByteFcnSLD`,
           :func:`icingByteFcnSEV`, or :func:`icingByteFcnPRB`).
    """
    if 'SLD' in imageType:
        map = imap.ICING_SLD_MAP
        byteFcn = icingByteFcnSLD
    elif 'SEV' in imageType:
        map = imap.ICING_SEV_MAP
        byteFcn = icingByteFcnSEV
    elif 'PRB' in imageType:
        map = imap.ICING_PRB_MAP
        byteFcn = icingByteFcnPRB            

    return (map, byteFcn)

def splitBinNum(binNum):
    """Split an alternate block number into latitude and longitude parts.

    Args:
        binNum (int): Alternative block number

    Returns:
        :tuple Tuple:
        
        1. (int) Latitude portion of the alternate block number.
           Example: ``614123`` => ``614`` 
        2. (int) Longitude portion of the alternate block number.
           Example: ``614123`` => ``123`` 
    """
    latBin = int(binNum / 1000)
    longBin = binNum - (latBin * 1000)

    return (latBin, longBin)

UL = 0 # Upper Left
LL = 1 # Lower Left
UR = 2 # Upper Right
LR = 3 # Lower Right

def getCoordsOfSplitBin(latBin, longBin, corner, res):
    """Given latitude and longitude parts of bin number, return actual
    latitude and longitude.

    Args:
        latbin (int): Latitude part of alternate block number.
        longBin (int): Longitude part of alternate block number.
        corner (int): Which corner of the block returned coordinates should be:

          * 0 - upper left
          * 1 - lower left
          * 2 - upper right
          * 3 - lower right

        res (int): Resolution of image block:

          * 0 - high
          * 1 - medium
          * 2 - low (never used)

    Returns:
        :tuple Tuple:
        
        1. (float) Latitude in degrees.
        2. (float) Longitude in degrees.
    """
    # Get the bin UL lat and long in pixels 
    pLong = (RES[res][2] - longBin) * 32
    pLat = (latBin + 1) * 4

    if corner in [LL, LR]:
        pLat = pLat - 4

    if corner in [UR, LR]:
        pLong = pLong - 32

    # Convert to degrees
    lat = (pLat * RES[res][0]) / 60.0
    long = -((pLong * RES[res][1]) / 60.0)

    return (lat, long)

def getBoundingBox(maxLatBin, minLatBin, maxLongBin, minLongBin, res):
    """Given 4 corner alternate block numbers, determine the image bounding box
    in latitude and longitude.

    Args:
        maxLatBin (int): Maximum latitude bin.
        minLatBin (int): Minimum latitude bin.
        maxLongBin (int): Maximum longitude bin.
        minLongBin (int): Minimum longitude bin.
        res (int): Resolution of image block

            * 0 - high
            * 1 - medium
            * 2 - low (never used)

    Returns:
        :tuple Tuple of 4 items-- each a tuple of two items
        (the latitudes and longitudes in the tuples are ``float``
        values).

          1. tuple of (lat, long) of upper left corner
          2. tuple of (lat, long) of lower left corner
          3. tuple of (lat, long) of upper right corner
          4. tuple of (lat, long) of upper right corner
    """
    # return as [(UL), (LL), (UR), (LR)]
    return [ \
        getCoordsOfSplitBin(maxLatBin, minLongBin, UL, res), \
        getCoordsOfSplitBin(minLatBin, minLongBin, LL, res), \
        getCoordsOfSplitBin(maxLatBin, maxLongBin, UR, res), \
        getCoordsOfSplitBin(minLatBin, maxLongBin, LR, res), \
        ]

def createGeoData(binDict, res):
    """Given a dictionary whose keys are bin numbers, determine various
    elements of the image.

    ``binDict`` is a dictionary whose keys are block numbers. Given all of those
    block numbers, determine the max latitude bin, min longitude bin (i.e.
    the upper left corner), the size of the image in pixels, and the full
    bounding box (in degrees) of the image.

    Args:
        binDict (dict): Described above.
        res (int): Resolution of image block

            * 0 - high
            * 1 - medium
            * 2 - low (never used)

    Returns:
        :tuple Tuple of the form:

        1. (int) Latitude part of block number of maximum latitude.
        2. (int) Longitude part of block number of minimum longitude.
        3. Tuple of:
        
            1. (int) Image height in pixels.
            2. (int) Image width in pixels.

        4. Tuple of bounding box (see :func:`getBoundingBox` for format).
    """
    # Determine the min and max lat and long bins
    minLatBin = 5000
    minLongBin = 5000
    maxLatBin = -1
    maxLongBin = -1

    # for each binNum, determine the max and min values.
    for binNum in binDict:
        latBin, longBin = splitBinNum(binNum)

        minLatBin = min(latBin, minLatBin)
        minLongBin = min(longBin, minLongBin)
        maxLatBin = max(latBin, maxLatBin)
        maxLongBin = max(longBin, maxLongBin)

    # Each bin has 32 columns of longitude
    imageWidthPixels = ((maxLongBin - minLongBin) + 1) * 32
    
    # Each bin has 4 rows of latitude
    imageHeightPixels = ((maxLatBin - minLatBin) + 1) * 4

    # Get the bounding box
    bb = getBoundingBox(maxLatBin, minLatBin, maxLongBin, minLongBin, res)

    return (maxLatBin, minLongBin, \
        (imageHeightPixels, imageWidthPixels), bb)
    
def npCoordsFromBin(binNum, maxLatBin, minLongBin):
    """Helper function for mapImg. Returns index for the top left corner of the bin.

    Given an alternate block number, Return the top left corner for mapping
    a bin's contents into the resultant numpy (np) image.

    Args:
        binNum (int): Full alternate block number.
        maxLatBin (int): Partial alternate block number with maximum latitude bin.
        minLongBin (int): Partial alternate block number with minimum longitude bin.

    Returns:
        :tuple Tuple of ((int) x, (int) y) for mapping bin contents into numpy image.
    """
    # Returns index for the top left corner of the bin
    latBin, longBin = splitBinNum(binNum)

    x = (longBin - minLongBin) * 32
    y = (maxLatBin - latBin) * 4

    return (x, y)

def mapBinStr(x, y, binStr, rCh, gCh, bCh, aCh, mapTable, byteFcn):
    """Map bin contents into image.

    Args:
        x (int): x coordinate for image (leftmost).
        y (int): y coordinate for image (topmost).
        binStr (unicode): Contents of bin with image data.
        rCh (np array): red channel array.
        gCh (np array): green channel array.
        bCh (np array): blue channel array.
        aCh (np array): alpha channel array.
        mapTable (dict): image map table to match bin contents with color/alpha.
        byteFcn (function): byte function to use for mapping.
    """
    binStrIdx = 0
    for yy in range(y, y + 4):
        for xx in range(x, x+32):
                c = byteFcn(binStr[binStrIdx])
                rgb, a, _, _ = mapTable[c]
                rCh[yy, xx] = (rgb >> 16) & 0xFF
                gCh[yy, xx] = (rgb >> 8) & 0xFF
                bCh[yy, xx] = rgb & 0xFF
                aCh[yy, xx] = a

                binStrIdx += 1

def mapImg(filename, binDict, resolution, mapFcn):
    """Given a set of bin numbers and values, create image.

    Create a PNG file into the specified ``filename`` given a dictionary
    with bin numbers as keys and a byte string with bin values.

    If ``cfg.SMOOTH_IMAGES`` is True, will also smooth the image. In this case
    it will write the file by adding the extension ``.org``, smoothing the image,
    then rename the file to the original filename.

    Args:
        filename (str): Complete filename and path to use. Usually ends in ``.png``.
        binDict (dict): Dictionary with alternate block numbers as keys and image contents as values.
        resolution(int): Resolution of image block:

            * 0 - high
            * 1 - medium
            * 2 - low (never used)
        mapFcn (function): Function that will produce an image map to use and byte function
            for the specific image type.

    Returns:
        list: Bounding box for leaflet. Consists of the NW and SE corners, with
        the latitude first.
    """

    maxLatBin, minLongBin, \
    imageSize, bb = createGeoData(binDict, resolution)
    
    mapTable, byteFcn = mapFcn(filename)
    
    # 'Not included' values.
    # This value is the default for the image. Any places that do not get
    # an image will have this value. You can think of it as an additional 'NO DATA'
    # value.
    rCh = np.full((imageSize), NOT_INCLUDED_RED, dtype=np.uint8)
    gCh = np.full((imageSize), NOT_INCLUDED_GREEN, dtype=np.uint8)
    bCh = np.full((imageSize), NOT_INCLUDED_BLUE, dtype=np.uint8)
    aCh = np.full((imageSize), mapTable[255][1], dtype=np.uint8)    

    # Fill pixel data
    for binNum in binDict:
        x, y = npCoordsFromBin(binNum, maxLatBin, minLongBin)
        bins, _ = binDict[binNum]
        mapBinStr(x, y, bins, rCh, gCh, bCh, aCh, mapTable, byteFcn)

    xMax = bb[UR][1]
    xMin = bb[UL][1]
    yMax = bb[UR][0]
    yMin = bb[LL][0]
    
    # Complute leaflet bounding box. Note: This is in
    # NW corner, SE corner format, with lat as the [0]
    # component. Only needed if using leaflet PNG.
    bbox = [ [float(round(yMax, 6)), float(round(xMin, 6))], \
            [float(round(yMin, 6)), float(round(xMax, 6))] ]
    
    # Calculate the resolution for PNG
    xRes = (xMax - xMin) / float(imageSize[1])
    yRes = (yMax - yMin) / float(imageSize[0])

    # Transformation for PNG
    xform = (xMin, xRes, 0, yMax, 0, -yRes)
    
    # Create the PNG
    ds = gdal.GetDriverByName('MEM').Create('', imageSize[1], imageSize[0], \
        4, gdal.GDT_Byte)

    ds.SetGeoTransform(xform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(rCh)
    ds.GetRasterBand(2).WriteArray(gCh)
    ds.GetRasterBand(3).WriteArray(bCh)
    ds.GetRasterBand(4).WriteArray(aCh)
    ds.FlushCache()

    pngDriver = gdal.GetDriverByName("PNG")
    png_ds = pngDriver.CreateCopy(filename, ds, 0)
    ds = None
    png_ds = None
    
    # Return bounding box.
    return bbox
    
def getLegendDict():
    """Create a dictionary showing the units and colors (with text values)
    for each image map. Used in clients to create a legend for an image.

    The keys for this dictionary are the name of the
    image map. The value is also a dictionary who's ``units`` key is the name
    of the units being used. The other entry to this dictionary is ``colors``.
    ``colors`` is a list of two element lists. The first entry is the integer ``RGB``
    color value, and the second entry is the text that goes with the color.

    Items that are not displayed for a particular map are not placed in the list
    of colors.

    The color list will always have the colors in order of intensity. This includes
    the icing severity table where 'heavy' and 'severe' are placed in the wrong
    order by the standard.

    This data will be placed in the LEGEND collection as its only entry.
    A truncated sample will look like: ::

      {"_id" : "LEGEND",
       "RADAR" : {
        "units" : "dBZ",
        "colors" : [[60977,"20-30"],[762654,"30-40"],[16776762,"40-45"],
                   [16750398,"45-50"],[16711697,"50-55"],[16711931,">55"],
                   [15522454,"Not Incl"]]
        },
       "TURBULENCE" : {
        "units" : "EDR*100",
        "colors" : [[13434481,"14-21"],[15588917,"21-28"],[16757806,"28-35"],
                   [16749864,"35-42"],[16741923,"42-49"],[16731165,"49-56"],
                   [16711704,"56-63"],[14876693,"63-70"],[12124177,"70-77"],
                   [9371661,"77-84"],[8060940,"84-91"],[5439496,"91-98"],
                   [4259846,">98"],[15522454,"No Data"]]
        }
      }

    Returns:
        dict: Dictionary as described above.
    """
    legendDict = {}

    # Make an entry in the dictionary for every image map.
    for j, x in enumerate(imap.IMAGE_MAPS):
        noDataValue = -1
        newMap = True
        colorValuesList = []
        mapName = imap.IMAGE_MAP_NAMES[j]

        # Sigh... special treatment for outlier ICING_SEV
        isIcingSevMap = False
        if mapName == 'ICING_SEV':
            isIcingSevMap = True    

        # Create entry for each map
        # Entries are sorted in order of severity
        for i in sorted(x.keys()):
            items = x[i]
            if newMap:
                legendDict[mapName] = {'units': items[3]}
                newMap = False

            # Skip invisible items
            if items[1] == 0:
                continue

            # If we have a 'no data' value and a 'not included' value, and they are
            # both the same, we need to skip the 'not included' value. So we save
            # the 'no data' value (which will occur first, and is stored in
            # NO_DATA_STR (usually 'No Data')), then check against the not
            # included value (always 255) if it occurs later.
            if items[2] == imap.NO_DATA_STR:
                noDataValue = items[0] 
            elif (i == 255) and (noDataValue == items[0]):
                continue

            # So all the color maps in the standard have all of their entries
            # in order EXCEPT for icing severity, where 'severe' comes before 'heavy'.
            # We will flip these values. We store the severe values and insert
            # them after we put the heavy values in.
            if isIcingSevMap:
                if i == 4:
                    icingSevereColor = items[0]
                    icingSevereValue = items[2]
                elif i == 5:
                    colorValuesList.append([items[0], items[2]])
                    colorValuesList.append([icingSevereColor, \
                        icingSevereValue])                                        
                else:
                    colorValuesList.append([items[0], items[2]])
            else:
                colorValuesList.append([items[0], items[2]])

        legendDict[mapName]['colors'] = colorValuesList

    return legendDict
