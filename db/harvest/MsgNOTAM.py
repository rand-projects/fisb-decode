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
        
    def processMessage(self, msg, digest):
        """Store NOTAM message to database.

        If ``cfg.IMMEDIATE_CRL_UPDATE`` is ``True``, and this
        is a ``TRA``, ``TFR``, or ``TMOA`` NOTAM, will also
        update the collection ``CRL_16``, ``CRL_8`` or ``CRL_17`` with completed reports.

        Args:
            msg (dict): Level 2 ``NOTAM``
              message to store. All messages get stored
              to the ``NOTAM`` collection.
        """
        # NOTAM-TFRs send out an empty message every other
        # transmission. For those messages, there will be a 'renew-only'
        # slot.
        # TODO: For now, these messages are just ignored.
        # When implemented, these messages will need to be checked that
        # they exist. If the do exist, the expiration date will need to be
        # checked to see if it is later than the current one, and if so, the
        # expiration changed and the message sent out again.
        if 'renew-only' in msg:
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
