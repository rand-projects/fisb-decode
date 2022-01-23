#!/usr/bin/env python3

"""LocalWx produces a local text wx report using the Harvest mongo database.

Produces a set of local weather printed out the the terminal for a set of
locations defined in :mod:`db.localwx.localwxConfig`.

Program usage: ::

    usage: localwx.py [-h] [--fdc] [--airmet] [--nogairmet] [--nowinds] [--nonotam]
                      [--nounavail] [--ad] [--obst] [--all] [--curses]

    Display local weather from database.
    
    For curses mode, the following keys are used (either upper or lower case):
     q - Quit
     a - Toggle AIRMETs (Will show SIGMET/WST, CWA)
     d - Toggle aerodrome (AD) NOTAMS
     f - Toggle FDC NOTAMS 
     g - Toggle G-AIRMETS
     m - Toggle METARs
     n - Toggle NOTAMS
     o - Toggle NOTAM obstructions
     s - Toggle all AIRMETs (SIGMET/WST, CWA, AIRMETs)
     t - Toggle TAFS
     u - Toggle FIS-B Unavailable messages
     w - Toggle Wind

    <space> will update screen
 

    optional arguments:
      -h, --help   show this help message and exit
      --fdc        Show FDC NOTAMS
      --airmet     Show AIRMETs (will show CWA, SIGMET/WST)
      --nogairmet  Don't show G-AIRMET forecasts
      --nowinds    Don't show wind forecast
      --nonotam    Don't show any NOTAMS
      --nounavail  Don't show any FIS-B Unavailable notices
      --obst       Show NOTAM obstructions
      --all        Show everything
      --curses     Show on updating display

Sample output: ::

    METAR KIND 110454Z 03006KT 10SM SCT060 OVC110 11/06 A3016 RMK AO2 SLP213
         T01060061 401670011=
    METAR KTYQ 110515Z AUTO 04004KT 10SM SCT044 BKN055 OVC065 09/08 A3017
         RMK AO2 T00850076=
    METAR KEYE 110453Z AUTO 01007KT 10SM BKN055 BKN075 OVC090 10/07
        A3016 RMK AO2 RAE00 SLP214 P0000 T01000067 401670011=

    TAF KIND 110525Z 1106/1212 01009KT P6SM BKN070
         FM111100 02007KT P6SM BKN045
         FM111200 02006KT P6SM SCT070=

    WINDS IND   FT   3000    6000    9000   12000   18000   24000  30000  34000  39000
    06 11/02-11/09   2909 2717+00 2720-06 2825-12 2862-20 2770-33 781144 772549 780252
    12 11/09-11/18   0319 2919+00 2925-06 2835-12 2865-21 2886-32 782346 782051 771356
    24 11/18-12/06   0116 3615-03 3519-06 3128-10 2859-20 2885-29 773242 774951 783557

    !HUF 04/093 TYQ RWY 18/36 WIP MOWING ADJ TUE-THU 1130-2100 2104131130-2110282100
    !EYE 05/003 EYE NAV ILS RWY 21 LOC U/S 2105110153-2105182000EST
    !EYE 05/002 EYE NAV ILS RWY 21 LOC U/S 2105071535-2105112000EST
    !IND 05/006 IND TWY A2, A4, A5, A7, A11, A12, B2, B5 2105031454-2105292100

    G-AIRMET
    00 11/03-11/06 TURB (24000-38000 MSL)
    00 11/03-11/06 ICING (4000-13000 MSL)
    03 11/06-11/09 TURB (24000-38000 MSL)
    03 11/06-11/09 ICING (4000-13000 MSL)
    06 11/09-11/12 TURB (24000-39000 MSL)
    06 11/09-11/12 ICING (4000-13000 MSL)
"""

import sys, os, json, time, argparse, traceback, glob
import dateutil.parser, curses, textwrap, pprint
from argparse import RawTextHelpFormatter
from curses import wrapper
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo import errors
from bson.objectid import ObjectId
from shapely.geometry import Point
from shapely.geometry import Polygon

