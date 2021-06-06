from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg

class MsgG_AIRMET(MsgBase):
    """Methods for handling G_AIRMET  messages.

    This handles the level 2 FIS-B message types of:
    ``G_AIRMET_00_HR``, ``G_AIRMET_03_HR``, and ``G_AIRMET_06_HR``.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['G_AIRMET_00_HR', 'G_AIRMET_03_HR', 'G_AIRMET_06_HR'], \
                         'G_AIRMET')
        
    def processMessage(self, msg, digest):
        """Store G-AIRMET message to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, will also
        update the collection ``CRL_14`` with completed reports.

        Args:
            msg (dict): Level 2 ``G_AIRMET_00_HR``, ``G_AIRMET_03_HR``,
              and ``G_AIRMET_06_HR`` message to store. All messages get stored
              to the ``G_AIRMET`` collection.
        """
        pkey = msg['unique_name']

        if self.processChanges('G_AIRMET', pkey, digest):
            return

        # Convert to geojson
        msg = self.geometryToGeojson(msg)

        del msg['unique_name']
        self.dbCollection().update( \
            { '_id': pkey}, \
            msg, \
            upsert=True)

        if cfg.IMMEDIATE_CRL_UPDATE:
            self.updateCRL('CRL_14', pkey, msg['station'], False)
