from db.harvest.MsgBase import MsgBase
import db.harvest.location as loc
import db.harvest.harvestConfig as cfg

class MsgWINDS_12_HR(MsgBase):
    """Methods for handling WINDS-12-HR messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['WINDS_12_HR'], 'WINDS_12_HR')
        
    def processMessage(self, msg):
        """Store WINDS_12_HR message.

        If ``cfg.TEXT_WX_LOCATION_SUPPORT`` is ``True`` will attempt to add
        geometry coordinates to this message.

        Args:
            msg (dict): Level 2 ``WINDS_12_HR`` message to store. All messages get stored
              to the ``WINDS_12_HR`` collection.
        """       
        pkey = msg['unique_name']

        # Augment with location if desired.
        if cfg.TEXT_WX_LOCATION_SUPPORT:
            msg = loc.addTextWxLoc(self.dbConnLocation, msg)

        # Remove redundant keys
        del msg['unique_name']
        del msg['location']
        del msg['type']

        self.dbCollection().update( \
            { '_id': pkey}, \
            msg, \
            upsert=True)


