import pprint

from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg

class MsgNOTAM(MsgBase):
    """Methods for handling NOTAM (-D -FDC)  messages.
    """
    def __init__(self):
        """Initialize.
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['NOTAM'])
    
    def renewNotamTFR(self, msg):
        """Check the renewal NOTAM-TFR message to update the expiration_time
        if needed.

        We must have the actual NOTAM-TFR (with text) and the expiration time on
        that object must be earlier than the renewal time. We just return ``None``
        if the criteria doesn't match. Otherwise, we return the original message
        with a new expiration time.

            Args:
                msg (dict): Renewal message dictionary. Doesn't contain TFR text,
                    just an updated expiration_time.

            Returns:
                (dict): Returns the original NOTAM-TFR with an updated expiration
                    time if the message existed and the new expiration time is later
                    than the original message. Otherwise returns None.
        """
        
        # See if the original NOTAM-TFR exists.
        # The station must also match.
        #
        # NOTE: Haven't really thought out the implications of multiple stations
        # feeding the same message and how that affects the CRLs.
        pkey = msg['type'] + '-' + msg['unique_name']
        origMsg = self.dbConn.MSG.find_one({'_id': pkey, 'station': msg['station']})

        # Message didn't match.
        if origMsg == None:
            return None

        # Make sure new expiration date is > than orig expiration date
        if origMsg['expiration_time'] >= msg['expiration_time']:
            return None

        # This is a renewal with a later expiration time.
        # Set new expiration time
        origMsg['expiration_time'] = msg['expiration_time']

        # Delete existing digest, and insert_time (_id is fine, it will just get overriden.)
        del origMsg['insert_time']
        del origMsg['digest']

        return origMsg
        
    def processMessage(self, msg, digest):
        """Store NOTAM message to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, and this
        is a ``TRA``, ``TFR``, or ``TMOA`` NOTAM, will also
        update the collection ``CRL_16``, ``CRL_8`` or ``CRL_17`` with completed reports.

        Args:
            msg (dict): Level 2 ``NOTAM``
              message to store. All messages get stored
              to the ``NOTAM`` collection.
            digest (str): Message digest of received JSON message.
        """
        # NOTAM-TFRs send out an empty message every other
        # transmission. For those messages, there will be a 'renew-only'
        # slot.
        # 
        # Check to see if the original NOTAM-TFR exists and if the
        # new expiration time is later than the current one. If so,
        # the message will be the original message with the new 
        # expiration date. We use the new digest from the renewal
        # so the original message doesn't match.
        if 'renew-only' in msg:
            msg = self.renewNotamTFR(msg)
            
            # If msg is None, there is no processing to be done.
            if msg == None:
                return

        if not self.checkThenAddIdDigest(msg, digest):
            return

        # Convert to geojson
        msg = self.geometryToGeojson(msg)

        # See if SUA NOTAM-D
        if (cfg.SUA_LOCATION_SUPPORT) and ('subtype' in msg) and (msg['subtype'] == 'D-SUA'):
            if ('airspace' in msg):
                airspace = msg['airspace']

                suaLoc = self.dbConnLocation.SUA.find_one({'_id': airspace})
                if suaLoc is not None:
                    del suaLoc['_id']
                    msg['geojson'] = suaLoc

        self.dbConn.MSG.replace_one( \
            { '_id': msg['_id']}, \
            msg, \
            upsert=True)

        msgSubtype = msg['subtype']
        if cfg.IMMEDIATE_CRL_UPDATE and \
            (msgSubtype in ['TFR', 'TMOA', 'TRA']):

            hasTextAndGraphics = False
            if ('contents' in msg) and ('geojson' in msg):
                hasTextAndGraphics = True

            if msgSubtype == 'TMOA':
                self.updateCRL('CRL_17', msg['unique_name'], msg['station'], hasTextAndGraphics)
            elif msgSubtype == 'TRA':
                self.updateCRL('CRL_16', msg['unique_name'], msg['station'], hasTextAndGraphics)
            elif msgSubtype == 'TFR':
                self.updateCRL('CRL_8', msg['unique_name'], msg['station'], hasTextAndGraphics)
