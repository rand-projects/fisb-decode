from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg

class MsgG_AIRMET(MsgBase):
    """Methods for handling G_AIRMET  messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['G_AIRMET'])
        
    def processMessage(self, msg, digest):
        """Store G-AIRMET message to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, will also
        update the collection ``CRL_14`` with completed reports.

        Args:
            msg (dict): Level 2 ``G_AIRMET``
              message to store. All messages get stored
              to the ``G_AIRMET`` collection.
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
            self.updateCRL('CRL_14', msg['unique_name'], msg['station'], False)
