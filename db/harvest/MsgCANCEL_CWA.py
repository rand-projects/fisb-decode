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

        The ``unique_name`` field of the level2 message is the same as
        the ``_id`` field in the ``SIGWX`` table. We just delete this
        entry.

        Args:
            msg (dict): Level2 message with CWA cancellation.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return      

        self.dbConn.MSG.replace_one( \
            {'_id': msg['_id']}, \
            msg, \
            upsert=True)

        # Remove CWA
        self.dbConn.MSG.delete_one({ '_id': 'CWA-' + msg['unique_name']})