import db.localwx.localwxConfig as cfg

SHOW_FDC = False
SHOW_ALL_AIRMETS = True
SHOW_AIRMET = False
SHOW_G_AIRMET = True
SHOW_WINDS = True
SHOW_NOTAMS = True
SHOW_OBST = False
SHOW_AD = True
SHOW_METAR = True
SHOW_TAF = True
SHOW_UNAVAILABLE = True
USE_CURSES = False

CRL_TYPES = ['CRL_11', 'CRL_12', 'CRL_14', 'CRL_15', \
    'CRL_16', 'CRL_17', 'CRL_8']

# Get items to display from configuration
mongoUri = cfg.MONGO_URI
WINDS_LIST = cfg.WINDS_LIST
METAR_LIST = cfg.METAR_LIST
TAF_LIST = cfg.TAF_LIST
NOTAM_LIST = cfg.NOTAM_LIST
MY_LOC = Point(cfg.MY_LOC[0], cfg.MY_LOC[1])

def pullPolygonFromFisB(dict):
    """If a message has a polygon, return its coordinates.

    Args:
        dict (dict): Message dictionary.

    Returns:
        tuple: Tuple:

        1. object: :class:`shapely.geometry.Polygon` object containing coordinates.
        2. str: Altitude type (``MSL`` or ``AGL``)
        3. int: Low altitude.
        4. int: High altitude.

        If this message doesn't match, will return the tuple:
        ``(None, '', 0, 0)``.
    """
    if ('geojson') not in dict:
        return (None, '', 0, 0)

    # Note: This will only get the first object even if there
    # is more than 1.
    geoDict = dict['geojson']['features'][0]

    if ('type' not in geoDict['geometry']) or \
        ('coordinates' not in geoDict['geometry']):
        return (None, '', 0, 0)

    if geoDict['geometry']['type'] != 'Polygon':
        return (None, '', 0, 0)

    altitudeType = geoDict['properties']['altitudes'][1]
    altitudeHigh = geoDict['properties']['altitudes'][0]
    altitudeLow = geoDict['properties']['altitudes'][2]

    coordList = geoDict['geometry']['coordinates']

    if coordList == None:
        return (None, '', 0, 0)
    
    # Now we have an actual list, turn into list for Polygon
    polyList = []
    
    for x in coordList:
        polyList.append((x[0], x[1]))

    return (Polygon(polyList), altitudeType, altitudeLow, altitudeHigh)

def forecastTimes(hrStr, d):
    """For wind forecast, create a string showing which forecase this is and valid times.

    Args:
        hrStr (str): String with hour of forecast (one of ``06``, ``12``, ``24``)
        d (dict): Wind message.

    Returns:
        str: String with winds times. Example ``06 11/02-11/09``.
    """
    dtFrom = d['for_use_from_time']
    dtTo = d['for_use_to_time']
    timeStr = '{} {:02d}/{:02d}-{:02d}/{:02d}'.format(hrStr, \
        dtFrom.day, dtFrom.hour, dtTo.day, dtTo.hour)
    return timeStr

def createAltitudeStr(altitudeLow, altitudeHigh, altitudeType):
    """Create a string out of a low altitude, high altitude, and altitude type.
    
    Return value will look something like: ``8000-20000 MSL``. If the
    low altitude is 0, it will be noted as ``SFC``.

    Args:
        altitudeLow (int): Low altitude.
        altitudeHigh (int): High altitude.
        altitudeType (str): Altitude type. One of ``AGL`` or ``MSL``.

    Returns:
        str: Altitude string as described above.
    """
    if altitudeLow == altitudeHigh:
        if altitudeLow == 0:
            return 'SFC'
        
        return str(altitudeLow) + ' ' + altitudeType

    lowStr = str(altitudeLow)
    if altitudeLow == 0:
        lowStr = 'SFC'

    return lowStr + '-' + str(altitudeHigh) + ' ' + altitudeType

