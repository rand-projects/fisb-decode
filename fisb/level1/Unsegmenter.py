import time, sys, os, json

import fisb.level1.level1Exceptions as ex
from fisb.level0.apdu_twgo import apdu_twgo
from fisb.level1.L1Base import L1Base

class Unsegmenter(L1Base):
    """Store segmented messages until all parts arrive, then send out as a new frame.
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
        """Given a segmented message, process or store for later.

        Will only be called for segmented frames.

        Args:
            frame (dict): Current segmented frame as a dictionary.
            currentTime (int): Current system time (secs since 1970)

        Returns:
            dict: If this is a completed message, this will be
            a modified frame with the new contents, ``s_flag`` set to 0,
            and ``product_file_length``, and ``apdu_number``
            removed. A return of ``None`` implies this
            segmented message doesn't have all its parts yet.

        Raises:
            SegmentIdxOutOfBoundsException: If we find an illegal or unexpected segment
                number.
        """

        # Create a unique key for the item consisting of the
        # product_id and product_file_id.
        # S added to tell this is a segmented message when expunging.
        uniqueName = 'S' + str(frame['product_id']) + '-' + \
                     str(frame['product_file_id'])
                        
        # This is the index number into the segment array.
        # 'apdu_number' is 1 based
        segment_index = frame['apdu_number'] - 1

        # pendingMsgs is a dictionary whose key is
        # the product_id + '-' + product_file_id.
        # The contents is another dictionary with the
        # following keys:
        #
        # insert_time time since 1/1/1970 record was created (in minutes)
        # number_i_need - Number of total segments for this msg
        # number_i_have - Number of segments I have
        # segments - List of all segments. Length is 'number_i_need'
        #            Entries are initially None

        if uniqueName not in self.pendingMsgs:
            # Make a new entry
            number_i_need = frame['product_file_length']
            segments = [None] * number_i_need

            itemDict = {}
            itemDict['number_i_need'] = number_i_need
            itemDict['insert_time'] = currentTime
            itemDict['number_i_have'] = 1

            if segment_index >= number_i_need:
                raise ex.SegmentIdxOutOfBoundsException('Segment index: {} Segments Size {}.\n{}'.format(segment_index, number_i_need, json.dumps(frame, indent = 2)))
            
            segments[segment_index] = frame
            itemDict['segments'] = segments
            self.pendingMsgs[uniqueName] = itemDict
            return None
        
        else:
            # Update current entry
            itemDict = self.pendingMsgs[uniqueName]

            # See if we have the entry
            segments = itemDict['segments']

            if segments[segment_index] is not None:
                # Currently have this index. Nothing to do
                return None

            # New segment, add it
            segments[segment_index] = frame
            number_i_have = itemDict['number_i_have'] + 1

            # Check if found all the segments
            if number_i_have < itemDict['number_i_need']:
                # Not enough yet
                itemDict['number_i_have'] = number_i_have
                itemDict['segments'] = segments
                self.pendingMsgs[uniqueName] = itemDict
                return None

            # Yay, found everything. Create new frame, delete
            # from pendingMsgs
            newFrame = self.consolidateFrames(segments)

            del self.pendingMsgs[uniqueName]
            return newFrame

    def consolidateFrames(self, segments):
        """Make segmented frames into a single message.

        Take all the segmented frames that make up a message and return
        a de-segmented message.

        New frame is created from a list of the frames making up the
        message. New frame has ``s_flag`` set to 0, and none of the other
        segmented message headers.

        Args:
            segments (list): List containing one item for each segmented message
                making up the complete message. Segmented messages are in the correct
                order.

        Returns:
            dict: Dictionary containing the new frame. If we did not complete 
            an entire message, ``None`` is returned.
        """
        
        # We use the first frame as the basis for the final
        # frame
        frame = segments[0]

        # Reset the frame to look like a normal frame
        frame['s_flag'] = 0

        # NOTE: We could delete the 'product_file_id' since it is no
        # longer used or needed. We keep it only because if you are
        # looking for a multisegmented message, it is the only thing
        # that you can identify a message by (the contents part with
        # the report number is in the 'contents' section and still
        # in hex at the end of level0). At the end of level1, you can
        # match a report number to the actual level0 message.
        del frame['product_file_length']
        del frame['apdu_number']

        # Create the actual byte string to decode
        byteStr = ''

        idx = 0
        for msg in segments:
            # We use the entire byte string for the first element.
            # This will include the TWGO header.
            if idx == 0:
                byteStr = msg['contents']
            else:
                # For the other elements, we have to skip over
                # the TWGO header (included for every segment and
                # which is 6 bytes [since it is still a string,
                # 12 characters]).
                byteStr = byteStr + msg['contents'][12:]

            idx += 1
            
        newContents = apdu_twgo(bytes.fromhex(byteStr), \
                                frame['product_id'], False)
        frame['contents'] = newContents

        return frame
