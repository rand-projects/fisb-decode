"""LocalWx configuration information.

Change these settings to display weather from the locations you 
are interested in.
"""

#: MONGO URL
MONGO_URL = 'mongodb://localhost:27017/'

#: List of WIND forecasts you want to get.
WINDS_LIST = ['IND']

#: List of current METARS you want displayed
METAR_LIST = ['KIND', 'KTYQ', 'KEYE']

#: List of terminal area forecasts to display.
TAF_LIST = ['KIND']

#: List of sites you want NOTAMs from.
NOTAM_LIST = ['KTYQ', 'KEYE', 'KIND', 'KI99']

#: Your lat, long. Used to determine if you are in SIGMETS, AIRMET, CWA, etc.
#: Configured as a tuple: ``(<longitude>, <latitude>)``.
MY_LOC = (-86.255593, 40.0383)