def gAirmet(db):
    """Create G-AIRMET forecast string.

    Will only add a G-AIRMET if ``cfg.MY_LOC`` is inside of the G-AIRMET's
    polygon.

    Args:
        db (object): Handle to database connection.
    
    Returns:
        str: Containing G-AIRMET forecast.
    """
    if SHOW_G_AIRMET == False:
        return ''

    forecastStr = ''
    for r in db.MSG.find({'type': 'G_AIRMET', 'geojson.features.geometry.type': 'Polygon'}).sort('subtype', 1):
        poly, altitudeType, altitudeLow, altitudeHigh = pullPolygonFromFisB(r)

        if poly is None:
            continue

        if poly.contains(MY_LOC):
            hrStr = '{:02d}'.format(r['subtype'])  # 00, 03, 06
            timeStr = forecastTimes(hrStr, r)
            element = r['geojson']['features'][0]['properties']['element']
            conditionsStr = ''
            if 'conditions' in r['geojson']['features'][0]['properties']:
                conditions = r['geojson']['features'][0]['properties']['conditions']
                conditionsStr = ' [' + ', '.join(conditions) + ']'

            altitudeStr = createAltitudeStr(altitudeLow, altitudeHigh, altitudeType)
            fStr = '{} {}{} ({})'.format(timeStr,element, \
                conditionsStr, altitudeStr)
            forecastStr = forecastStr + fStr + '\n'
    
    if forecastStr != '':
        forecastStr = '\nG-AIRMET\n' + forecastStr
    
    return forecastStr

def fisbUnavailable(db):
    """Create string containing any FIS-B Unavailable messages.

    Args:
        db (object): Handle to database connection.
    
    Returns:
        str: Containing any FIS-B Unavailable information.
    """
    if SHOW_UNAVAILABLE == False:
        return ''

    fisbStr = ''

    for r in db.MSG.find({'type': 'FIS_B_UNAVAILABLE'},{'contents': 1, 'centers': 1}):
        centerList = ','.join(r['centers'])
        centerStr = ' [' + centerList + ']'
        
        fisbEntry = r['contents'] + centerStr
        fisbStr = fisbStr + textwrap.fill(fisbEntry, 78, subsequent_indent='     ') + '\n'
        
    if fisbStr != '':
        fisbStr = '\n' + fisbStr
        
    return fisbStr
    
def findSigWx(db):
    """Create string containing any AIRMET, SIGMET/WST,  or CWA reports.

    AIRMETs are optionally shown based on parameters at runtime.

    ``cfg.MY_LOC`` must be inside the polygon to be listed.

    Args:
        db (object): Handle to database connection.
    
    Returns:
        str: Containing any pertinent AIRMET, SIGMET/WST, or CWA reports.
    """
    if SHOW_ALL_AIRMETS == False:
        return ''

    wxStr = ''

    for r in db.MSG.find({'$or': [ {'type': 'AIRMET'}, {'type': 'SIGMET'}, \
        {'type': 'CWA'} ]}, \
        {'contents': 1, 'type': 1, 'issued_time': 1, 'geojson':1}).sort('issued_time', -1):

        if (SHOW_AIRMET == False) and (r['type'] == 'AIRMET'):
            continue

        poly, _, _, _ = pullPolygonFromFisB(r)

        if poly != None:
            if poly.contains(MY_LOC):
                wxStr = wxStr + r['contents'] + '\n\n'

    if wxStr != '':
        wxStr = '\n' + wxStr
    
    return wxStr

def showWinds(hrStr, d):
    """Produce winds forecast string.

    Args:
        hrStr (str): String with hour of forecast (one of ``06``, ``12``, ``24``)
        d (dict): Winds message to use.

    Returns:
        str: String containing single 6, 12, or 24 hour wind forecast.
    """
    return '{}{}\n'.format(forecastTimes(hrStr, d), d['contents'])
    
