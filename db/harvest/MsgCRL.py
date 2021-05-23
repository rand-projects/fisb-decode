import sys, os, pprint
from datetime import datetime, timezone

from db.harvest.MsgBase import MsgBase
import db.harvest.harvestConfig as cfg
import db.harvest.testing as test

class MsgCRL(MsgBase):
    """Methods for handling CRL messages.
    """
    def __init__(self):
        """Initialize
        """
        # All message types must indicate the actual dictionary
        # 'type' handled
        super().__init__(['CRL'], 'CRL')

    def expireMessages(self):
        """Expire CRL messages.

        There are 7 mongo collections that contain CRL messages. All of them
        will be expired by this function.

        Expire messages from:

        - ``CRL_8``
        - ``CRL_11``
        - ``CRL_12``
        - ``CRL_14``
        - ``CRL_15``
        - ``CRL_16``
        - ``CRL_17``
        """
        for x in ['CRL_8', 'CRL_11', 'CRL_12', 'CRL_14', 'CRL_15', 'CRL_16', 'CRL_17']:
            ptr = self.dbConn[x]
            ptr.delete_many({'expiration_time': {'$lte': test.datetimeNow()}})
            
    def collectionNameFromProductId(self, productId):
        """Return mongo collection name from product ID.

        Nothing more difficult than concatinating ``CRL_`` with
        ``productId``. Example: Product id 8 returns ``CRL_8``.

        Args:
            productId (int): FIS-B product id associated with a CRL.

        Returns:
            str: Collection name for CRL associated with this CRL.
        """
        return 'CRL_' + str(productId)

    def dictFromQuery(self, collection, find1, find2):
        """Create a dictionary of all ``_id``'s returned from a query.

        Given a collection pointer and the 2 parts of a find query, 
        return a dictionary containing an key for each ``_id``. The 
        value of each entry will be if the report has text, graphics,
        or both (one of the strings ``/TO``, ``/TG``, and ``/GO``).
        This is important because we can't count a report as
        complete until all the components that make up the report are
        present.
        
        This is sort of hard to explain but easy to see what is happening. Here is
        code that calls this function:

        .. code-block:: python

            if productId == 8: 
                idDict = self.dictFromQuery(self.dbConn.NOTAM_TFR, 
                        {}, 
                        {'id': 1, 'contents': 1, 'geojson': 1})
            elif productId in [11, 12, 15]:  # AIRMET, SIGMET, WST, CWA
                idDict = self.dictFromQuery(self.dbConn.SIGWX, 
                        {}, 
                        {'id': 1, 'contents': 1, 'geojson': 1})
            elif productId == 14:
                idDict = self.dictFromQuery(self.dbConn.G_AIRMET, 
                        {}, 
                        {'id': 1, 'contents': 1, 'geojson': 1})
            elif productId == 16:
                idDict = self.dictFromQuery(self.dbConn.NOTAM, 
                        {'subtype': 'TRA'}, 
                        {'id': 1, 'subtype': 1, 'contents': 1, 'geojson': 1})
            elif productId == 17:
                idDict = self.dictFromQuery(self.dbConn.NOTAM, 
                        {'subtype': 'TMOA'}, 
                        {'id': 1, 'subtype': 1, 'contents': 1, 'geojson': 1})


        Args:
            collection (object): Pointer to MongoDB collection to use.
            find1 (dict): First part of the find query.
            find2 (dict): Second part of the find query.

        Returns:
            dict: Dictionary with one entry for each ``_id``.
        """
        d = {}
        for r in collection.find(find1, find2):
            # Need to figure out if a message as a graphics section, text section, or both.
            # This has to match up for CRL completeness.
            hasText = False
            hasGraphics = False

            if 'contents' in r:
                hasText = True
            if 'geojson' in r:
                hasGraphics = True

            if hasText and hasGraphics:
                val = '/TG'
            elif hasText:
                val = '/TO'
            else:
                val = '/GO'

            d[r['_id']] = val
        
        return d

    def updateReports(self, reportList, idDict):
        """Update a list of report names with an '``*``' if in the database.

        Given a list of CRL reports from a FIS-B message, return
        a new list identical entries, but annotate an entry with
        an '``*``' at the end if the entry is in the database.

        Args:
            reportList (list): List of report ids from the FIS-B message. This
               will be the ``reports`` value from a level 2 ``CRL`` message.
            idDict (dict): Dictionary of report ids for this type of message
                that exist in the database.

        Returns:
            list: List of reports with annotations if indicated.
        """
        newReportList = []

        for x in reportList:
            # Remove any existing '*'
            if x[-1] == '*':
                x = x[:-1]

            # 'x' contains the /xx part of the report. Only pure report name in idDict.
            reportId = x.split('/')[0]

            if reportId in idDict:
                # Only flag text+graphics objects complete if they have both parts.
                if '/TG' in x:
                    if idDict[reportId] == '/TG':
                        x = x + '*'
                else:
                    x = x + '*'
            newReportList.append(x)

        return newReportList

    def processMessage(self, msg):
        """Place CRL messages in the database.

        Place CRL message in the database. If configured, will annotate the
        list of messages so that the '``reports``' list will have an '``*``' appended
        to it if it is already in the database.

        Args:
            msg (dict): FIS-B level 2 ``CRL`` message to store in database.
        """
        productId = msg['product_id']
        collectionName = self.collectionNameFromProductId(productId)

        # Since this is database heavy, only annotate CRL reports
        # if desired.
        if cfg.ANNOTATE_CRL_REPORTS:

            # Update the reports field by adding a '*' to the name if 
            # we have the report. Else don't add anything.
            idDict = {}

            # Run a query that creates a dictionary of all the _id's for
            # given type. All of 11,12,15 types are in SIGWX, and the
            # contents of the 'reports' field in the message will filter
            # out the type.
            if productId == 8: 
                idDict = self.dictFromQuery(self.dbConn.NOTAM_TFR, \
                                            {}, \
                                            {'id': 1, 'contents': 1, 'geojson': 1})
            elif productId in [11, 12, 15]:  # AIRMET, SIGMET, WST, CWA
                idDict = self.dictFromQuery(self.dbConn.SIGWX, \
                                            {}, \
                                            {'id': 1, 'contents': 1, 'geojson': 1})
            elif productId == 14:
                idDict = self.dictFromQuery(self.dbConn.G_AIRMET, \
                                            {}, \
                                            {'id': 1, 'contents': 1, 'geojson': 1})
            elif productId == 16:
                idDict = self.dictFromQuery(self.dbConn.NOTAM, \
                                            {'subtype': 'TRA'}, \
                                            {'id': 1, 'subtype': 1, 'contents': 1, 'geojson': 1})
            elif productId == 17:
                idDict = self.dictFromQuery(self.dbConn.NOTAM, \
                                            {'subtype': 'TMOA'}, \
                                            {'id': 1, 'subtype': 1, 'contents': 1, 'geojson': 1})

            # Replace reports with an annotated one
            msg['reports'] = self.updateReports(msg['reports'], idDict)

        pkey = msg['station']

        del msg['station']
        del msg['product_id']
        del msg['unique_name']
        del msg['type']

        ptr = self.dbConn[collectionName]
        ptr.update( \
            { '_id': pkey}, \
            msg, \
            upsert=True)
