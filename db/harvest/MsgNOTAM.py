from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg

class MsgNOTAM(MsgBase):
    """Methods for handling NOTAM (-D -FDC)  messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['NOTAM'])
        
    def processMessage(self, msg, digest):
        """Store NOTAM message to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, and this
        is a ``TRA`` or ``TMOA`` NOTAM, will also
        update the collection ``CRL_16`` or ``CRL_17`` with completed reports.

        Args:
            msg (dict): Level 2 ``NOTAM``
              message to store. All messages get stored
              to the ``NOTAM`` collection.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return

        # Convert to geojson
        msg = self.geometryToGeojson(msg)

        self.dbConn.MSG.replace_one( \
            { '_id': msg['_id']}, \
            msg, \
            upsert=True)

        msgSubtype = msg['subtype']
        if cfg.IMMEDIATE_CRL_UPDATE and \
            ((msgSubtype == 'TMOA') or (msgSubtype == 'TRA')):

            hasTextAndGraphics = False
            if ('contents' in msg) and ('geojson' in msg):
                hasTextAndGraphics = True

            if msgSubtype == 'TMOA':
                self.updateCRL('CRL_17', msg['unique_name'], msg['station'], hasTextAndGraphics)
            else:
                self.updateCRL('CRL_16', msg['unique_name'], msg['station'], hasTextAndGraphics)
