"""Deduplicator class
"""

import time, sys, os, json, hashlib

class Deduplicator():
    """Checks for duplicate files and manages the system that holds them.

    Messages are hashed in a message digest and that is used as a key
    for a hashtable. The value of the hashtable is the insertion
    time, or the last time we checked the message for a duplicate.

    Every ``expungeHashtableMins`` we will go through and check each entry,
    deleting any that have not been seen in over ``expireMsgTimeMins``.
    """
    def __init__(self, expireMsgTimeMins, expungeHashtableMins):
        """Initialize class

        Args:
            expireMsgTimeMins (int): Number of minutes after which a message hash in 
                the hashtable will be expired after if we have not seen it. Each
                time a message is seen, the time is reset. So the message must
                have gone this amount of time without being check for a duplicate
                to be expired.
            expungeHashtableMins (int): Number of minutes we run the expunger
                to check for any unused keys from the hashtable.
        """
        # Store message expire time in seconds for normal use.
        self.expireMsgTimeSecs = expireMsgTimeMins * 60

        # Store hashtable expunger time in seconds for normal use.
        self.expungeHashtableSecs = expungeHashtableMins * 60

        # Dictionary holding the hashtable.
        self.hashtable = {}
        
        # Last time the hashtable expunger was run.
        self.lastExpungeTime = time.time()


    def okToSendMsg(self, msg):
        """Return ``True`` if this message hasn't been seen before.

        Args:
            msg (dict): Message to check to see if we can send it out.
        
        Returns:
            bool: ``True`` if this message is not a duplicate and OK to
            be sent to standard output or stored to a file.
            ``False`` if the message is a duplicate.
        """
        # Create hash digest of the message.
        digest = hashlib.sha224(str.encode(msg)).hexdigest()

        okToSend = False

        if digest not in self.hashtable:
            okToSend = True

        currentTime = time.time()

        # Add a new entry to the hashtable or
        # set the time of the last seen message for a duplicate.
        self.hashtable[digest] = currentTime

        # Expunge the hash table if it is time
        if (currentTime - self.lastExpungeTime) > self.expungeHashtableSecs:
            self.expungeHashtable(currentTime)
            self.lastExpungeTime = currentTime
            
        return okToSend

    def expungeHashtable(self, currentTime):
        """Delete any keys from hashtable not accessed in a while.

        Remove any items from the hashtable that haven't been accessed
        in the time specified by ``expungeHashtableMins`` at object
        creation.

        Args:
            currentTime (int): Recent result from ``time.time()``.
        """
        hashtableKeys = list(self.hashtable.keys())

        # Used to store keys to be deleted after iterating over the keys.
        keysToDelete = []
        
        # Can't delete keys while iterating dictionary, so we make a list.
        for x in hashtableKeys:
            lastTimeSeen = self.hashtable[x]
            if (currentTime - lastTimeSeen) > self.expireMsgTimeSecs:
                keysToDelete.append(x)

        # Delete any keys we flagged for deleting.
        for x in keysToDelete:
            del self.hashtable[x]
