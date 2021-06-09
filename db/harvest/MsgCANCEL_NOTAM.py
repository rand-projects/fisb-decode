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

        There are two collections for NOTAMs: ``NOTAM`` and ``NOTAM_TFR``,
        so we attempt to cancel from each. This also might be a
        ``FIS_B_UNAVAILABLE`` message, so try there also.
        These usually expire, but the message mechanisms
        do allow for a cancellation even if the standard doesn't
        indicate it.

        Args:
            msg (dict): Level2 message with G_AIRMET cancellation.
        """        
        if not self.checkThenAddIdDigest(msg, digest):
            return      

        self.dbConn.MSG.replace_one( \
            {'_id': msg['_id']}, \
            msg, \
            upsert=True)

        pkey = msg['unique_name']

        # See if this is a NOTAM_TFR. We just check to see if it is
        # there, if not we assume normal NOTAM. This might end up cancelling
        # a non-existant NOTAM. NOTAM_TFR and NOTAM_FDC share numbers under
        # 10000, so we check there first.
        notamNum = int(pkey.split('-')[1])

        if notamNum < 10000:
            doc = self.dbConn.NOTAM_TFR.find_one({'_id': 'NOTAM_TFR-' + pkey})
            if doc is not None:
                self.dbConn.MSG.delete_one({'_id': 'NOTAM_TFR-' + pkey})
                return                

        self.dbConn.MSG.delete_one({'_id': 'NOTAM-' + pkey})
