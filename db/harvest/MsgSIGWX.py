from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg
import db.harvest.harvestExceptions as ex

class MsgSIGWX(MsgBase):
    """Methods for handling ``AIRMET``, ``SIGMET``, and
    ``CWA`` messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['AIRMET', 'SIGMET', 'CWA'])
        
    def processMessage(self, msg, digest):
        """Store ``AIRMET``, ``SIGMET``, and ``CWA``
        messages to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, will also
        update the appropriate CRL collection with completed reports.

        Args:
            msg (dict): Level 2 ``SIGMET``, ``AIRMET``,
              or ``CWA`` message to store. All messages get stored
              to the ``MSG`` collection.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return      

        # Convert to geojson
        msg = self.geometryToGeojson(msg)

        self.dbConn.MSG.replace_one( \
            {'_id': msg['_id']}, \
            msg, \
            upsert=True)

        if cfg.IMMEDIATE_CRL_UPDATE:
            msgType = msg['type']

            if msgType == 'SIGMET':
                crlTable = 'CRL_12'
            elif msgType == 'AIRMET':
                crlTable = 'CRL_11'
            elif msgType == 'CWA':
                crlTable = 'CRL_15'
            else: 
                raise ex.UnknownCrlException('No CRL type for "{}"'.format(msgType))

            hasTextAndGraphics = False
            if ('contents' in msg) and ('geojson' in msg):
                hasTextAndGraphics = True

            self.updateCRL(crlTable, msg['unique_name'], msg['station'], hasTextAndGraphics)