def winds(db):
    """Create string containing 6, 12, and 24 hour forecasts.

    Args:
        db (object): Handle to database connection.
    
    Returns:
        str: String containing any 6, 12, and 24 hour wind forecasts.
    """
    windResult = ''

    if SHOW_WINDS == False:
        return ''

    for windsLoc in WINDS_LIST:

        windHeader = 'WINDS ' + windsLoc + \
            '   FT   3000    6000    9000   12000   18000   24000  30000  34000  39000\n'
        windStr = ''

        x = db.MSG.find_one({'_id': 'WINDS_06_HR-' + windsLoc})
        if x is not None:
            windStr = windStr + showWinds('06', x)

        x = db.MSG.find_one({'_id': 'WINDS_12_HR-' + windsLoc})
        if x is not None:
            windStr = windStr + showWinds('12', x)

        x = db.MSG.find_one({'_id': 'WINDS_24_HR-' + windsLoc})
        if x is not None:
            windStr = windStr + showWinds('24', x)
    
        if windStr != '':
            windResult = windResult + '\n' + windHeader + windStr

    return windResult

def metars(db):
    """Create string containing all desired METAR forecasts.

    Args:
        db (object): Handle to database connection.
    
    Returns:
        str: String with METAR forecasts.
    """
    if not SHOW_METAR:
        return ''

    metarStr = ''

    for x in METAR_LIST:
        r = db.MSG.find_one({'_id': 'METAR-' + x},{'contents': 1, '_id': 0})
        
        if r is not None:
            metarStr = metarStr + r['contents'] + '\n'
    
    if metarStr != '':
        metarStr = '\n' + metarStr

    return metarStr

def isCrlStatusComplete(db):
    """Looks at all CRL tables and returns ``True`` if all CRLs are complete.

    Args:
        db (object): Database connection.

    Returns:
        bool: ``True if all CRLs are complete, else ``False``.
    """
    for x in CRL_TYPES:
        r = db.MSG.find_one({'type': x},{'reports': 1, 'overflow': 1})

        if r is None:
            return False  # no entry

        # check for the rare overflow
        if r['overflow'] == 1:
            return False

        reports = r['reports']

        # No entries counts as complete
        if len(reports) == 0:
            continue

        # Look at each report and make sure it is present
        # If no '*', return False, not complete.
        for y in reports:
            if '*' not in y:
                return False

    # Dropping out the bottom means all reports complete.
    return True

def serviceStatus(db):
    """Return a string showing the number of TIS-B targets and current RSR.

    String has the format ``(xT y%)`` where '``x``' is the number of TIS-B
    targets, and '``y``' is the RSR percentage. If either is missing no value
    will be shown. If both are missing, the empty string is returned.

    Args:
        db (object): Database connection.

    Returns:
        str: String with TIS-B and RSR data.
    """
    tisbTargets = 0
    rsr = -1

    # Get the number of TIS-B targets
    for r in db.MSG.find({'type': 'SERVICE_STATUS'},{'traffic': 1}):
        tisbTargets = len(r['traffic'])

    # Get the current RSR
    r = db.MSG.find_one({'_id': 'RSR-RSR'},{'stations': 1})
    # only worry about one entry (we are assuming ground use here).
    if r is not None:
        for x in r['stations']:
            rsr = r['stations'][x][2] # Percentage RSR
            break
            
    tisbStr = ''
    if tisbTargets > 0:
        tisbStr = '({}T'.format(tisbTargets)
        
    rsrStr = ''
    if rsr != -1:
        rsrStr = '{}%)'.format(rsr)

    if len(tisbStr) == 0:
        if len(rsrStr) == 0:
            returnStr = ''
        else:
            returnStr = '(' + rsrStr
    else:
        if len(rsrStr) == 0:
            returnStr = tisbStr + ')'
        else:
            returnStr = tisbStr + ' ' + rsrStr

    return returnStr

