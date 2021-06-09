from db.harvest.MsgBase import MsgBase

class MsgFIS_B_UNAVAILABLE(MsgBase):
    """Methods for handling FIS_B_UNAVAILABLE messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['FIS_B_UNAVAILABLE'])
        
    def processMessage(self, msg, digest):
        """Stores ``FIS_B_UNAVAILABLE`` message in database.
        
        Args:
            msg (dict): Level 2 FIS-B Unavailable message to store.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return
        
        self.dbConn.MSG.replace_one( \
            { '_id': msg['_id']}, \
            msg, \
            upsert=True)
