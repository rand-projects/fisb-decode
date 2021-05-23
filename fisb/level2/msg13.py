"""Decode and create messages from product id 13 (SUA) frames.

Process Special Use Airspace (SUA) messages. 
These messages are in the process of being phased out and replace
by NOTAM-TMOA messages. They are recommended to not be used.

The reference for decoding these messages
comes from '*FAA/SBS Surveillance
and Broadcast Services Description Document SRT-047, Revision 01
10/24/2011*'. There is a large comment in the code describing the 
various fields.
"""

import sys, os, json, time, re

import fisb.level2.level2Config as cfg
import fisb.level2.utilities as util
import fisb.level2.level2Exceptions as ex

# SUA Regex for 'valid_time'. group(1) -> date, group(2) -> schedule_id
SUA_RE = re.compile(r"SUA ([0-3]\d[0-2]\d[0-5]\d) (.+)")

def msg13(records0, rYear, rMonth, rDay):
    """Decode SUA product_id 13 messages for appropriate processing

    Args:
        records0 (dict): Contents of ``frame['contents']['records'][0]``
        rYear (int): Message received year.
        rMonth (int): Message received month.
        rDay (int): Message received day.

    Returns:
        dict: Dictionary with completed message.
    """
    newMsg = {}
    
    # Create the report id
    reportId = str(records0['report_year']) + '-' + str(records0['report_number'])

    # Never see cancellations here. Generate exception if we do
    if records0['report_status'] == 0:
        raise ex.SuaException("SUA cancellations not implemented.")

    # Strip trailing \n off record and break into fields
    text = records0['text'].rstrip()
    textList = text.split('|')

    # Fields for the SUA
    #
    # [00] SUA, 'valid_time' in standard FAA six digit time, and
    #      'schedule_id' (a unique assigned value).
    #      Note: 'valid_time' is just the time the entry was last
    #      validated by the FIS-B data provider. It is very suspect
    #      since some of the time it just seems like boilerplate.
    #      For the purpose of this message, it is not used.
    # [01] 'airspace_id' Airspace catalog ID
    # [02] 'schedule_status'
    #        P Pending approval
    #        W Waiting to start
    #        H Hot. Activated
    # [03] 'airspace_type'
    #        W Warning area (*)
    #        R Restricted area (*)
    #        M MOA (*)
    #        P Prohibited area
    #        L Alert area
    #        A Air traffic control assigned airspace
    #        I Instrument route
    #        V Visual route
    #        S Slow route
    #        B Refueling route (*)
    #        O Other (*)
    #        T Refueling track
    #     (*) indicates values actually seen
    # [04] 'airspace_name' up to 50 characters.
    # [05] 'start_time' format yymmddHHMM
    # [06] 'end_time' format yymmddHHMM
    # [07] 'low_altitude' lower altitude in 100's of feet (unknown AGL vs MSL)
    # [08] 'high_altitude' lower altitude in 100's of feet (unknown AGL vs MSL)
    # [09] 'separation_rule'
    #       ' ' Unspecified (never seen)
    #       'A' Aircraft rule (common)
    #       'O' Other rule (rare)
    # [10] 'shape_indicator' Shape indicator defined.
    #        Y shape defined (only value ever seen)
    #        N shape not defines (never seen)
    #
    # << values [11 - 14] are missing about 30% of the time >>
    #
    # [11] 'nfdc_id' NFDC airspace id
    # [12] 'nfdc_name' NFDC airspace name
    # [13] 'dafif_id' DAFIF airspace id
    # [14] 'dafif_name' DAFIF airspace name

    # Decode the valid_time and unique_value
    m = SUA_RE.match(textList[0])
    if m is None:
        raise ex.SuaException("Could not decode textList[0]: {}".format(text))

    startTimeIso = util.notamTimeToIso8601(rYear, textList[5])
    endTimeIso = util.notamTimeToIso8601(rYear, textList[6])

    scheduleId = m.group(2)

    newMsg['type'] = 'SUA'
    newMsg['unique_name'] = reportId
    newMsg['airspace_name'] = textList[4]
    newMsg['start_time'] = startTimeIso
    newMsg['end_time'] = endTimeIso
    newMsg['schedule_id'] = scheduleId
    newMsg['airspace_id'] = textList[1]
    newMsg['status'] = textList[2]
    newMsg['airspace_type'] = textList[3]
    newMsg['low_altitude'] = int(textList[7]) * 100
    newMsg['high_altitude'] = int(textList[8]) * 100    

    # Never see a blank separation rule, but change it to 'U'
    # (better value than ' ')
    if (textList[9] == '') or (textList[9] == ' '):
        textList[9] = 'U'

    newMsg['separation_rule'] = textList[9]
    newMsg['shape_defined'] = textList[10]

    # Entries [11 - 14] are either all there, or all missing
    if (textList[11] != ''):
        newMsg['nfdc_id'] = textList[11]
        newMsg['nfdc_name'] = textList[12]
        newMsg['dafif_id'] = textList[13]
        newMsg['dafif_name'] = textList[14]

    newMsg['expiration_time'] = endTimeIso

    return newMsg