def tafs(db):
    """Create string containing all desired TAF forecasts.

    Args:
        db (object): Handle to database connection.
    
    Returns:
        str: String with TAF forecasts.
    """    
    if not SHOW_TAF:
        return ''

    tafStr = ''

    for x in TAF_LIST:
        r = db.MSG.find_one({'_id': 'TAF-' + x},{'contents': 1, '_id': 0})
        
        if r is not None:
            tafStr = tafStr + r['contents'] + '\n'
    
    if tafStr != '':
        tafStr = '\n' + tafStr

    return tafStr

def notams(db):
    """Create string containing all desired NOTAMS.

    Args:
        db (object): Handle to database connection.
    
    Returns:
        str: String with NOTAMS.
    """    
    notamStr = ''
    if SHOW_NOTAMS:
        for x in NOTAM_LIST:
            for r in db.MSG.find({'type': 'NOTAM', 'location': x}, \
                {'contents': 1, 'keyword': 1, 'subtype': 1, \
                    'number': 1, '_id': 1}).sort('number', -1):

                if (r['keyword'] == 'OBST') and not SHOW_OBST:
                    continue
                if (r['subtype'] == 'FDC') and not SHOW_FDC:
                    continue
                if (r['subtype'] == 'AD') and not SHOW_AD:
                    continue                

                # Insert spaces after new lines in NOTAMS (usually affects FDC NOTAMS)
                addedSpaces = r['contents'].replace('\n','\n                    ')
                notamStr = notamStr + addedSpaces + '\n'
    
    if notamStr != '':
        notamStr = '\n' + notamStr

    return notamStr

def myWx(db):
    """Create string with entire weather contents.

    Args:
        db (object): Database connection.

    Returns:
        str: Entire report with each line separated by newlines.
    """
    screenStr = fisbUnavailable(db) + metars(db) + tafs(db) + winds(db) + notams(db) + \
        gAirmet(db) + findSigWx(db)

    # Get rid of any starting \n (rare case in curses where
    # no metar shown)
    if (screenStr != '') and (screenStr[0] == '\n'):
        screenStr = screenStr[1:]

    return screenStr

def myWxCurses(db, rows, cols):
    """Create the screen contents to display. 

    Calls :func:`myWx` and splits up the lines, truncating as
    needed to fit the available screen space.

    Args:
        db (object): Database connection.
        rows (int): Number of rows on the screen.
        cols (int): Number of columns on the screen.

    Returns:
        str: Weather report as a string truncated for the number
        of rows and columns. Does not include bottom line.
    """
    curRow = 0
    cursesWxStr = ''
    
    for line in myWx(db).splitlines():
        if len(line) > cols:
            line = line[0:cols - 1]
        if curRow != 0:
            cursesWxStr += '\n'
        cursesWxStr += line
        curRow += 1
        if curRow == rows:
            break

    return cursesWxStr

def createBottomLine(cols, tisbStr, crlStatusComplete):
    """Create bottom line of curses display.

    Args:
        cols (int): Width of display in columns.
        tisbStr (str): Empty or contains a string of the form ``xT`` where
            ``x`` is the number of TIS-B targets being provided by this 
            station. Only a single station is used (this is meant to be
            used on the ground).
        crlStatusComplete (bool): If ``True`` add '``*``' to the
            beginning of the line.
    
    Returns:
        str: String contents of the bottom line.
    """
    str = ''

    if SHOW_METAR:
        str += '+(M)ETAR '
    else:
        str += '-(M)ETAR '

    if SHOW_TAF:
        str += '+(T)AF '
    else:
        str += '-(T)AF '

    if SHOW_WINDS:
        str += '+(W)IND '
    else:
        str += '-(W)IND '

    if SHOW_NOTAMS:
        str += '+(N)OTAM '
    else:
        str += '-(N)OTAM '

    if SHOW_FDC:
        str += '+(F)DC '
    else:
        str += '-(F)DC '

    if SHOW_OBST:
        str += '+(O)BST '
    else:
        str += '-(O)BST '

    if SHOW_G_AIRMET:
        str += '+(G)AIR '
    else:
        str += '-(G)AIR '

    if SHOW_AIRMET:
        str += '+(A)IR '
    else:
        str += '-(A)IR '

    if SHOW_ALL_AIRMETS:
        str += '+(S)IG '
    else:
        str += '-(S)IG '

    if SHOW_UNAVAILABLE:
        str += '+(U)NAVAIL'
    else:
        str += '-(U)NAVAIL'

    if tisbStr != '':
        str += ' ' + tisbStr

    if crlStatusComplete:
        str = '* ' + str

    str = str.ljust(cols - 1)

    # In case screen smaller
    str = str[0:cols - 1]

    return str

