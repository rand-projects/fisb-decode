from db.harvest.MsgBase import MsgBase
import db.harvest.location as loc
import db.harvest.harvestConfig as cfg

class MsgTAF(MsgBase):
    """Methods for handling TAF messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['TAF'])
        
    def processMessage(self, msg, digest):
        """Store TAF message.

        If ``cfg.TEXT_WX_LOCATION_SUPPORT`` is ``True`` will attempt to add
        geometry coordinates to this message.

        Args:
            msg (dict): Level 2 ``TAF`` message to store. All messages get stored
              to the ``TAF`` collection.
        """       
        if not self.checkThenAddIdDigest(msg, digest):
            return

        # Augment with location if desired.
        if cfg.TEXT_WX_LOCATION_SUPPORT:
            msg = loc.addTextWxLoc(self.dbConnLocation, msg)

        # Remove redundant keys
        del msg['location']

        self.dbConn.MSG.replace_one( \
            { '_id': msg['_id']}, \
            msg, \
            upsert=True)


