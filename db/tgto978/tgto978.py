#!/usr/bin/env python3

"""tgto978 converts standard test data to 978 format for consumption by fisb-decode.

Test group data from the standard body will get placed in
``fisb-decode/tg/tg-source/imported/TGxx`` where ``xx`` is a
number from ``01`` to ``27``. Each of these directories will have a
file ``TestGroupxx Stimulus.csv``. It will also have a ``/bin`` directory
which contains multiple files with each file containing a 432 byte packet.

The *stimulus* file contains one line per packet file as well as the time
in seconds after midnight of the start date that the packet should arrive.
In most cases the date is not specified, in some cases it is. In one case it
was in the future at the time it was released.

Fisb-decode provides a start date file in 
``fisb-decode/tg/triggers/start-dates.csv``.

What ``tgto978`` goes is to take a start date, a set of packet data, and the
times those packets should be sent and turns them into regular hex packets
with the correct date appended just like ``dump978-fa`` would produce. These
files are placed in the ``fisb-decode/tg/tg-source/generated`` folder.
"""

import sys, os, json, time, traceback, glob
import dateutil.parser, curses, textwrap
from datetime import datetime, timezone, timedelta
import csv
import binascii

import db.tgto978.tgto978Config as cfg

# Dictionary holding start dates for each TG
tg_ymd = {}

def createTime(tgNum, secs):
    """Create a ``datetime`` object which is a timestamp for
    when a message should arrive. This is the start date with
    the number of seconds added.

    Args:
        tgNum (int): Test group number.
        secs (int): Seconds after midnight at the date the test was started.

    Returns:
        datetime: Datetime object holding the date/time a message should arrive.
    """
    y = tg_ymd[tgNum][0]
    m = tg_ymd[tgNum][1]
    d = tg_ymd[tgNum][2]

    t = datetime(y, m, d, 0, 0, 0, tzinfo=timezone.utc)
    t = t + timedelta(0, secs)

    return t.timestamp()

def makeStartDateDict():
    """Create the global ``tg_ymd`` dictionary which holds the start
    dates for each test group.

    Reads the start date file and for each test group stores the
    test group number as the key and a list holding the year, month,
    and day as its value. 

    Stored in the global ``tg_ymd``.
    """
    global tg_ymd

    with open(cfg.TG_START_DATES, newline='') as csvfile:
        csvReader = csv.reader(csvfile, delimiter=',')
        for row in csvReader:
            tg_ymd[int(row[0])] = [int(row[1]), int(row[2]), int(row[3])]
    
def tgto978():
    """Transform standard test group data to compatible fisb-decode data.
    """
    print('Converting TG data. Please wait...')
    makeStartDateDict()
    
    for tgNum in range(1,28):
        # Holds tgNum as 2 character leading 0 string
        tgStr = '{:02d}'.format(tgNum)

        outPath = os.path.join(cfg.TG_OUT_DIR, \
            'tg' + tgStr + '.978')
        outFile = open(outPath, 'w') 

        stimulusPath = os.path.join(cfg.TG_IN_DIR, \
            'TG' + tgStr, \
            'TestGroup' + tgStr + ' Stimulus.csv')

        with open(stimulusPath, newline='') as csvfile:
            # Interval to use for messages sent at the same time
            oldSecs = -1
            secsInARow = 0
            
            csvReader = csv.reader(csvfile, delimiter=',')
            next(csvReader) # skip header
            for row in csvReader:
                file = row[0]
                secs = int(row[1])
                
                if secs != oldSecs:
                    oldSecs = secs
                    secsInARow = 0
                else:
                    secsInARow += 1

                # Real FIS-B messages start at 6ms and go until 176 + 6ms.
                secs = secs + 0.006 + (secsInARow * 0.005)                

                filePath = os.path.join(cfg.TG_IN_DIR, \
                    'TG' + tgStr, \
                    'bin', \
                    file + '.bin')

                with open(filePath, 'rb') as binFile:
                    data = bytes.hex(binFile.read())
                    t = createTime(tgNum, secs)
                    outFile.write('+{};rs=24;rssi=-8.6;t={:.3f};\n'.format(data, t))
        
        outFile.close()

if __name__ == "__main__":

    # Call tgto978
    tgto978()
