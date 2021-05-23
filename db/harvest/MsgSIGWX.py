from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg
import db.harvest.harvestExceptions as ex

class MsgSIGWX(MsgBase):
    """Methods for handling ``AIRMET``, ``SIGMET``, ``WST``, and
    ``CWA`` messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['AIRMET', 'SIGMET', 'WST', 'CWA'], \
                         'SIGWX')
        
    def processMessage(self, msg):
        """Store ``AIRMET``, ``SIGMET``, ``WST``, and ``CWA``
        messages to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, will also
        update the appropriate CRL collection with completed reports.

        Args:
            msg (dict): Level 2 ``SIGMET``, ``AIRMET``, ``WST``,
              or ``CWA`` message to store. All messages get stored
              to the ``SIGWX`` collection.
        """        
        pkey = msg['unique_name']

        # Convert to geojson
        msg = self.geometryToGeojson(msg)

        del msg['unique_name']
        
        self.dbCollection().update( \
            { '_id': pkey}, \
            msg, \
            upsert=True)

        if cfg.IMMEDIATE_CRL_UPDATE:
            msgType = msg['type']

            if msgType in ['SIGMET', 'WST']:
                crlTable = 'CRL_12'
            elif msgType == 'AIRMET':
                crlTable = 'CRL_11'
            elif msgType == 'CWA':
                crlTable = 'CRL_15'
            else: 
                raise ex.UnknownCrlException('No SIGWX CRL type for "{}"'.format(msgType))

            hasTextAndGraphics = False
            if ('contents' in msg) and ('geojson' in msg):
                hasTextAndGraphics = True

            self.updateCRL(crlTable, pkey, msg['station'], hasTextAndGraphics)

