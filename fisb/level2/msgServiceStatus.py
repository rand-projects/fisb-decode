"""Decode and create messages from Service Status Frames (type 15).

Service status frames show which aircraft are being provided 
TIS-B 'hockey pucks' by a particular ground station. Be aware
that it doesn't always produce the same aircraft each time it
sends out a message. It sometimes splits the aircraft accross
messages. So if you are keeping track of this you need to
keep a pool of aircraft as a separate task.

Each aircraft being followed is represented by the hex code
of its 24-bit ICAO address.

Produces the 'SERVICE_STATUS' message. The unique name for the message
is the station who sent the message.

See Doc 9861 AN/460 ‘Manual on the Universal Access Transceiver (UAT)’
for details on how the service status works. DO-317 is probably the
better place to look, but I don't have access to it. See
also 'SRT-047 Rev 01 (2011) section 3.3.4.1.2'.
"""

import sys, os, json, time, re

import fisb.level2.level2Config as cfg
import fisb.level2.utilities as util
import fisb.level2.level2Exceptions as ex

# Address qualifier list. They get appended if they are not 0 (99.9999%) are.
# The only non-zero one seen is 1 (Self-Assigned address).
ADDR_QUALIFIER_TYPES = ['', '/1', '/2', '/3', '/4', \
                        '/5', '/6', '/7']

def msgServiceStatus(rcvdTime, frame, station):
    """Process Service Status messages.
    
    Args:
        rcvdTime (str): ISO time the message was received.
            Used for calculating the expiration time.
        frame (dict): Type 15 frame.
        station (str): Ground station ID.

    Returns:
        dict: Dictionary with completed message.
    """
    newMsg = {}

    newMsg['type'] = 'SERVICE_STATUS'

    # Service status messages are sent for each aircraft being
    # followed every 20 seconds. However, subsequent messages
    # may not contain the same aircraft. When handling this message
    # for a database, each aircraft should be assigned the expiration
    # time for the message, and aircraft should be combined into
    # one pool.

    newMsg['unique_name'] = station

    contentsList = frame['contents']

    trafficList = []

    for plane in contentsList:
        icao = plane['address']
        icao = icao + ADDR_QUALIFIER_TYPES[plane['address_type']]
    
        trafficList.append(icao)

    newMsg['traffic'] = trafficList
    newMsg['no_msg_digest'] = 't'
    newMsg['expiration_time'] = util.addSecondsToIso8601(rcvdTime, \
            cfg.SERVICE_STATUS_EXPIRATION_SECONDS)
    
    return newMsg
