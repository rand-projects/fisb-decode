"""Module containing harvest utility functions.
"""

import sys, os, time, random
from datetime import timezone, datetime

CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

CHARS_LEN_MINUS_1 = len(CHARS) - 1

def randomname(length, postfix = ''):
    name = ''
    for _ in range(0, length):
        name += CHARS[random.randint(0, CHARS_LEN_MINUS_1)]
    
    return name + postfix
