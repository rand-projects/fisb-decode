#!/usr/bin/env python3

"""Convert pretty printed json to non-pretty printed json.
"""
import sys, os

def pp2nopp():
    """Convert multi-line json to single line json.
    """
    outStr = ''
    for line in sys.stdin:
        if (len(line) > 0) and (line[0] == '#'):
            continue
        line = line.rstrip()

        if line == '{':
            outStr = '{'
        elif line == '}':
            outStr = outStr + '}'
            print(outStr)
        else:
            outStr = outStr + line.strip()

if __name__ == "__main__":
    ## --- Script Code ---##
    pp2nopp()
