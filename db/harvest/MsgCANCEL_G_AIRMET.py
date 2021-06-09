from db.harvest.MsgBase import MsgBase

class MsgCANCEL_G_AIRMET(MsgBase):
    """Methods for cancelling G_AIRMET messages.
    """
    def __init__(self):
        """Initialize
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['CANCEL_G_AIRMET'])
        
    def processMessage(self, msg, digest):
        """Cancel G_AIRMET message.

        The ``unique_name`` field of the level2 message is the same as
        the ``_id`` field in the ``G_AIRMET`` table. We just delete this
        entry.

        Args:
            msg (dict): Level2 message with G_AIRMET cancellation.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return      

        self.dbConn.MSG.replace_one( \
            {'_id': msg['_id']}, \
            msg, \
            upsert=True)

        # Remove G_AIRMET
        self.dbConn.MSG.delete_one({ '_id': 'G_AIRMET-' + msg['unique_name']})
