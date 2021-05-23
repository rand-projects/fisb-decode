#!/usr/bin/env python3

"""Convert single-line json (non-pretty-printed) to pretty-printed json.

"""
import sys, os, json, time, argparse, traceback, hashlib

def nopp2pp(msg, ppIndent):
    """Convert single-line json to multi-line json.

    Args:
        msg (str): JSON string of the message.
        ppIndent (int): Number of characters to indent for pretty printing.
    """
    msg = json.loads(msg)
    msgJson = json.dumps(msg, indent = ppIndent)
    print(msgJson, flush=True)

if __name__ == "__main__":
    ## --- Script Code ---##

    # Main loop
    for line in sys.stdin:
        line = line.strip()

        if (len(line) > 0) and (line[0] == '#'):
            continue

        nopp2pp(line, 2)
