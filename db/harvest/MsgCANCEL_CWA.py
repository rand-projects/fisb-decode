from db.harvest.MsgBase import MsgBase

class MsgCANCEL_CWA(MsgBase):
    """Methods for cancelling CWA messages.

    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['CANCEL_CWA'])
        
    def processMessage(self, msg, digest):
        """Cancel CWA message.

        All this does is update any existing CWA message by
        changing the type from ``CANCEL_CWA`` to ``CWA`` with
        minimum contents, but adding the ``cancel`` field.
        
        Args:
            msg (dict): Level2 message with CWA cancellation.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return      

        # Message gets a new type so it fits in the CWA stream.
        uniqueName = msg['unique_name']
        msg['type'] = 'CWA'
        msg['cancel'] = uniqueName

        self.dbConn.MSG.replace_one( \
            {'_id': 'CWA-' + uniqueName}, \
            msg, \
            upsert=True)
