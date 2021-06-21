import sys, os
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import db.harvest.testing as test
import db.harvest.harvestExceptions as ex
import db.harvest.vectors as vec

class MsgBase(ABC):
    """Base message handler for all messages.

    Most messages are stored in a mongoDB collection. The fisb-decode
    level 2 message type to collection map is:

    - All block messages => :mod:`db.harvest.MsgBLOCK` (not stored in database, images are stored as files)
    - ``CRL`` => :mod:`db.harvest.MsgCRL`

      - ``CRL_8``
      - ``CRL_11``
      - ``CRL_12``
      - ``CRL_14``
      - ``CRL_15``
      - ``CRL_16``
      - ``CRL_17``
    - ``FIS_B_UNAVAILABLE`` => :mod:`db.harvest.MsgFIS_B_UNAVAILABLE`
    
      - ``FIS_B_UNAVILABLE``
    - ``G_AIRMET_xx_HR`` => :mod:`db.harvest.MsgG_AIRMET`
    
      - ``G_AIRMET``
    - ``METAR`` => :mod:`db.harvest.MsgMETAR`

      - ``METAR``
    - ``NOTAM`` => :mod:`db.harvest.MsgNOTAM`

      - ``NOTAM``
    - ``PIREP`` => :mod:`db.harvest.MsgPIREP`

      - ``PIREP``
    - ``SERVICE_STATUS`` => :mod:`db.harvest.MsgSERVICE_STATUS`

      - ``SERVICE_STATUS``
    - ``AIRMET``, ``SIGMET``, ``WST``, ``CWA`` => :mod:`db.harvest.MsgSIGWX`

      - ``SIGWX``
    - ``SUA`` => :mod:`db.harvest.MsgSUA`

      - ``SUA``
    - ``TAF`` => :mod:`db.harvest.MsgTAF`

      - ``TAF``
    - ``WINDS_06_HR`` => :mod:`db.harvest.MsgWINDS_06_HR`

      - ``WINDS_06_HR``
    - ``WINDS_12_HR`` => :mod:`db.harvest.MsgWINDS_12_HR`

      - ``WINDS_12_HR``
    - ``WINDS_24_HR`` => :mod:`db.harvest.MsgWINDS_24_HR`

      - ``WINDS_24_HR``
    """
    def __init__(self, typesList):
        """Initialize class

        Args:
            typesList (list): List of all message types (from fisb level2 message ``type`` slots)
                that this class will handle.
        """
        self.dbConn = None
        self.dbConnLocation = None
        self.typesList = typesList

    def checkThenAddIdDigest(self, msg, digest):
        """
        """
        # See if message already exists
        # If so, and the digests are equal, return False
        pkey = msg['type'] + '-' + msg['unique_name']
        oldMsg = self.dbConn.MSG.find_one({'_id': pkey})

        if (oldMsg != None) and ('digest' in oldMsg):
          if digest == oldMsg['digest']:
            # Duplicate
            return False

        # We have a changed or original message
        msg['_id'] = pkey
        msg['digest'] = digest
        msg['insert_time'] = test.datetimeNow()
        return True
        
    def getDbConn(self):
        """Get the MongoDB database handle.

        Returns:
            object: MongoDB database handle.
        """
        return self.dbConn

    def setDbConn(self, dbConn, dbConnLocation):
        """Set the MondoDB database handle.

        Args:
            dbConn (object): MongoDB database handle (``fisb``).
            dbConnLocation (object): MongoDB Location DB handle (``fisb_location``).
              If you are not using the location DB, this can be ``None``.
        """
        self.dbConn = dbConn
        self.dbConnLocation = dbConnLocation

    def getTypesList(self):
        """Return list of all fisb level2 message ``types`` handled by this class.

        Returns:
            list: List of all types handled by this class.
        """
        return self.typesList

    def createFeatureDict(self, geoEntry, msg):
      """Convert entry in a fisb-decode ``geometry`` slot into a ``geojson`` 
      ``features`` list item. Called internally by
      :meth:`db.harvest.MsgBase.MsgBase.geometryToGeojson`.

      Args:
        geoEntry (dict): Dictionary that was a ``geometry`` list item in
           the original message.
        msg (dict): Dictionary with original message. Used for properties.

      Returns:
        dict: Geojson form of ``geoEntry``.
      """
      featureDict = {'type': 'Feature'}

      # Process the 'geometry' entry. Simple except for circles.
      oldGeoType = geoEntry['type']

      geometryDict = {}

      if oldGeoType == 'POINT':
        geometryDict['type'] = 'Point'
        geometryDict['coordinates'] = geoEntry['coordinates']
        
      elif oldGeoType == 'POLYGON':
        geometryDict['type'] = 'Polygon'
        geometryDict['coordinates'] = geoEntry['coordinates']
        
      elif oldGeoType == 'POLYLINE':
        geometryDict['type'] = 'LineString'
        geometryDict['coordinates'] = geoEntry['coordinates']

      elif oldGeoType == 'CIRCLE':
        geometryDict['type'] = 'Polygon'
        geometryDict['coordinates'] = vec.circleToPolygon( \
          geoEntry['coordinates'][0], \
          geoEntry['coordinates'][1], \
          geoEntry['radius_nm'])
      else:
        raise ex.UnknownGeometryType('Unknown geometry of "{}"'.format(oldGeoType))
      
      # Add geometry key
      featureDict['geometry'] = geometryDict
      
      # Move other entries into 'properties' (propertiesDict)
      propertiesDict = {}

      keys = list(geoEntry.keys())

      for k in keys:
        if k in ['type', 'coordinates', 'radius_nm']:
          continue
        propertiesDict[k] = geoEntry[k]

      # All items get an `id` property from original message
      propertiesDict['id'] = msg['unique_name']

      # Add properties key (will be included even if empty)
      featureDict['properties'] = propertiesDict
      
      return featureDict

    def geometryToGeojson(self, msg):
      """Convert any 'geometry' slot in a message to a 'geojson' slot.

      Converts any ``geometry`` slot into a ``geojson`` slot. The
      ``type`` and ``coordinates`` fields are transferred directly, unless
      it is a circle. Circles are converted into a ``Polygon``. 

      Slots that are part of a 'geometry' object, but that are not ``type``,
      ``coordinates``, or ``radius_nm`` are place in the ``properties``
      dictionary.

      Args:
        msg (dict): Message dictionary, possibly with 'geometry' slot.
          *This is a level 2 fis-b message* **NOT** *a mongo db entry.*

      Returns:
        dict: Message, possibly with new 'geojson' slot.
      """
      # Return if no geometry to process
      if 'geometry' not in msg:
        return msg

      # Create list of all features.
      featuresList = [self.createFeatureDict(geoEntry, msg) for geoEntry in msg['geometry']]

      msg['geojson'] = {'type': 'FeatureCollection', \
          'features': featuresList}

      # Delete existing geometry
      del msg['geometry']

      # Return altered message
      return msg

    def updateCRL(self, crlTable, id, station, hasTextAndGraphics):
        """Update CRL related to a message with the specified ID.

        If a message is received that has an associated CRL, this function
        will lookup the current CRL (if any), and add the ``seen`` flag 
        (an asterisk at the end of the ID in the ``reports`` slot) if 
        needed. This way the CRL is kept up to date.

        Args:
            crlTable (str): CRL table to update (such as ``CRL_15``, etc)
            id (str): ID of the message (usually ``year-reportnumber``)
            station (str): Station ID 
            hasTextAndGraphics (bool): ``True`` if the message calling this has both a text
                and graphic portion. CRL messages requiring text and graphics
                need both to be complete.
        """
        crl = self.dbConn.MSG.find_one({'_id': crlTable + '-' + station})
        if crl == None:
            return

        reports = crl['reports']

        for x in range(0, len(reports)):
            if reports[x].startswith(id):
                # Remove any existing completeness status.
                if reports[x][-1] == '*':
                    reports[x] = reports[x][:-1]

                # Only mark TG reports complete if both parts are there.    
                if '/TG' in reports[x]:
                    if hasTextAndGraphics:
                        reports[x] = reports[x] + '*'
                else:
                    reports[x] = reports[x] + '*'

                # Update report list
                self.dbConn.MSG.update_one({'_id': crlTable + '-' + station}, \
                  {'$set':{'reports': reports}})
                break
        
    @abstractmethod
    def processMessage(self, msg):
        """Process message

        Abstract method that is required to be implemented by subclasses.

        Args:
            msg (dict): Message to process
        """
        pass
