import time, sys, os

import fisb.level1.level1Exceptions as ex
from fisb.level1.L1Base import L1Base

class TwgoMatcher(L1Base):
    """Handle matching NOTAMS text and graphic portions.

    Take TWGO objects that have text and graphic parts (all but G-AIRMET, SUA)
    and will match them. The standard requires any text part comes
    out immediately, but will also match and send out the text and graphics
    when available.

    This class handles one of the thorniest issues in all of FIS-B:
    
    We want to match text and graphics. We are required to send any
    text part out immediately. However, if the message has a text and
    graphics part, we will send the text part first (if we get it 
    first), then the text with graphics. Now we get the text part again. If we
    just send it out, the graphics part is gone until it comes
    along again. That's not good. If we store and ignore it, we will
    send it out next as a text/graphics message. That is fine, and that will
    happen before any > 60 minutes expiration (standard requires these messages be
    kept for > 60 minutes (unless they contain an explicit stop time)). But what if the text 
    changes? The test groups certainly check for that. Well, we can
    check if the text changes and send it out as a new message. That's
    good. But what if the message has only a text part, and it never
    changes? *Oh, Oh*. Now we send the text part out once and never again.
    So when the system sends it again, we will ignore it. It will
    eventually expire in the system, never to be seen again.
    Not good. What I've actually described is the case of the normal
    text only TFR-NOTAM.
    
    Approach Taken:
    
    * We get a text part:
    
        * If we have not seen it before, store in msgHx and it send out (with graphics
          if we have any).
        * If we have seen before:
           * If the text has changed, remove any graphic notification and send out.
             (we consider this to be a new fresh message whose current graphics
             section may not agree with it. This could be debated).
           * If the text hasn't changed:
               * If we have never seen a graphics for this object, send out.
               * If we have seen a graphic, just wait for the next graphic.

     * We get a graphics part:

        * If we have a text part, send out both.
        * If we have no text part, just store away waiting for text part.

    """
    
    def __init__(self, expungeTimeMins):
        """Initialize class

        Args:
            expungeTimeMins (int): Number of minutes
                after which any messages still hanging around unmatched
                will be removed.
        """
        super().__init__(expungeTimeMins)
        
    def processFrame(self, frame, currentTime):
        """Given a TWGO message, process or store for later.

        Cancelations will always cause a message to be generated.

        We do make changes to the frame. We rename the ``contents``
        of any graphics part to ``contents_graphics`` and the
        ``contents`` of any text part to ``contents_text``. This way
        we keep all the data, but keep it separated.

        Args:
            frame (dict): Current frame as a dictionary.
            currentTime (int): Current system time (minutes since 1970)

        Returns:
            dict: ``None`` if we don't have anything to return. Otherwise
            returns the modified frame to send out.
        """
        productId = frame['product_id']

        contents = frame['contents']

        # Get whether textual or graphical
        recordFormat = contents['record_format'] # 8 graph, 2 text

        # We allow multiple graphic records, but only one text portion.
        records = contents['records']

        # Use the first record for recording the id (works
        # for both graphics and text).
        record = contents['records'][0]
        
        # Allow multiple graphical records, but only one text record.
        if (recordFormat == 2) and \
            len(records) != 1:
            raise ex.TwgoRecordsException('More than 1 text record in TWGO. Found {}'.format(len(records)))

        # Create a unique name.
        # Rules for uniqueness vary based on
        # type. See standard B.3.3 for details. Location is especially 
        # needed for D-NOTAMS.
        location = 'X'
        month = 0
        if 'location' in contents:
            location = contents['location']
        if 'month' in frame:
            month = frame['month']

        uniqueName = str(productId) + '-' + str(record['report_year']) + "-" + \
                     str(record['report_number']) + "-" + location + "-" + str(month)
        
        # Get the msgHx object for this name, or create one
        if uniqueName in self.msgHx:
            msgHxRecord = self.msgHx[uniqueName]
        else:
            msgHxRecord = {'text_contents': None, \
                        'graphics_contents': None, \
                        'last_update_time': currentTime}

            self.msgHx[uniqueName] = msgHxRecord

        if recordFormat == 8:
            # Graphical

            msgHxRecord['graphics_contents'] = contents

            # See if we have both parts
            if msgHxRecord['text_contents'] is not None:

                # yes, create and return the message
                frame['contents_graphics'] = contents
                frame['contents_text'] = msgHxRecord['text_contents']
                del frame['contents']
                return frame

            # no, wait till we get text.
            return None
           
        elif recordFormat == 2:
            # Textual

            # If a cancellation, return it
            if record['report_status'] == 0:
                frame['contents_text'] = frame['contents']
                del frame['contents']                
                return frame

            # A lot of ACTIVE records have a text field of "". Ignore these unless
            # they are of product type 8 which is an empty NOTAM-TFR-- in which case
            # just send it out. NOTAM-TFRs get sent text only every other transmission.
            # The ones with no text are just 'renewals'. This will result in a special
            # level 2 message and special handling in Harvest.
            if len(record['text']) == 0:
                if productId != 8:
                    return None
                else:
                    # NOTAM-TFRs with empty text are renewals.
                    frame['contents_text'] = frame['contents']
                    del frame['contents']                
                    return frame

            # If here, we don't have a text part yet. Send it out.
            if msgHxRecord['text_contents'] is None:
                # Brand new.
                msgHxRecord['text_contents'] = contents
                if msgHxRecord['graphics_contents'] is not None:
                    frame['contents_graphics'] = msgHxRecord['graphics_contents']
                frame['contents_text'] = contents
                del frame['contents']
                return frame

            # We have at least a text part. See if we have changed text.
            if msgHxRecord['text_contents']['records'][0]['text'] != \
                contents['records'][0]['text']:
                # Text is changed. Reset any graphics portion and resend.
                msgHxRecord['graphics_contents'] = None
                msgHxRecord['text_contents'] = contents
                frame['contents_text'] = contents
                del frame['contents']
                return frame

            # Store text.
            msgHxRecord['text_contents'] = contents

            # See if we have both parts
            if msgHxRecord['graphics_contents'] is not None:

                # yes, create and return the message
                frame['contents_graphics'] = msgHxRecord['graphics_contents']
                frame['contents_text'] = contents
                del frame['contents']
                return frame

            # If here, we don't have a graphics part. Send it
            frame['contents_text'] = contents
            del frame['contents']
            return frame
        else:
            raise ex.TwgoRecordFormatException(\
                'TWGO found record format not 2 or 8. Found: {}'.\
                format(recordFormat))
