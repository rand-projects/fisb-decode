from db.harvest.MsgBase import MsgBase

class MsgCANCEL_CWA(MsgBase):
    """Methods for cancelling CWA messages.

    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['CANCEL_CWA'], None)
        
    def processMessage(self, msg):
        """Cancel CWA message.

        The ``unique_name`` field of the level2 message is the same as
        the ``_id`` field in the ``SIGWX`` table. We just delete this
        entry.

        Args:
            msg (dict): Level2 message with CWA cancellation.
        """
        # Remove from SIGWX collection
        self.dbConn['SIGWX'].delete_one({ '_id': msg['unique_name']})
