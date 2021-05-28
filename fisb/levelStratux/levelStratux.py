#!/usr/bin/env python3

"""LevelStratux reads messages from a Stratus box using the GDL 90 protocol and
outputs dump978 format data (without the time).

Given a port number (supplied in :mod:`fisb.levelStratux.levelStratuxConfig`),
we create an UDP server (not client) that Stratus will connect to (assuming
we have a DHCP lease from Stratux).
We use the GDL 90protocol to get type 7 messages from Stratux containing the
FIS-B data. We then turn the data back into dump978 format (Stratux uses 
dump978 for data acquisition), and dump it to the terminal.

Generally, is run with ``cfg.PRINT_ERRORS = False``, so any disconnects
and reconnects are silent. If it cannot connect, or if the
connection is dropped, will continually (after a small sleep)
try to reconnect.

If ``cfg.PRINT_ERRORS`` is ``True``, will print errors to ``sys.stderr``.
"""

import socket, sys, os, time

import fisb.levelStratux.levelStratuxConfig as cfg

def crcInit():
    """Create CRC table at start-up.

    Creates a table using the algorithm from 
    the `GDL 90 Data Interface Specification
    <https://www.faa.gov/nextgen/programs/adsb/Archival/media/GDL90_Public_ICD_RevA.PDF>`_.
    We store the 256 values the algorithm creates in a list that is used by
    :func:`crcCompute`.

    Returns:
        list:   256 element list with calculated CRC values used by :func:`crcCompute`.
    """
    result = []

    for i in range(0, 256):
        crc = (i << 8) & 0xffff
        for _ in range(0, 8):
            crcByte = 0
            if (crc & 0x8000) != 0:
                crcByte = 0x1021
            crc = (((crc << 1) & 0xffff) ^ crcByte)
            
        result.append(crc)
    
    return result

# crcList is a 256 element list holding helper values for crcCompute.
crc16List = crcInit()

def crcCompute(msgWithFlagsCrC):
    """Given a complete GDL 90 message, compute the CRC value and compare
    with the value in the current message. Return ``True`` if the CRC is correct,
    else ``False``.

    The CRC is computed only on the data in the message. The starting
    and ending ``0x7e`` flags and the CRC in the message are ignored.
    The existing CRC in ``msgWithFlagsCrc`` is used as a comparison value.

    Uses CRC algorithm from the
    `GDL 90 Data Interface Specification
    <https://www.faa.gov/nextgen/programs/adsb/Archival/media/GDL90_Public_ICD_RevA.PDF>`_.

    Args:
        msgWithFlagsCrc (bytestr): GDL message as received from Stratux. Includes flag values
            (``0x7e``) at both ends, and a 2 byte CRC value before the last flag
            value.

    Returns:
        bool:   ``True`` if the CRC check passes, else ``False``.
    """
    # Extract existing CRC in message.
    crcInMsg = (msgWithFlagsCrC[-2] << 8) | msgWithFlagsCrC[-3]
    
    # Remove flags and CRC from passed argument. CRC is only computed on the
    # data part.    
    msg = msgWithFlagsCrC[1:-3]
    msgLength = len(msg)
    crc = 0

    for i in range(0, msgLength):
        crc = crc16List[crc >> 8] ^ ((crc << 8) & 0xffff) ^ msg[i]
        crc = crc & 0xffff

    # Compare computed CRC with message CRC.
    if (crcInMsg != crc):
        return False

    return True

def getMyIpAddr():
    """Return my current external IP address as a string. Will return
    ``127.0.0.1`` if there is none. The address should be a DHCP address
    assigned by Statux (usually ``192.168.10.xx``). 

    Note: Stratux should be started before 'fisb-decode', since Stratux 
    provides message services only to machines that use it as a DHCP
    server.

    Returns:
        str: IP address. Should be ``192.168.10.xx``. Returns ``127.0.0.1`` if
            there is no external default route.
    """
    try:
        mySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mySocket.connect(('10.255.255.255', 1))
        myIpAddr = mySocket.getsockname()[0]

    except Exception:
        myIpAddr = '127.0.0.1'

    finally:
        mySocket.close()

    return myIpAddr

def connectToServer():
    """Start a UDP server and do not return until successful.

    Start a UDP server that Stratux will connect to and start sending 
    UDP messages to. If our IP address is the loopback address
    (``127.0.0.1``), will continue trying until we have an actual
    external address (usually ``192.168.10.xx``).

    If ``cfg.PRINT_ERRORS`` is ``True``, will print errors to
    ``sys.stderr``. Else will remain silent for exceptions.

    Returns:
        socket: Socket containing an open and working UDP server.
    """
    while True:
        # Connect to server and return socket. If not successful, 
        # keep trying.
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            myIpAddr = getMyIpAddr()

            if myIpAddr == '127.0.0.1':
                raise Exception('No routable Address')

            server_socket.bind( (myIpAddr, cfg.NETWORK_PORT) )

            return(server_socket)
        except Exception as ex:
            if cfg.PRINT_ERRORS:
                print(ex, file=sys.stderr)
            try:
                server_socket.close()
            except:
                pass
            time.sleep(5)

