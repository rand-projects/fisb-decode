from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg

class MsgNOTAM_TFR(MsgBase):
    """Methods for handling NOTAM_TFR messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['NOTAM_TFR'], 'NOTAM_TFR')
        
    def processMessage(self, msg):
        """Store NOTAM_TFR message to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, this
        will also
        update the collection ``CRL_8`` with completed reports.

        Args:
            msg (dict): Level 2 ``NOTAM_TFR``
              message to store. All messages get stored
              to the ``NOTAM_TFR`` collection.
        """        
        pkey = msg['unique_name']

        # Convert to geojson
        msg = self.geometryToGeojson(msg)

        del msg['unique_name']
        del msg['type']

        self.dbCollection().update( \
            { '_id': pkey}, \
            msg, \
            upsert=True)

        if cfg.IMMEDIATE_CRL_UPDATE:
            hasTextAndGraphics = False
            if ('contents' in msg) and ('geojson' in msg):
                hasTextAndGraphics = True

            self.updateCRL('CRL_8', pkey, msg['station'], hasTextAndGraphics)
