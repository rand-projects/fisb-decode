from db.harvest.MsgBase import MsgBase

class MsgCANCEL_NOTAM(MsgBase):
    """Methods for cancelling NOTAM messages.
    """
    def __init__(self):
        """Initialize
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['CANCEL_NOTAM'])
        
    def processMessage(self, msg, digest):
        """Cancel NOTAM message.

        The ``unique_name`` field of the level2 message is the same as
        the ``_id`` field in the various tables associated with
        NOTAMS. We just delete this entry.

        How this works is we replace the message with an empty message
        (except for required fields) that has a ``cancel`` field whose
        value is the unique name. Essentially, we change the type of the
        cancel message to ``NOTAM``.

        Args:
            msg (dict): Level2 message with NOTAM cancellation.
        """        
        if not self.checkThenAddIdDigest(msg, digest):
            return      

        msg['type'] = 'NOTAM'
        uniqueName = msg['unique_name']
        msg['_id'] = 'NOTAM-' + uniqueName
        msg['cancel'] = uniqueName

        self.dbConn.MSG.replace_one( \
            {'_id': 'NOTAM-' + uniqueName}, \
            msg, \
            upsert=True)
