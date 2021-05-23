from db.harvest.MsgBase import MsgBase

class MsgSUA(MsgBase):
    """Methods for handling Special Use Airspace (``SUA``) messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['SUA'], 'SUA')
        
    def processMessage(self, msg):
        """Store SUA message.

        Args:
            msg (dict): Level 2 ``SUA`` message to store. All messages get stored
              to the ``SUA`` collection.
        """       
        pkey = msg['unique_name']

        # Remove redundant keys
        del msg['unique_name']
        del msg['type']

        self.dbCollection().update( \
            { '_id': pkey}, \
            msg, \
            upsert=True)