def refreshScreen(db, scr):
    """Create a new report and refresh the screen with updated contents.
    
    Args:
        db (object): Database connection.
        scr (object): Curses screen object.
    """
    rows, cols = scr.getmaxyx()
    scr.erase()
    scr.addstr(0, 0, myWxCurses(db, rows - 1, cols))

    bottomLine = createBottomLine(cols, serviceStatus(db), \
        isCrlStatusComplete(db))
    scr.addstr(rows - 1, 0, bottomLine, curses.A_REVERSE)

    scr.refresh()

def cursesDisplay(db):
    """Initialize curses display, then continually update report.

    Basic operation is to produce the report, then refresh the screen
    every 30 seconds unless the user types a command.

    When the user exits by '``q``' or '``^C``', reset the terminal to
    normal operation.

    Args:
        db (object): Database connection.
    """
    global SHOW_FDC, SHOW_AIRMET, SHOW_G_AIRMET, SHOW_WINDS, \
        SHOW_NOTAMS, SHOW_TAF, SHOW_METAR, SHOW_ALL_AIRMETS, \
        SHOW_OBST, SHOW_AD, SHOW_UNAVAILABLE
    
    scr = curses.initscr()
    scr.clear()
    curses.noecho()
    curses.cbreak()
    scr.keypad(True)
    scr.nodelay(True)
    rows, cols = scr.getmaxyx()

    try:
        while True:
            refreshScreen(db, scr)

            # 120 intervals with 1/4 character checks = refresh every 30 seconds.
            for _ in range(0,120):
                if curses.is_term_resized(rows, cols):
                    # Screen resize event
                    rows, cols = scr.getmaxyx()
                    curses.resizeterm(rows, cols)
                    refreshScreen(db, scr)

                x = scr.getch()

                if x in [81, 81+32]: # q Quit
                    curses.nocbreak()
                    scr.keypad(False)
                    curses.echo()
                    curses.endwin()
                    return
                elif x == 32: # SPACE
                    # Refresh screen immediately
                    break
                elif x in [70, 70+32]: # f FDC toggle
                    SHOW_FDC = not SHOW_FDC
                    refreshScreen(db, scr)
                elif x in [65, 65+32]: # a AIRMET toggle
                    SHOW_AIRMET = not SHOW_AIRMET
                    refreshScreen(db, scr)
                elif x in [68, 68+32]: # d NOTAM AD (aerodrome) toggle
                    SHOW_AD = not SHOW_AD
                    refreshScreen(db, scr)
                elif x in [71, 71+32]: # g G_AIRMET toggle
                    SHOW_G_AIRMET = not SHOW_G_AIRMET
                    refreshScreen(db, scr)
                elif x in [87, 87+32]: # w WINDS toggle
                    SHOW_WINDS = not SHOW_WINDS
                    refreshScreen(db, scr)
                elif x in [78, 78+32]: # n NOTAM toggle
                    SHOW_NOTAMS = not SHOW_NOTAMS
                    refreshScreen(db, scr)
                elif x in [79, 79+32]: # o NOTAM obstruction toggle
                    SHOW_OBST = not SHOW_OBST
                    refreshScreen(db, scr)
                elif x in [77, 77+32]: # m METAR toggle
                    SHOW_METAR = not SHOW_METAR
                    refreshScreen(db, scr)
                elif x in [83, 83+32]: # s all AIRMETs toggle
                    SHOW_ALL_AIRMETS = not SHOW_ALL_AIRMETS
                    refreshScreen(db, scr)
                elif x in [84, 84+32]: # t TAF toggle
                    SHOW_TAF = not SHOW_TAF
                    refreshScreen(db, scr)
                elif x in [85, 85+32]: # u FIS-B UNAVAILABLE toggle
                    SHOW_UNAVAILABLE = not SHOW_UNAVAILABLE
                    refreshScreen(db, scr)

                time.sleep(0.250)

    except KeyboardInterrupt:
        curses.nocbreak()
        scr.keypad(False)
        curses.echo()
        curses.endwin()
        sys.exit(0)

