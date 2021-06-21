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

        We create a new message with the same _id as the original
        (replacing this messages ``CANCEL_G_AIRMET`` with ``G_AIRMET``).
        The message has only the essential fields but adds a ``cancel`` slot
        which contains the unique name.

        Args:
            msg (dict): Level2 message with G_AIRMET cancellation.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return      

        uniqueName = msg['unique_name']
        msg['type'] = 'G_AIRMET'
        msg['_id'] = 'G_AIRMET-' + uniqueName
        msg['cancel'] = uniqueName
        
        self.dbConn.MSG.replace_one( \
            {'_id': 'G_AIRMET-' + uniqueName}, \
            msg, \
            upsert=True)
