from datetime import datetime, timezone, timedelta
from osgeo import gdal
import numpy, os, pprint

from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg
import db.harvest.images as img
import db.harvest.testing as test
import db.harvest.harvestExceptions as ex
import fisb.level2.utilities as util

IMAGE_LIST =['NEXRAD_REGIONAL', 'NEXRAD_CONUS', \
               'CLOUD_TOPS', 'LIGHTNING', \
               'ICING_02000', 'ICING_04000', 'ICING_06000', 'ICING_08000', \
               'ICING_10000', 'ICING_12000', 'ICING_14000', 'ICING_16000', \
               'ICING_18000', 'ICING_20000', 'ICING_22000', 'ICING_24000', \
               'TURBULENCE_02000', 'TURBULENCE_04000', 'TURBULENCE_06000', \
               'TURBULENCE_08000', 'TURBULENCE_10000', 'TURBULENCE_12000', \
               'TURBULENCE_14000', 'TURBULENCE_16000', 'TURBULENCE_18000', \
               'TURBULENCE_20000', 'TURBULENCE_22000', 'TURBULENCE_24000']

class MsgBLOCK(MsgBase):
    """Methods for handling all block (image) messages.
    """
    def __init__(self):
        """Initialize MsgBLOCK Object.

        Creation of this object at the start of a Harvest run does
        the following things:

        * Remove all images (all the .tif files residing in the
          image storage area).
        * Creates the ``imageDict``. The ``imageDict`` is a dictionary where
          the key is the name of the image as defined in ``IMAGE_LIST``.
          The value is another dictionary containing information about the
          image. See the comments in the :func:`createNoDataDict` function
          about the values stored there.
          Part of the ``imageDict`` is storage for any image data we receive.

        Images are essentially self contained and managed. The life cycle is
        as follows:

        * When Harvest is started, all ``.tif`` images are removed. Each image
          type will get its own (empty) entry in ``imageDict``.
        * Fisb-decode level2 messages with data get sent to
          :func:`processMessage`.
          The image data will get stored. Updates to ``imageDict`` will be made.
        * The function :func:`periodicUpdate` will be called periodically and
          will see if any data has arrived after the image was created. If it
          was (after possibly a ``quiet time`` where no data has arrived for
          some period of seconds) a new message will be generated. It will also
          remove the image and its ``imageDict`` entry (making a new empty one)
          if the image has reached its expiration time. Also, for lightning
          and radar images which allow latency (where two or more images can
          be combined), the system will enforce the standard where the
          difference between the newest data and the oldest data
          cannot be more than 10 minutes. For other messages, image data with a
          later timestamp than the current data will force the old data to be
          removed and replaced with new data.
        """

        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['IMAGE'])

        self.imageDict = {}

    def initiateImages(self):
        # Create initial 'no data states' for all images.
        for x in IMAGE_LIST:
            self.imageDict[x] = self.createNoDataDict(x)

            # Delete any existing file so we start fresh.
            self.deleteImageFile(x)

    def createImageReport(self, dt):
        """Called by the testing system to generate an image report.

        Images are just ``.tif`` files and contain no obvious metadata.
        For testing, whenever a periodic dump is done, the images are 
        transferred to a dump area and this report is generated which
        contains information about each image.

        The current date/time is used to generate information about
        how old the image is.

        Args:
            dt (datetime): Datetime object reflecting the ``current time``. 

        Returns:
            tuple: Tuple containing:

            * ``True`` if there are any existing images, ``False`` if not.
            * String containing the contents of the report.
        """
        hasImages = False

        report = 'Current Image Report at {}\n\n'.format(dt.strftime('%Y/%m/%d %H:%M:%S'))

        # Cereate report information for every existing report.
        for x in IMAGE_LIST:
            d = self.imageDict[x]

            if not d['has_any_data']:
                continue

            hasImages = True
            obsType = d['obs_or_valid']

            dtNewestOfficial = datetime.utcfromtimestamp(d['newest_official_ts'])
            dtOldestOfficial = datetime.utcfromtimestamp(d['oldest_official_ts'])
            dtLastChanged = datetime.utcfromtimestamp(d['last_changed_ts'])

            report = report + x + '\n'

            if x in ['NEXRAD_REGIONAL', 'NEXRAD_CONUS', 'LIGHTNING']:
                # Oldest data is reported as the observation time.
                report = report + '  {}: {}\n'.format(obsType, \
                    dtOldestOfficial.strftime('%Y/%m/%d %H:%M:%S'))
                report = report + '  newest_data: {}\n'.format( \
                    dtNewestOfficial.strftime('%Y/%m/%d %H:%M:%S'))
                report = report + '  image_age (mm:ss): {}\n'.format( \
                    util.secondsToMMSS(dt.timestamp() - d['oldest_official_ts']))
            else:
                report = report + '  {}: {}\n'.format(obsType, \
                    dtNewestOfficial.strftime('%Y/%m/%d %H:%M:%S'))
                report = report + '  image_age (mm:ss): {}\n'.format( \
                    util.secondsToMMSS(dt.timestamp() - d['newest_official_ts']))

            report = report + '  last_changed: {}\n'.format( \
                dtLastChanged.strftime('%Y/%m/%d %H:%M:%S'))

        report = report + '\n\n'

        return (hasImages, report)

    def createFileNameList(self, imgType):
        """Create a list of file names for the specified image type.

        Generates full file paths for the specified ``imgType``. Base
        directory information comes from ``cfg.IMAGE_DIRECTORY``. 
        Most images only have one name, but icing and lightning
        images generate more than one image.

        Args:
            imgType (str): Image type as found in ``IMAGE_LIST``.

        Returns:
            list: List of path names where images of this type will be stored.
        """
        nameList = []
        if imgType.startswith('ICING'):
            nameList.append(imgType + '_SLD.tif')    
            nameList.append(imgType + '_SEV.tif')    
            nameList.append(imgType + '_PRB.tif')
        elif imgType.startswith('LIGHT'):
            nameList.append(imgType + '_ALL.tif')    
            nameList.append(imgType + '_POS.tif')    
        else:
            nameList.append(imgType + '.tif')

        # Add full paths
        for i in range(0, len(nameList)):
            nameList[i] = os.path.join(cfg.IMAGE_DIRECTORY, nameList[i])

        return nameList

    def deleteImageFile(self, imgType):
        """Delete all ``.tif`` files associated with the image type.

        Args:
            imgType (str): Image type as found in ``IMAGE_LIST``
        """
        nameList = self.imageDict[imgType]['filename_list']

        for x in nameList:
            if os.path.isfile(x):
                os.remove(x)

        self.dbConn.MSG.delete_one({'_id': 'IMAGE-' + imgType})

    def getMapFcn(self, imgType):
        """Return function that is used to choose correct image map and byte function.

        Given an image type as found in ``IMAGE_LIST`` return a function used 
        during image creation to use the correct color map and interpret
        pixels correctly for lightning and icing images.

        Args:
            imgType (str): Image type as found in ``IMAGE_LIST``

        Returns:
            function: Correct function for image type.

        Raises:
            UndefinedImageFunctionException: If undefined image type given.
        """
        if imgType.startswith('TURB'):
            fcn = img.mapFcnTurb
        elif imgType.startswith('ICING'):
            fcn = img.mapFcnIcing
        elif imgType.startswith('NEXRAD'):
            fcn = img.mapFcnRadar
        elif imgType.startswith('CLOUD'):
            fcn = img.mapFcnCloudTops
        elif imgType.startswith('LIGHT'):
            fcn = img.mapFcnLightning
        else:
            raise ex.UndefinedImageFunctionException( \
                'No such image type as "{}"'.format(imgType))

        return fcn
        
    def createImageFile(self, imgType, quietImageTime):
        """Create a new ``.tif`` image file(s) for the given type if needed.

        This function will create a new image only if needed. So it called each
        time through :func:`periodicUpdate`. If there is no image data, or the data
        hasn't changed from the last update, or the data hasn't been quiet
        long enough, this function will simply return.

        Args:
            imgType (str): Image type as found in ``IMAGE_LIST``
            quietImageTime (int): Create image only if it has been this many seconds
                since we received new data. This prevents making many images during
                an active upload.
        """
        imgDict = self.imageDict[imgType]

        # Nothing to do if no data
        if not imgDict['has_any_data']:
            return
            
        lastChangedTs = imgDict['last_changed_ts']

        # If a quiet time (a number of seconds where no new data
        # has been written to this image) is desired, perform check.
        if quietImageTime > 0:
            # Get current UTC time
            tsNow = test.datetimeNow().timestamp()

            if (tsNow  - lastChangedTs) < quietImageTime:
                return

        # See if new data added after last image created
        if imgDict['file_creation_ts'] > lastChangedTs:
            return

        # if we get here, time to make an image
        imageList = imgDict['filename_list']

        # Make one or more (for lightning and icing) .tif files.
        for filename in imageList:
            bbox = img.mapImg(filename, imgDict['bins_dict'], \
                   imgDict['scale_factor'], imgDict['image_map_fcn'])

        # Get the insert/creation timestamp
        insertTime = test.datetimeNow()
        oldestTime = datetime.utcfromtimestamp(imgDict['oldest_official_ts'])
        expirationTime = oldestTime + timedelta(0, imgDict['revert_to_no_data_time'])

        msgId = 'IMAGE-' + imgType

        msg = {'_id': msgId, 'type': 'IMAGE', 'unique_name': imgType, \
            imgDict['obs_or_valid']: oldestTime, \
            'bbox': bbox, 'insert_time': insertTime, 'expiration_time': expirationTime}

        self.dbConn.MSG.replace_one({'_id': msgId}, \
            msg, \
            upsert = True)
            
        # Set the creation time.
        imgDict['file_creation_ts'] = insertTime.timestamp()

    def createNoDataDict(self, imgType):
        """Create a 'no data' ``imageDict`` dictionary.

        This creates an empty entry for the ``imageDict`` for a particular 
        type of image. It contains placeholders for new data as well as 
        default values for a particular image type. The result of this
        function will be used as an entry in ``imageDict``.

        Args:
            imgType (str): Image type as found in ``IMAGE_LIST``

        Returns:
            dict: Contains empty placeholder for image data and metadata.
        """
        imgDict = {}

        # True if this image has any data.
        imgDict['has_any_data'] = False

        # Timestamp last created file was made
        imgDict['file_creation_ts'] = -1

        # Contains list of all filenames (usually just 1, but 
        # lightning and icing have more than one image per type).
        imgDict['filename_list'] = self.createFileNameList(imgType)

        # Timestamp when last changed. This is in actual time.
        imgDict['last_changed_ts'] = -1

        # Holds timestamps of the newest data in current image
        # This is the timestamp based on valid/observed time
        imgDict['newest_official_ts'] = -1

        # Holds timestamps of the oldest data in current image
        # This is the timestamp based on valid/observed time.
        # It is really only used for RADAR messages which all have
        # a latency. For other messages, it is not used. It is
        # updated periodically during latency checking.
        imgDict['oldest_official_ts'] = -1

        # Image type dependent constants
        # 1) Seconds this message needs to revert to no data condition.
        #    This is a mandated time of 75 or 105 minutes. We store these
        #    times as seconds.
        # 2) Seconds of maximum latency. This is the maximun allowed time
        #    from the newest observed time to the oldest observed time that
        #    is allowed to exist in a single message.
        # 3) Time of message is either 'valid_time' or 'observation_time'. Store
        #    the correct key name.
        if imgType in ['NEXRAD_REGIONAL', 'NEXRAD_CONUS', 'LIGHTNING']:
            imgDict['revert_to_no_data_time'] = 60 * 75  # 75 minutes
            imgDict['max_latency_time'] = 60 * 10        # 10 minutes
            imgDict['obs_or_valid'] = 'observation_time'            
        else:
            imgDict['revert_to_no_data_time'] = 60 * 105 # 105 minutes
            imgDict['max_latency_time'] = 0              # None
            imgDict['obs_or_valid'] = 'valid_time'

        # Set the scale factor
        if imgType in ['NEXRAD_REGIONAL', 'LIGHTNING', 'CLOUD_TOPS']:
            imgDict['scale_factor'] = 0
        else:
            imgDict['scale_factor'] = 1
        
        # Set the image mapping function
        imgDict['image_map_fcn'] = self.getMapFcn(imgType)

        # Small dictionary for each bin
        # Each item is a tuple: [0] is the bin string and [1] is the timestamp
        # of the valid time. Key is the alternate block number.
        imgDict['bins_dict'] = {}
        
        return imgDict
        
    def processMessage(self, msg, _):
        """Called by Harvest to process a message containing image data.

        Places image data in the appropriate ``imageDict`` entry and
        updates its metadata. Ignores any duplicate data.

        Args:
            msg (dict): Fisb level2 image message.
        """
        # If not processing images, ignore all this.
        if not cfg.PROCESS_IMAGES:
            return

        # Get current image dictionary for this type
        imgDict = self.imageDict[msg['unique_name']]

        # Also get the dictionary of bins in the image
        imgBinsDict = imgDict['bins_dict']

        # For the current message, get the official valid/observation
        # time, bins, and binNumber
        curMsgBinNumber = msg['alt_bn']
        curMsgOfficialTime = msg[imgDict['obs_or_valid']].timestamp()
        curMsgBins = msg['bins']

        if curMsgBinNumber in imgBinsDict:
            imgBinStr, imgOfficialTime = imgBinsDict[curMsgBinNumber]

            # See if this is a duplicate. Data that doesn't change has
            # no effect.
            if (curMsgOfficialTime == imgOfficialTime) and \
                (curMsgBins == imgBinStr):

                # Duplicate, nothing to do.
                return

        # See if this is a valid time later than we have seen
        if curMsgOfficialTime > imgDict['newest_official_ts']:

            # We are starting a new image.
            imgDict['newest_official_ts'] = curMsgOfficialTime

            # Radar and Lightning images allow latency. Others do not.
            # If the latency is 0 for this type, wipe out all bins.
            if imgDict['max_latency_time'] == 0:
                imgDict['bins_dict'] = {}

                # Re-get the bins dictionary. Otherwise creates a hard to find bug.
                imgBinsDict = imgDict['bins_dict']        

        # We have new data, so update the receive time
        imgDict['last_changed_ts'] = test.datetimeNow().timestamp()

        # Add the new data
        imgBinsDict[curMsgBinNumber] = (curMsgBins, curMsgOfficialTime)

        imgDict['has_any_data'] = True

    def periodicUpdate(self):
        """Performs periodic maintenance issues such as creating ``.tif``
        images or removing images.

        Performs the following tasks:

        * Delete any images past their 'revert to no data' time.
        * Process latency for those images that require it.
        * Generate new images if needed.
        """
        # Ignore if not processing images.
        if not cfg.PROCESS_IMAGES:
            return

        # Look at each image type and decide what to do.
        for x in IMAGE_LIST:
            # Get current image dictionary for this type
            imgDict = self.imageDict[x]

            # If no data, there is nothing to see here
            if not imgDict['has_any_data']:
                continue

            # Setup to process latency and 'no data' time.
            latencyTime = imgDict['max_latency_time']
            noDataTime = imgDict['revert_to_no_data_time']
            tsNow = test.datetimeNow().timestamp()
            binsDict = imgDict['bins_dict']

            newestTs = imgDict['newest_official_ts']

            # After looping through the data, this will hold the
            # oldest still active data for messages that care about
            # letency. Assume the newest data for now.
            oldestActiveLatentData = newestTs

            # Set this to True if we delete any bins.
            anyChanges = False
            
            # Process latency and 'no data' time
            keys = list(binsDict.keys())
            for z in keys:
                # Set to True if we have a bin to delete.
                binToDelete = False

                # Get timestamp of the current bin.
                _, ts = binsDict[z]

                # Latency
                tsDiff = newestTs - ts
                if latencyTime > 0:
                    # Letency exceeded, delete.
                    if tsDiff >= latencyTime:
                        binToDelete = True
                    else:
                        # See if this is the oldest data we know about.
                        oldestActiveLatentData = min(oldestActiveLatentData, ts)

                # See if data is so old we need to expire it.
                if (tsNow - ts) >= noDataTime:
                    binToDelete = True

                if binToDelete:
                    del binsDict[z]
                    anyChanges = True

            imgDict['oldest_official_ts'] = oldestActiveLatentData

            if anyChanges:
                imgDict['last_changed_ts'] = tsNow

            # Case where there are no more bins left
            if len(list(imgDict['bins_dict'].keys())) == 0:

                # Expired message
                self.deleteImageFile(x)
                self.imageDict[x] = self.createNoDataDict(x)
                continue

            # Lastly, create any files. This won't create a new file
            # unless there is some specific reason to (such as a change).
            self.createImageFile(x, cfg.IMAGE_QUIET_SECONDS)
