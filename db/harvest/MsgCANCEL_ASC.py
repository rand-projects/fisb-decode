from db.harvest.MsgBase import MsgBase

class MsgCANCEL_ASC(MsgBase):
    """Methods for cancelling AIRMET SIGMET CWA (ASC) messages.

    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['CANCEL_CWA', 'CANCEL_AIRMET', 'CANCEL_SIGMET'])
        
    def processMessage(self, msg, digest):
        """Cancel CWA/AIRMET/SIGMET messages.

        All this does is update any existing CWA/AIRMET/SIGMET message by
        changing the type from ``CANCEL_xxx`` to ``xxx`` with
        minimum contents, but adding the ``cancel`` field.
        
        Args:
            msg (dict): Level2 message with CWA cancellation.
        """
        if not self.checkThenAddIdDigest(msg, digest):
            return      

        # Message gets a new type so it fits in the CWA/AIRMET/SIGMET stream.
        uniqueName = msg['unique_name']
        msgType = msg['type']

        if msgType == 'CANCEL_CWA':
            newType = 'CWA'

        elif msgType == 'CANCEL_AIRMET':
            newType = 'AIRMET'
        else:
            # CANCEL_SIGMET
            newType = 'SIGMET'
            
        msg['type'] = newType
        msg['_id'] = newType + '-' + uniqueName
        msg['cancel'] = uniqueName

        self.dbConn.MSG.replace_one( \
            {'_id': msg['_id']}, \
            msg, \
            upsert=True)
