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
        super().__init__(['NOTAM_TFR'])
        
    def processMessage(self, msg, digest):
        """Store NOTAM_TFR message to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, this
        will also
        update the collection ``CRL_8`` with completed reports.

        Args:
            msg (dict): Level 2 ``NOTAM_TFR``
              message to store. All messages get stored
              to the ``NOTAM_TFR`` collection.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return

        # Convert to geojson
        msg = self.geometryToGeojson(msg)

        self.dbConn.MSG.replace_one( \
            { '_id': msg['_id']}, \
            msg, \
            upsert=True)

        if cfg.IMMEDIATE_CRL_UPDATE:
            hasTextAndGraphics = False
            if ('contents' in msg) and ('geojson' in msg):
                hasTextAndGraphics = True

            self.updateCRL('CRL_8', msg['unique_name'], msg['station'], hasTextAndGraphics)