def localwx():
    """Main routine.

    Create database connection and produce desired report.
    Initialize curses if using it.
    """
    client = MongoClient(mongoUri, tz_aware=True)
    db = client.fisb

    if USE_CURSES:
        cursesDisplay(db)
    else:
        wxStr = myWx(db)    
        print(wxStr, end='')
    
if __name__ == "__main__":
    hlpText = \
"""Display local weather from database.
    
For curses mode, the following keys are used (either upper or lower case):
 q - Quit
 a - Toggle AIRMETs (Will show SIGMET/WST, CWA)
 d - Toggle aerodrome NOTAMS
 f - Toggle FDC NOTAMS 
 g - Toggle G-AIRMETS
 m - Toggle METARs
 n - Toggle NOTAMS
 o - Toggle NOTAM obstructions
 s - Toggle all AIRMETs (SIGMET/WST, CWA, AIRMET)
 t - Toggle TAFS
 u - Toggle FIS-B Unavailable messages
 w - Toggle Wind

 <space> will update screen
 """
    parser = argparse.ArgumentParser(description= hlpText, \
        formatter_class=RawTextHelpFormatter)

    parser.add_argument('--fdc', help="Show FDC NOTAMS", action="store_true")
    parser.add_argument('--airmet', help="Show AIRMETs (will show CWA, SIGMET/WST)", action="store_true")
    parser.add_argument('--nogairmet', help="Don't show G-AIRMET forecasts", action="store_true")
    parser.add_argument('--nowinds', help="Don't show wind forecast", action="store_true")
    parser.add_argument('--nonotam', help="Don't show any NOTAMS", action="store_true")
    parser.add_argument('--nounavail', help="Don't show any FIS-B Unavailable notices", action="store_true")
    parser.add_argument('--obst', help="Show NOTAM obstructions", action="store_true")
    parser.add_argument('--ad', help="Don't show aerodrome (AD) NOTAMs", action="store_true")
    parser.add_argument('--all', help="Show everything", action="store_true")
    parser.add_argument('--curses', help="Show on updating display", action="store_true")
    
    args = parser.parse_args()
        
    if args.fdc:
        SHOW_FDC = True

    if args.airmet:
        SHOW_AIRMET = True

    if args.nogairmet:
        SHOW_G_AIRMET = False

    if args.nounavail:
        SHOW_UNAVAILABLE = False

    if args.nowinds:
        SHOW_WINDS = False

    if args.nonotam:
        SHOW_NOTAMS = False

    if args.obst:
        SHOW_OBST = True

    if args.ad:
        SHOW_AD = False

    if args.all:
        SHOW_FDC = True
        SHOW_AIRMET = True
        SHOW_G_AIRMET = True
        SHOW_WINDS = True
        SHOW_NOTAMS = True
        SHOW_OBST = True
        SHOW_AD = True
        SHOW_UNAVAILABLE = True

    if args.curses:
        USE_CURSES = True

    # Call localwx
    localwx()
