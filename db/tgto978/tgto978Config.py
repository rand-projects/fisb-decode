"""tgto978 Convert Test Group data to .978 format.
"""

#: Where to find the start dates for each TG.
TG_START_DATES = '../tg/triggers/start-dates.csv'

#: Where to find the TG data. Assumes each TG is a subdirectory
#: of this directory with a name like ``TG<nn>`` (i.e. ``TG01``). Under
#: that directory is a ``/bin`` subdirectory and a csv file with
#: the timing data.
TG_IN_DIR = '../tg/tg-source/imported'

#: Where the .978 files will be placed. Files 
#: in this directory will have names like ``TG01.978``.
TG_OUT_DIR = '../tg/tg-source/generated'
