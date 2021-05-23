import time, sys, os

class L1Base:
    """Base object for :mod:`fisb.level1.TwgoMatcher` and :mod:`fisb.level1.Unsegmenter`

    Holds common items, such as the expungeTime and dictionary
    containing the information for the objects being held.
    """
    def __init__(self, expungeTimeMins):
        """Initialize base object

        Args:
            expungeTimeMins (int): Number of minutes a message
                must not be matched until it is deleted from the
                '*looking for a match*' dictionary.
        """
        # Number of minutes after which items in
        # pendingMsgs are considered 'stuck' and will
        # be expunged. Internally this is stored as
        # seconds.
        self.expungeTimeSecs = expungeTimeMins * 60

        # Dictionary used by Unsegmenter
        self.pendingMsgs = {}

        # Holds information about current text and graphic portions
        # of messages.
        self.msgHx = {}

    def expungeItems(self, currentTime):
        """Delete all items in pendingMsgs whose last entry > expungeTime

        Args:
            currentTime (int): Current time (in seconds since 1970).
        """

        # Delete expired entries

        msgHxKeys = list(self.msgHx.keys())
        for x in msgHxKeys:
            lastUpdate = self.msgHx[x]['last_update_time']

            if (currentTime - lastUpdate) >= self.expungeTimeSecs:
                del self.msgHx[x]
