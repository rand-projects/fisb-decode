from db.harvest.MsgBase import MsgBase

class MsgSUA(MsgBase):
    """Methods for handling Special Use Airspace (``SUA``) messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['SUA'])
        
    def processMessage(self, msg, digest):
        """Store SUA message.

        Args:
            msg (dict): Level 2 ``SUA`` message to store. All messages get stored
              to the ``SUA`` collection.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return
  
        self.dbConn.MSG.replace_one( \
            {'_id': msg['_id']}, \
            msg, \
            upsert=True)
