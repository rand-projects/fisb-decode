from datetime import datetime, timezone

from db.harvest.MsgBase import MsgBase
import db.harvest.testing as test

class MsgSERVICE_STATUS(MsgBase):
    """Methods for updating ``SERVICE_STATUS``.

    Service status is tricky, since if there is a lot of traffic,
    different aircraft will be placed in different messages. What
    we do is maintain a merged view of all aircraft such that the
    entry we place in the database is a current view of all valid
    planes.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['SERVICE_STATUS'], 'SERVICE_STATUS')
        
        self.planes = {}

    def processMessage(self, msg):
        """Store ``SERVICE_STATUS`` message information to database
        combined with other current information.

        We maintain a dictionary of all current planes. The
        dictionary uses the planes id as key, and it's value
        is when the message arrived. Any plane that has not been
        reported on in 40 seconds is deleted from the dictionary.

        The new result is stored in the ``SERVICE_STATUS`` collection
        with the ``_id`` being the station that sent the message.

        Args:
            msg (dict): Level 2 ``SERVICE_STATUS``
              message.
        """       
        # Update the planes dictionary by adding all planes in the
        # current message
        traffic = msg['traffic']
        expireTime = msg['expiration_time']

        for x in traffic:
            self.planes[x] = expireTime

        # Now expire all entries in planes older than 40 seconds
        # by creating the newPlanes dictionary and storing all
        # the current aircraft in it. Replace self.planes with the
        # new dictionary (preventing 'remove entry while iterating'
        # headaches).
        #
        # Note: Because we are creating this from an a current
        # SERVICE_STATUS message with active planes, this will never
        # be empty.
        utcNow = test.datetimeNow()
        newPlanes = {}
        trafficList = []
        
        for x in self.planes:
            if (utcNow - self.planes[x]).total_seconds() < 40:
                newPlanes[x] = self.planes[x]
                trafficList.append(x)
                
        self.planes = newPlanes

        serviceStatus = {}
        serviceStatus['traffic'] = trafficList
        serviceStatus['expiration_time'] = expireTime

        # Make new SERVICE_STATUS entry for database
        self.dbCollection().update( \
            { '_id': msg['unique_name']}, \
            serviceStatus, \
            upsert=True)
