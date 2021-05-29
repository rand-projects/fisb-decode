from db.harvest.MsgBase import MsgBase
import db.harvest.location as loc
import db.harvest.harvestConfig as cfg

class MsgMETAR(MsgBase):
    """Methods for handling METAR messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['METAR'], 'METAR')
        
    def processMessage(self, msg):
        """Store METAR message.

        If ``cfg.TEXT_WX_LOCATION_SUPPORT`` is ``True`` will attempt to add
        geometry coordinates to this message.

        Args:
            msg (dict): Level 2 ``METAR`` message to store. All messages get stored
              to the ``METAR`` collection.
        """
        pkey = msg['unique_name']

        # Augment with location if desired.
        if cfg.TEXT_WX_LOCATION_SUPPORT:
            msg = loc.addTextWxLoc(self.dbConnLocation, msg)
            
        # Remove redundant keys
        del msg['unique_name']
        del msg['location']

        self.dbCollection().update( \
            { '_id': pkey}, \
            msg, \
            upsert=True)


