"""Decode and create messages from frame type 14 (Current Report List)

Produces the 'CRL' message type. CRLs are tied to a particular
ground station, so you will get one CRL of each type for each
ground station.

CRLs have two fields that are unique to it:

- ``range_nm`` is the radius from the station that these reports
  apply to.
- ``reports`` is a list of all messages this station has sent out for
  its specific Product Id. This list will be empty if there are no 
  messages of this type, or will contain one item of the format
  ``'x-y/tg'`` for each report:

  - ``x`` is either a month or year (1 or 2 digits) representing the
    month or year of the report (what this is varies by Product Id)
  - ``y`` is the FIS-B report number.
  - ``tg`` is one of ``'TO'`` for a text only report, ``'GO'`` for
    a graphics only report, and ``'TG'`` if the report has both a 
    text and graphics part.

FIS-B produces CRL messages for the following product types:

- (8) NOTAM-TFR only
- (11) AIRMET
- (12) SIGMET
- (14) G-AIRMET
- (15) CWA
- (16) NOTAM-TRA
- (17) NOTAM-TMOA
"""

import sys, os, json, time, re

import fisb.level2.level2Config as cfg
import fisb.level2.utilities as util
import fisb.level2.level2Exceptions as ex

#: Messages stuck in the system. Also see
#: :mod:`fisb.level2.msg11_12_15` which ignores
#: the text of these messages.
BAD_MESSAGES_CRL12 = ['20-7489', '20-7676']

def msgCrl(rcvdTime, frame, station):
    """Process CRL (Current Report List) messages.

    Args:
        rcvdTime (str): ISO time message was received. Used for calculating
            expiration time.
        frame (dict): Dictionary frame containing the CRL data.
        station (str): Station which sent this CRL.

    Returns:
        dict: Dictionary with completed message.

    Raises:
        BadCrlTypeException: If we got a CRL for a product type that
          doesn't have one.
        IllegalCrlException: If both text flag and graphics flag are 0.
    """
    newMsg = {}

    productId = frame['product_id']
    newMsg['type'] = 'CRL'
    newMsg['unique_name'] = 'CRL-' + str(productId) + '-' + station
    newMsg['station'] = station
    newMsg['product_id'] = productId
    newMsg['range_nm'] = frame['product_range_nm']

    if frame['o_flag'] == 1:
        newMsg['has_overflow'] = True

    # Expiration of time of the CRL depends upon the normal transmission time of
    # the message.  It is set at twice the nominal transmission rate of the
    # regular message (see Table C-1 in standard).
    if productId in [8, 15, 16, 17]:
        expirationTime = util.addMinutesToIso8601(rcvdTime, 2 * 10)
    elif productId in [11, 12, 14]:
        expirationTime = util.addMinutesToIso8601(rcvdTime, 2 * 5)
    else:
        raise ex.BadCrlTypeException('Got product_id of {}'.format(productId))

    reportList = []
    
    for x in frame['reports']:
        # Note: Per 258B, for NOTAM-TRA and NOTAM-TMOA, 'report_year'
        # is really the report month. Not sure what difference this makes.
        uniqueName = str(x['report_year_or_month']) + '-' + str(x['report_number'])
    
        # There are bad messages that just sit in the system forever and
        # don't expire (current record holder is over a year). If these
        # come in the '12' CRL, ignore them.
        if (productId == 12) and (uniqueName in BAD_MESSAGES_CRL12):
            continue

        # Append a string at the end, one of '/TO', '/GO', '/TG' to indicate
        # if this report is text only, graphics only, or text and graphics.
        # We can't count a report complete until we have all the needed sections.
        textFlag = x['text_flag']
        graphicsFlag = x['graphics_flag']
        if (textFlag == 1) and (graphicsFlag == 1):
            reportType = '/TG'
        elif (textFlag == 0) and (graphicsFlag == 1):
            reportType = '/GO'
        elif (textFlag == 1) and (graphicsFlag == 0):
            reportType = '/TO'
        else:
            raise ex.IllegalCrlException('Both text flag and graphics flag are 0')

        reportList.append(uniqueName + reportType)

    newMsg['reports'] = reportList
    newMsg['no_msg_digest'] = 't'
    newMsg['expiration_time'] = expirationTime
    
    return newMsg
