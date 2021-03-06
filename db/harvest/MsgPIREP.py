from db.harvest.MsgBase import MsgBase
import db.harvest.location as loc
import db.harvest.harvestConfig as cfg

class MsgPIREP(MsgBase):
    """Methods for handling PIREP messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['PIREP'])
        
    def processMessage(self, msg, digest):
        """Store PIREP message.

        If ``cfg.PIREP_LOCATION_SUPPORT`` is ``True`` will attempt to add
        geometry coordinates to this message.

        Args:
            msg (dict): Level 2 ``PIREP`` message to store. All messages get stored
              to the ``PIREP`` collection.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return        

        # Augment with location if desired.
        if cfg.PIREP_LOCATION_SUPPORT:
            msg = loc.pirepLocation(self.dbConnLocation, msg)

        self.dbConn.MSG.replace_one( \
            { '_id': msg['_id']}, \
            msg, \
            upsert=True)