def processMessage(msg):
    """Process a GDL 90 message. Ignore all messages other than FIS-B. If the
    message is a FIS-B message, will print it to standard output.

    Messages must pass the following tests:

    * Is a type 7 GDL message.
    * Passes the CRC check.
    * Is the correct length for FIS-B.

    Args:
        msg (bytestr):  Contains GDL 90 message, possibly a FIS-B message.
    """
    # Message id 7 are the fis-b messages.
    if msg[1] != 7:
        return

    # Check for CRC error.
    if not crcCompute(msg):
        return

    # Bad length
    if len(msg) != 440:
        return

    # Convert into a dump978 format message and sent it out.
    fisb = '+' + msg[5:-3].hex() + ';rssi=-20.0'
    print(fisb, flush=True)

# States for processData's state machine.
INITIAL = 0
IN_MESSAGE = 1
ESCAPE_SEQUENCE = 2

def processData(newData, oldData, state):
    """Take data from Stratux and try to find complete messages to process.

    Any complete messages are sent to :func:`processMessage` for decoding.

    Note: Statux always sends complete message packets out of UDP. The most
    common reason for having an incomplete message is a large bolus of messages
    that exceeds buffer storage (happend with an 8k buffer, never with the current
    64k buffer). In this case, the incomplete message is never completed, and the
    message after the incomplete message will fail length criteria and be dropped.

    Args:
        newData (bytestr): New data received from Statux.
        oldData (bytestr): Any incomplete message from previous call.
        state (int): Previous state machnine value.

    Returns:
        tuple: Tuple:

        1. (bytestr) Partial data information from any incomplete message.
            If all messages were processed, will return ``b''``.
        2. (int) Current state machine value.
    """
    data = oldData + newData
    
    newMessage = b''
    i = -1

    # Loop until all of 'data' that can be processed, is processed.
    while True:
        i = i + 1

        lenData = len(data)

        # If lenData is 0, this means we have totally processed
        # the message (ie: the last part of the message was a 
        # complete message).
        if lenData == 0:
            return (b'', INITIAL)

        # If we reached the end of the data, this implies that we
        # have not completely processed a message. The remaining
        # part will be returned along with the current state.
        if i == lenData:
            return (data, state)        
        
        c = data[i]

        # Process state machine and change states as appropriate.
        if state == INITIAL:
            if c == 0x7e:
                state = IN_MESSAGE
                newMessage = c.to_bytes(1, byteorder='big')
        elif state == IN_MESSAGE:
            if c == 0x7d:
                # For reference: An escape sequence is used when you
                # want to send 0x7e or 0x7d. To do so, send 0x7d followed
                # by 0x7e or 0x7d XORed with 0x20. CRC is computed or
                # created before or after any escape sequences are applied
                # (i.e. on raw data).
                state = ESCAPE_SEQUENCE
            elif c == 0x7e:
                # special case where we start on the last 0x7e and
                # mistake it for the first.
                if len(newMessage) == 1:
                    newMessage = c.to_bytes(1, byteorder='big')
                    state = IN_MESSAGE
                else:
                    # Only process messages that have a chance of being valid.
                    # UDP drops can sometimes cause invalid messages.
                    if len(newMessage) > 5:
                        processMessage(newMessage + c.to_bytes(1, byteorder='big'))

                    # Start a new message. Use the remaining part of 'data' to
                    # look for more messages.
                    state = INITIAL
                    newMessage = b''
                    data = data[i+1:]
                    i = -1
            else:
                newMessage = newMessage + c.to_bytes(1, byteorder='big')
        elif state == ESCAPE_SEQUENCE:
            c = c ^ 0x20
            newMessage = newMessage + c.to_bytes(1, byteorder='big')
            state = IN_MESSAGE            

def mainLoop():
    """Loops forever reading data from Stratux client or attempting reconnect.

    Creates a UDP server and waits for a connection from Stratux. Will attempt
    to restart the server for any problems. After the server is started
    and Stratux connects, will process any data from Stratux.
    
    Will never exit unless terminated.

    If ``cfg.PRINT_ERRORS`` is ``True``, will print errors to
    ``sys.stderr``. Else will remain silent for exceptions.
    """
    connected = False

    # Values needed for processData()
    oldData = b''
    state = INITIAL

    try:
        while True:
            # Connect if not connected
            if not connected:
                server_socket = connectToServer()
                connected = True

            # Get data from client. Large buffer helps
            # since large blobs (>16k) will be sent
            # occasionally. A large value here will decrease lost
            # UDP packets. Tried an initial value here of 8192
            # and that was not big enough. 64k seemed to not have
            # any issues.
            # Note: The number of bytes does not mean that this call
            # will wait until the buffer is full. It will return 
            # whatever data it has and will wait until it has some
            # data (i.e. it doesn't go into a hard loop).
            data, _ = server_socket.recvfrom(65536)

            # Take data and process it. We store any incomplete
            # messages in 'oldData', and the current state machine
            # internal value in 'state'.
            oldData, state = processData(data, oldData, state)

    except Exception as ex:
        if cfg.PRINT_ERRORS:
            print(ex, file=sys.stderr)
        
        # Assume not connected for any errors.
        connected = False

        try:            
            server_socket.close()
        except:
            pass

        time.sleep(3)

if __name__ == "__main__":
    mainLoop()
