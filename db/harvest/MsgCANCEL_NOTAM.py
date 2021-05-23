from db.harvest.MsgBase import MsgBase

class MsgCANCEL_NOTAM(MsgBase):
    """Methods for cancelling NOTAM messages.
    """
    def __init__(self):
        """Initialize
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['CANCEL_NOTAM'], None)
        
    def processMessage(self, msg):
        """Cancel G_AIRMET message.

        The ``unique_name`` field of the level2 message is the same as
        the ``_id`` field in the various tables associated with
        NOTAMS. We just delete this entry.

        There are two collections for NOTAMs: ``NOTAM`` and ``NOTAM_TFR``,
        so we attempt to cancel from each. This also might be a
        ``FIS_B_UNAVAILABLE`` message, so try there also.
        These usually expire, but the message mechanisms
        do allow for a cancellation even if the standard doesn't
        indicate it.

        Args:
            msg (dict): Level2 message with G_AIRMET cancellation.
        """        
        # Remove from NOTAM_TFR, FIS_B_UNAVAILABLE, and NOTAM collections
        # (it will only be in one (or none) or course).
        self.dbConn['NOTAM_TFR'].delete_one({ '_id': msg['unique_name']})
        self.dbConn['NOTAM'].delete_one({ '_id': msg['unique_name']})
        self.dbConn['FIS_B_UNAVAILABLE'].delete_one({ '_id': msg['unique_name']})
