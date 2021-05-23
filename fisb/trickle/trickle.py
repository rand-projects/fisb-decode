#!/usr/bin/env python3

"""Process raw messages and dispatch them in real time.

Trickle is a program that takes a file consisting of raw hex data like that
produced by ``dump978`` and outputs them to standard output at the same
rate that they were received. For example, if the file has 3 messages every
second, but then skips two seconds, the output will mimic the exact same
behavior. Trickle simulates the message timing of the original message stream.

The main purpose of Trickle is to simulate the real time flow of messages
recorded in the past. This is primarily used along with Harvest to run the
various test group files.

The basic flow of Trickle is to open the file containing the messages and
read the first message. This message will have the timestamp of when it
was originally received. This initial timestamp gets a small interval 
subtracted from it (so the time is set to a few seconds before the time the actual
message would have arrived). Then the difference between the actual time
and the simulated time is computed (this gives Harvest some time to get ready).
This difference is then written to
a file usually called ``sync.fisb``. The ``sync.fisb`` file is read by Harvest
which uses it to set its clock back to the same time. Harvest is then
acting like it was receiving the messages in real time, but at the time
the messages were originally sent.

After the first message, Trickle will send the messages out at the times
they were sent out in the past, allowing for any delays in message arrival.

Trickle exits when all messages have been read.
"""

import os, io, sys, json, argparse, time

import fisb.trickle.trickleConfig as cfg

def getMsgTime(line):
    """Parse the timestamp off the 978 message and return as a float.

        Args:
            line (str): Line containing a 978 message with a timestamp at the end.

        Returns:
            float: Timestamp of the message.

        Raises:
            Exception: If the timestamp can't be found.
    """
    payloadTimeIndex = line.find(';t=')

    if payloadTimeIndex == -1:
        raise Exception('Illegal time format')

    timeInSecs = float(line[payloadTimeIndex + 3:-1])

    return timeInSecs

def waitTillTime(msgTime, syncDiff):
    """Calculate how long to wait until the next message is due to be sent. Then sleep that long.

    Args:
        msgTime (int): Received time of the next message
        syncDiff (float): Time between message time and actual time.
    """
    timeToWait = msgTime - (time.time() - syncDiff)
    if timeToWait > 0:
        time.sleep(timeToWait)

if __name__ == "__main__":
    #----------------------------------------------------------------------------#
    # M A I N   C O D E   B L O C K
    #----------------------------------------------------------------------------#

    parser = argparse.ArgumentParser(description= \
                                     """
                                     Take dump978 messages and dispatch in real time
                                     """)
    parser.add_argument('filename', help='filename to take input from')
    args = parser.parse_args()

    
    inStream = io.TextIOWrapper(sys.stdin.buffer, encoding='ISO-8859-1')

    syncFilePath = os.path.join(cfg.SYNC_DIRECTORY, 'sync.fisb')

    # Do special things for the first message
    isFirstMessage = True
    
    try:
        with open(args.filename, 'r', encoding='ISO-8859-1') as file:
            for _, line in enumerate(file):
                line = line.strip()

                # Note: this will skip comments and blank lines (or lines
                # that don't start with a '+')
                if len(line) == 0:
                    continue
                elif line[0] == '#':
                    continue
                elif line[0] == '+':
                    # parse off time
                    msgTime = getMsgTime(line)

                    if isFirstMessage:
                        # Get sync difference
                        syncDiff = time.time() - (msgTime - float(cfg.INITIAL_DELAY))

                        # Write sync file and delay
                        with open(syncFilePath, 'w') as f:
                            f.write(str(syncDiff) + '\n')
                        isFirstMessage = False

                waitTillTime(msgTime, syncDiff)
                print(line, flush=True)

    except KeyboardInterrupt:
        # Capture interrupt so we can still erase sync file
        pass
    
    # Remove sync file if exists (harvest should have removed it)
    if os.path.isfile(syncFilePath):
        os.remove(syncFilePath)
