#!/usr/bin/env python3

"""Test data for the utilities module in level2.
"""

import sys, os, datetime

from fisb.level2.utilities import singleDigitYear
from fisb.level2.utilities import doubleDigitYear
from fisb.level2.utilities import dayHourMinToIso8601
from fisb.level2.utilities import cleanFAAText

def test_cleanFAAText():
    xx = cleanFAAText("line1\nline2\n")
    xx = xx.replace(' ','_')
    assert(xx == """line1
line2""")

    xx = cleanFAAText("METAR K0A9 060115Z AUTO 00000KT 10SM SCT060 SCT070 22/20 A2998 RMK  \n     AO2=\n")
    xx = xx.replace(' ','_')
    assert(xx == """METAR_K0A9_060115Z_AUTO_00000KT_10SM_SCT060_SCT070_22/20_A2998_RMK
_____AO2=""")

    xx = cleanFAAText("TAF.AMD KAGC 062205Z 0622/0718 23011G19KT P6SM VCTS BKN040CB\n      TEMPO 0622/0623 34015G25KT\n     FM070000 20004KT P6SM BKN040\n     FM070300 19003KT P6SM VCSH BKN040\n     FM070600 20004KT P6SM BKN040\n     FM071700 22006KT P6SM VCTS BKN035CB=\n")
    xx = xx.replace(' ','_')
    assert(xx == """TAF.AMD_KAGC_062205Z_0622/0718_23011G19KT_P6SM_VCTS_BKN040CB
______TEMPO_0622/0623_34015G25KT
_____FM070000_20004KT_P6SM_BKN040
_____FM070300_19003KT_P6SM_VCSH_BKN040
_____FM070600_20004KT_P6SM_BKN040
_____FM071700_22006KT_P6SM_VCTS_BKN035CB=""")

    xx = cleanFAAText("WINDS TYS 111800Z  FT 3000 6000      9000   12000       18000   24000   30000    34000  39000                         \n   9900 9900+19 0109+13 3512+08 3324-03 3232-16 344430 336240 347153\n")
    xx = xx.replace(' ','_')
    assert(xx == """WINDS_TYS_111800Z__FT_3000_6000______9000___12000_______18000___24000___30000____34000__39000
___9900_9900+19_0109+13_3512+08_3324-03_3232-16_344430_336240_347153""")

def generateTestData_singleDigitYear():
    for i in range(2015, 2026):
        for j in range(0, 10):
            yearStr = str(j)
            print("    assert(singleDigitYear({}, '{}')) == {}"\
                .format(i, j, \
                        singleDigitYear(i, yearStr)))

def generateTestData_doubleDigitYear():
    for i in range(2000, 2031):
        for j in range(0, 100, 10):
            yearStr = str(j)
            print('    assert(doubleDigitYear({}, "{}")) == "{}"'\
                .format(i, j, \
                        doubleDigitYear(i, yearStr)))
            
def test_dayHourMinToIso8601():
    assert(dayHourMinToIso8601(2019, 8, 13, '141222')) == '2019-08-14T12:22:00'
    assert(dayHourMinToIso8601(2019, 8, 14, '141222')) == '2019-08-14T12:22:00'
    assert(dayHourMinToIso8601(2019, 8, 15, '141222')) == '2019-08-14T12:22:00'
    assert(dayHourMinToIso8601(2019, 8, 14, '131222')) == '2019-08-13T12:22:00'
    assert(dayHourMinToIso8601(2019, 8, 14, '141222')) == '2019-08-14T12:22:00'
    assert(dayHourMinToIso8601(2019, 8, 14, '151222')) == '2019-08-15T12:22:00'
    assert(dayHourMinToIso8601(2019, 8, 30, '011222')) == '2019-09-01T12:22:00'
    assert(dayHourMinToIso8601(2019, 8, 30, '021222')) == '2019-09-02T12:22:00'
    assert(dayHourMinToIso8601(2019, 8, 30, '031222')) == '2019-09-03T12:22:00'
    assert(dayHourMinToIso8601(2019, 9, 1, '291222')) == '2019-08-29T12:22:00'
    assert(dayHourMinToIso8601(2019, 9, 2, '301222')) == '2019-08-30T12:22:00'
    assert(dayHourMinToIso8601(2019, 9, 3, '031222')) == '2019-09-03T12:22:00'
    assert(dayHourMinToIso8601(2019, 12, 30, '011222')) == '2020-01-01T12:22:00'
    assert(dayHourMinToIso8601(2019, 12, 30, '021222')) == '2020-01-02T12:22:00'
    assert(dayHourMinToIso8601(2019, 12, 30, '031222')) == '2020-01-03T12:22:00'
    assert(dayHourMinToIso8601(2019, 1, 1, '271222')) == '2018-12-27T12:22:00'
    assert(dayHourMinToIso8601(2019, 1, 1, '291222')) == '2018-12-29T12:22:00'
    assert(dayHourMinToIso8601(2019, 1, 1, '311222')) == '2018-12-31T12:22:00'
    assert(dayHourMinToIso8601(2019, 9, 6, '1012')) == '2019-09-10T12:00:00'
    assert(dayHourMinToIso8601(2019, 9, 6, '1024')) == '2019-09-11T00:00:00'
    assert(dayHourMinToIso8601(2019, 2, 28, '011234')) == '2019-03-01T12:34:00'
    assert(dayHourMinToIso8601(2020, 2, 28, '011234')) == '2020-03-01T12:34:00'
    assert(dayHourMinToIso8601(2020, 2, 28, '291234')) == '2020-02-29T12:34:00'

def test_singleDigitYear():
    assert(singleDigitYear(2015, '0')) == 2010
    assert(singleDigitYear(2015, '1')) == 2011
    assert(singleDigitYear(2015, '2')) == 2012
    assert(singleDigitYear(2015, '3')) == 2013
    assert(singleDigitYear(2015, '4')) == 2014
    assert(singleDigitYear(2015, '5')) == 2015
    assert(singleDigitYear(2015, '6')) == 2016
    assert(singleDigitYear(2015, '7')) == 2017
    assert(singleDigitYear(2015, '8')) == 2018
    assert(singleDigitYear(2015, '9')) == 2019
    assert(singleDigitYear(2016, '0')) == 2020
    assert(singleDigitYear(2016, '1')) == 2011
    assert(singleDigitYear(2016, '2')) == 2012
    assert(singleDigitYear(2016, '3')) == 2013
    assert(singleDigitYear(2016, '4')) == 2014
    assert(singleDigitYear(2016, '5')) == 2015
    assert(singleDigitYear(2016, '6')) == 2016
    assert(singleDigitYear(2016, '7')) == 2017
    assert(singleDigitYear(2016, '8')) == 2018
    assert(singleDigitYear(2016, '9')) == 2019
    assert(singleDigitYear(2017, '0')) == 2020
    assert(singleDigitYear(2017, '1')) == 2021
    assert(singleDigitYear(2017, '2')) == 2012
    assert(singleDigitYear(2017, '3')) == 2013
    assert(singleDigitYear(2017, '4')) == 2014
    assert(singleDigitYear(2017, '5')) == 2015
    assert(singleDigitYear(2017, '6')) == 2016
    assert(singleDigitYear(2017, '7')) == 2017
    assert(singleDigitYear(2017, '8')) == 2018
    assert(singleDigitYear(2017, '9')) == 2019
    assert(singleDigitYear(2018, '0')) == 2020
    assert(singleDigitYear(2018, '1')) == 2021
    assert(singleDigitYear(2018, '2')) == 2022
    assert(singleDigitYear(2018, '3')) == 2013
    assert(singleDigitYear(2018, '4')) == 2014
    assert(singleDigitYear(2018, '5')) == 2015
    assert(singleDigitYear(2018, '6')) == 2016
    assert(singleDigitYear(2018, '7')) == 2017
    assert(singleDigitYear(2018, '8')) == 2018
    assert(singleDigitYear(2018, '9')) == 2019
    assert(singleDigitYear(2019, '0')) == 2020
    assert(singleDigitYear(2019, '1')) == 2021
    assert(singleDigitYear(2019, '2')) == 2022
    assert(singleDigitYear(2019, '3')) == 2023
    assert(singleDigitYear(2019, '4')) == 2014
    assert(singleDigitYear(2019, '5')) == 2015
    assert(singleDigitYear(2019, '6')) == 2016
    assert(singleDigitYear(2019, '7')) == 2017
    assert(singleDigitYear(2019, '8')) == 2018
    assert(singleDigitYear(2019, '9')) == 2019
    assert(singleDigitYear(2020, '0')) == 2020
    assert(singleDigitYear(2020, '1')) == 2021
    assert(singleDigitYear(2020, '2')) == 2022
    assert(singleDigitYear(2020, '3')) == 2023
    assert(singleDigitYear(2020, '4')) == 2024
    assert(singleDigitYear(2020, '5')) == 2015
    assert(singleDigitYear(2020, '6')) == 2016
    assert(singleDigitYear(2020, '7')) == 2017
    assert(singleDigitYear(2020, '8')) == 2018
    assert(singleDigitYear(2020, '9')) == 2019
    assert(singleDigitYear(2021, '0')) == 2020
    assert(singleDigitYear(2021, '1')) == 2021
    assert(singleDigitYear(2021, '2')) == 2022
    assert(singleDigitYear(2021, '3')) == 2023
    assert(singleDigitYear(2021, '4')) == 2024
    assert(singleDigitYear(2021, '5')) == 2025
    assert(singleDigitYear(2021, '6')) == 2016
    assert(singleDigitYear(2021, '7')) == 2017
    assert(singleDigitYear(2021, '8')) == 2018
    assert(singleDigitYear(2021, '9')) == 2019
    assert(singleDigitYear(2022, '0')) == 2020
    assert(singleDigitYear(2022, '1')) == 2021
    assert(singleDigitYear(2022, '2')) == 2022
    assert(singleDigitYear(2022, '3')) == 2023
    assert(singleDigitYear(2022, '4')) == 2024
    assert(singleDigitYear(2022, '5')) == 2025
    assert(singleDigitYear(2022, '6')) == 2026
    assert(singleDigitYear(2022, '7')) == 2017
    assert(singleDigitYear(2022, '8')) == 2018
    assert(singleDigitYear(2022, '9')) == 2019
    assert(singleDigitYear(2023, '0')) == 2020
    assert(singleDigitYear(2023, '1')) == 2021
    assert(singleDigitYear(2023, '2')) == 2022
    assert(singleDigitYear(2023, '3')) == 2023
    assert(singleDigitYear(2023, '4')) == 2024
    assert(singleDigitYear(2023, '5')) == 2025
    assert(singleDigitYear(2023, '6')) == 2026
    assert(singleDigitYear(2023, '7')) == 2027
    assert(singleDigitYear(2023, '8')) == 2018
    assert(singleDigitYear(2023, '9')) == 2019
    assert(singleDigitYear(2024, '0')) == 2020
    assert(singleDigitYear(2024, '1')) == 2021
    assert(singleDigitYear(2024, '2')) == 2022
    assert(singleDigitYear(2024, '3')) == 2023
    assert(singleDigitYear(2024, '4')) == 2024
    assert(singleDigitYear(2024, '5')) == 2025
    assert(singleDigitYear(2024, '6')) == 2026
    assert(singleDigitYear(2024, '7')) == 2027
    assert(singleDigitYear(2024, '8')) == 2028
    assert(singleDigitYear(2024, '9')) == 2019
    assert(singleDigitYear(2025, '0')) == 2020
    assert(singleDigitYear(2025, '1')) == 2021
    assert(singleDigitYear(2025, '2')) == 2022
    assert(singleDigitYear(2025, '3')) == 2023
    assert(singleDigitYear(2025, '4')) == 2024
    assert(singleDigitYear(2025, '5')) == 2025
    assert(singleDigitYear(2025, '6')) == 2026
    assert(singleDigitYear(2025, '7')) == 2027
    assert(singleDigitYear(2025, '8')) == 2028
    assert(singleDigitYear(2025, '9')) == 2029

def test_doubleDigitYear():
    assert(doubleDigitYear(2000, '00')) == 2000
    assert(doubleDigitYear(2000, '10')) == 2010
    assert(doubleDigitYear(2000, '20')) == 2020
    assert(doubleDigitYear(2000, '30')) == 2030
    assert(doubleDigitYear(2000, '40')) == 2040
    assert(doubleDigitYear(2000, '50')) == 1950
    assert(doubleDigitYear(2000, '60')) == 1960
    assert(doubleDigitYear(2000, '70')) == 1970
    assert(doubleDigitYear(2000, '80')) == 1980
    assert(doubleDigitYear(2000, '90')) == 1990
    assert(doubleDigitYear(2001, '00')) == 2000
    assert(doubleDigitYear(2001, '10')) == 2010
    assert(doubleDigitYear(2001, '20')) == 2020
    assert(doubleDigitYear(2001, '30')) == 2030
    assert(doubleDigitYear(2001, '40')) == 2040
    assert(doubleDigitYear(2001, '50')) == 2050
    assert(doubleDigitYear(2001, '60')) == 1960
    assert(doubleDigitYear(2001, '70')) == 1970
    assert(doubleDigitYear(2001, '80')) == 1980
    assert(doubleDigitYear(2001, '90')) == 1990
    assert(doubleDigitYear(2002, '00')) == 2000
    assert(doubleDigitYear(2002, '10')) == 2010
    assert(doubleDigitYear(2002, '20')) == 2020
    assert(doubleDigitYear(2002, '30')) == 2030
    assert(doubleDigitYear(2002, '40')) == 2040
    assert(doubleDigitYear(2002, '50')) == 2050
    assert(doubleDigitYear(2002, '60')) == 1960
    assert(doubleDigitYear(2002, '70')) == 1970
    assert(doubleDigitYear(2002, '80')) == 1980
    assert(doubleDigitYear(2002, '90')) == 1990
    assert(doubleDigitYear(2003, '00')) == 2000
    assert(doubleDigitYear(2003, '10')) == 2010
    assert(doubleDigitYear(2003, '20')) == 2020
    assert(doubleDigitYear(2003, '30')) == 2030
    assert(doubleDigitYear(2003, '40')) == 2040
    assert(doubleDigitYear(2003, '50')) == 2050
    assert(doubleDigitYear(2003, '60')) == 1960
    assert(doubleDigitYear(2003, '70')) == 1970
    assert(doubleDigitYear(2003, '80')) == 1980
    assert(doubleDigitYear(2003, '90')) == 1990
    assert(doubleDigitYear(2004, '00')) == 2000
    assert(doubleDigitYear(2004, '10')) == 2010
    assert(doubleDigitYear(2004, '20')) == 2020
    assert(doubleDigitYear(2004, '30')) == 2030
    assert(doubleDigitYear(2004, '40')) == 2040
    assert(doubleDigitYear(2004, '50')) == 2050
    assert(doubleDigitYear(2004, '60')) == 1960
    assert(doubleDigitYear(2004, '70')) == 1970
    assert(doubleDigitYear(2004, '80')) == 1980
    assert(doubleDigitYear(2004, '90')) == 1990
    assert(doubleDigitYear(2005, '00')) == 2000
    assert(doubleDigitYear(2005, '10')) == 2010
    assert(doubleDigitYear(2005, '20')) == 2020
    assert(doubleDigitYear(2005, '30')) == 2030
    assert(doubleDigitYear(2005, '40')) == 2040
    assert(doubleDigitYear(2005, '50')) == 2050
    assert(doubleDigitYear(2005, '60')) == 1960
    assert(doubleDigitYear(2005, '70')) == 1970
    assert(doubleDigitYear(2005, '80')) == 1980
    assert(doubleDigitYear(2005, '90')) == 1990
    assert(doubleDigitYear(2006, '00')) == 2000
    assert(doubleDigitYear(2006, '10')) == 2010
    assert(doubleDigitYear(2006, '20')) == 2020
    assert(doubleDigitYear(2006, '30')) == 2030
    assert(doubleDigitYear(2006, '40')) == 2040
    assert(doubleDigitYear(2006, '50')) == 2050
    assert(doubleDigitYear(2006, '60')) == 1960
    assert(doubleDigitYear(2006, '70')) == 1970
    assert(doubleDigitYear(2006, '80')) == 1980
    assert(doubleDigitYear(2006, '90')) == 1990
    assert(doubleDigitYear(2007, '00')) == 2000
    assert(doubleDigitYear(2007, '10')) == 2010
    assert(doubleDigitYear(2007, '20')) == 2020
    assert(doubleDigitYear(2007, '30')) == 2030
    assert(doubleDigitYear(2007, '40')) == 2040
    assert(doubleDigitYear(2007, '50')) == 2050
    assert(doubleDigitYear(2007, '60')) == 1960
    assert(doubleDigitYear(2007, '70')) == 1970
    assert(doubleDigitYear(2007, '80')) == 1980
    assert(doubleDigitYear(2007, '90')) == 1990
    assert(doubleDigitYear(2008, '00')) == 2000
    assert(doubleDigitYear(2008, '10')) == 2010
    assert(doubleDigitYear(2008, '20')) == 2020
    assert(doubleDigitYear(2008, '30')) == 2030
    assert(doubleDigitYear(2008, '40')) == 2040
    assert(doubleDigitYear(2008, '50')) == 2050
    assert(doubleDigitYear(2008, '60')) == 1960
    assert(doubleDigitYear(2008, '70')) == 1970
    assert(doubleDigitYear(2008, '80')) == 1980
    assert(doubleDigitYear(2008, '90')) == 1990
    assert(doubleDigitYear(2009, '00')) == 2000
    assert(doubleDigitYear(2009, '10')) == 2010
    assert(doubleDigitYear(2009, '20')) == 2020
    assert(doubleDigitYear(2009, '30')) == 2030
    assert(doubleDigitYear(2009, '40')) == 2040
    assert(doubleDigitYear(2009, '50')) == 2050
    assert(doubleDigitYear(2009, '60')) == 1960
    assert(doubleDigitYear(2009, '70')) == 1970
    assert(doubleDigitYear(2009, '80')) == 1980
    assert(doubleDigitYear(2009, '90')) == 1990
    assert(doubleDigitYear(2010, '00')) == 2000
    assert(doubleDigitYear(2010, '10')) == 2010
    assert(doubleDigitYear(2010, '20')) == 2020
    assert(doubleDigitYear(2010, '30')) == 2030
    assert(doubleDigitYear(2010, '40')) == 2040
    assert(doubleDigitYear(2010, '50')) == 2050
    assert(doubleDigitYear(2010, '60')) == 1960
    assert(doubleDigitYear(2010, '70')) == 1970
    assert(doubleDigitYear(2010, '80')) == 1980
    assert(doubleDigitYear(2010, '90')) == 1990
    assert(doubleDigitYear(2011, '00')) == 2000
    assert(doubleDigitYear(2011, '10')) == 2010
    assert(doubleDigitYear(2011, '20')) == 2020
    assert(doubleDigitYear(2011, '30')) == 2030
    assert(doubleDigitYear(2011, '40')) == 2040
    assert(doubleDigitYear(2011, '50')) == 2050
    assert(doubleDigitYear(2011, '60')) == 2060
    assert(doubleDigitYear(2011, '70')) == 1970
    assert(doubleDigitYear(2011, '80')) == 1980
    assert(doubleDigitYear(2011, '90')) == 1990
    assert(doubleDigitYear(2012, '00')) == 2000
    assert(doubleDigitYear(2012, '10')) == 2010
    assert(doubleDigitYear(2012, '20')) == 2020
    assert(doubleDigitYear(2012, '30')) == 2030
    assert(doubleDigitYear(2012, '40')) == 2040
    assert(doubleDigitYear(2012, '50')) == 2050
    assert(doubleDigitYear(2012, '60')) == 2060
    assert(doubleDigitYear(2012, '70')) == 1970
    assert(doubleDigitYear(2012, '80')) == 1980
    assert(doubleDigitYear(2012, '90')) == 1990
    assert(doubleDigitYear(2013, '00')) == 2000
    assert(doubleDigitYear(2013, '10')) == 2010
    assert(doubleDigitYear(2013, '20')) == 2020
    assert(doubleDigitYear(2013, '30')) == 2030
    assert(doubleDigitYear(2013, '40')) == 2040
    assert(doubleDigitYear(2013, '50')) == 2050
    assert(doubleDigitYear(2013, '60')) == 2060
    assert(doubleDigitYear(2013, '70')) == 1970
    assert(doubleDigitYear(2013, '80')) == 1980
    assert(doubleDigitYear(2013, '90')) == 1990
    assert(doubleDigitYear(2014, '00')) == 2000
    assert(doubleDigitYear(2014, '10')) == 2010
    assert(doubleDigitYear(2014, '20')) == 2020
    assert(doubleDigitYear(2014, '30')) == 2030
    assert(doubleDigitYear(2014, '40')) == 2040
    assert(doubleDigitYear(2014, '50')) == 2050
    assert(doubleDigitYear(2014, '60')) == 2060
    assert(doubleDigitYear(2014, '70')) == 1970
    assert(doubleDigitYear(2014, '80')) == 1980
    assert(doubleDigitYear(2014, '90')) == 1990
    assert(doubleDigitYear(2015, '00')) == 2000
    assert(doubleDigitYear(2015, '10')) == 2010
    assert(doubleDigitYear(2015, '20')) == 2020
    assert(doubleDigitYear(2015, '30')) == 2030
    assert(doubleDigitYear(2015, '40')) == 2040
    assert(doubleDigitYear(2015, '50')) == 2050
    assert(doubleDigitYear(2015, '60')) == 2060
    assert(doubleDigitYear(2015, '70')) == 1970
    assert(doubleDigitYear(2015, '80')) == 1980
    assert(doubleDigitYear(2015, '90')) == 1990
    assert(doubleDigitYear(2016, '00')) == 2000
    assert(doubleDigitYear(2016, '10')) == 2010
    assert(doubleDigitYear(2016, '20')) == 2020
    assert(doubleDigitYear(2016, '30')) == 2030
    assert(doubleDigitYear(2016, '40')) == 2040
    assert(doubleDigitYear(2016, '50')) == 2050
    assert(doubleDigitYear(2016, '60')) == 2060
    assert(doubleDigitYear(2016, '70')) == 1970
    assert(doubleDigitYear(2016, '80')) == 1980
    assert(doubleDigitYear(2016, '90')) == 1990
    assert(doubleDigitYear(2017, '00')) == 2000
    assert(doubleDigitYear(2017, '10')) == 2010
    assert(doubleDigitYear(2017, '20')) == 2020
    assert(doubleDigitYear(2017, '30')) == 2030
    assert(doubleDigitYear(2017, '40')) == 2040
    assert(doubleDigitYear(2017, '50')) == 2050
    assert(doubleDigitYear(2017, '60')) == 2060
    assert(doubleDigitYear(2017, '70')) == 1970
    assert(doubleDigitYear(2017, '80')) == 1980
    assert(doubleDigitYear(2017, '90')) == 1990
    assert(doubleDigitYear(2018, '00')) == 2000
    assert(doubleDigitYear(2018, '10')) == 2010
    assert(doubleDigitYear(2018, '20')) == 2020
    assert(doubleDigitYear(2018, '30')) == 2030
    assert(doubleDigitYear(2018, '40')) == 2040
    assert(doubleDigitYear(2018, '50')) == 2050
    assert(doubleDigitYear(2018, '60')) == 2060
    assert(doubleDigitYear(2018, '70')) == 1970
    assert(doubleDigitYear(2018, '80')) == 1980
    assert(doubleDigitYear(2018, '90')) == 1990
    assert(doubleDigitYear(2019, '00')) == 2000
    assert(doubleDigitYear(2019, '10')) == 2010
    assert(doubleDigitYear(2019, '20')) == 2020
    assert(doubleDigitYear(2019, '30')) == 2030
    assert(doubleDigitYear(2019, '40')) == 2040
    assert(doubleDigitYear(2019, '50')) == 2050
    assert(doubleDigitYear(2019, '60')) == 2060
    assert(doubleDigitYear(2019, '70')) == 1970
    assert(doubleDigitYear(2019, '80')) == 1980
    assert(doubleDigitYear(2019, '90')) == 1990
    assert(doubleDigitYear(2020, '00')) == 2000
    assert(doubleDigitYear(2020, '10')) == 2010
    assert(doubleDigitYear(2020, '20')) == 2020
    assert(doubleDigitYear(2020, '30')) == 2030
    assert(doubleDigitYear(2020, '40')) == 2040
    assert(doubleDigitYear(2020, '50')) == 2050
    assert(doubleDigitYear(2020, '60')) == 2060
    assert(doubleDigitYear(2020, '70')) == 1970
    assert(doubleDigitYear(2020, '80')) == 1980
    assert(doubleDigitYear(2020, '90')) == 1990
    assert(doubleDigitYear(2021, '00')) == 2000
    assert(doubleDigitYear(2021, '10')) == 2010
    assert(doubleDigitYear(2021, '20')) == 2020
    assert(doubleDigitYear(2021, '30')) == 2030
    assert(doubleDigitYear(2021, '40')) == 2040
    assert(doubleDigitYear(2021, '50')) == 2050
    assert(doubleDigitYear(2021, '60')) == 2060
    assert(doubleDigitYear(2021, '70')) == 2070
    assert(doubleDigitYear(2021, '80')) == 1980
    assert(doubleDigitYear(2021, '90')) == 1990
    assert(doubleDigitYear(2022, '00')) == 2000
    assert(doubleDigitYear(2022, '10')) == 2010
    assert(doubleDigitYear(2022, '20')) == 2020
    assert(doubleDigitYear(2022, '30')) == 2030
    assert(doubleDigitYear(2022, '40')) == 2040
    assert(doubleDigitYear(2022, '50')) == 2050
    assert(doubleDigitYear(2022, '60')) == 2060
    assert(doubleDigitYear(2022, '70')) == 2070
    assert(doubleDigitYear(2022, '80')) == 1980
    assert(doubleDigitYear(2022, '90')) == 1990
    assert(doubleDigitYear(2023, '00')) == 2000
    assert(doubleDigitYear(2023, '10')) == 2010
    assert(doubleDigitYear(2023, '20')) == 2020
    assert(doubleDigitYear(2023, '30')) == 2030
    assert(doubleDigitYear(2023, '40')) == 2040
    assert(doubleDigitYear(2023, '50')) == 2050
    assert(doubleDigitYear(2023, '60')) == 2060
    assert(doubleDigitYear(2023, '70')) == 2070
    assert(doubleDigitYear(2023, '80')) == 1980
    assert(doubleDigitYear(2023, '90')) == 1990
    assert(doubleDigitYear(2024, '00')) == 2000
    assert(doubleDigitYear(2024, '10')) == 2010
    assert(doubleDigitYear(2024, '20')) == 2020
    assert(doubleDigitYear(2024, '30')) == 2030
    assert(doubleDigitYear(2024, '40')) == 2040
    assert(doubleDigitYear(2024, '50')) == 2050
    assert(doubleDigitYear(2024, '60')) == 2060
    assert(doubleDigitYear(2024, '70')) == 2070
    assert(doubleDigitYear(2024, '80')) == 1980
    assert(doubleDigitYear(2024, '90')) == 1990
    assert(doubleDigitYear(2025, '00')) == 2000
    assert(doubleDigitYear(2025, '10')) == 2010
    assert(doubleDigitYear(2025, '20')) == 2020
    assert(doubleDigitYear(2025, '30')) == 2030
    assert(doubleDigitYear(2025, '40')) == 2040
    assert(doubleDigitYear(2025, '50')) == 2050
    assert(doubleDigitYear(2025, '60')) == 2060
    assert(doubleDigitYear(2025, '70')) == 2070
    assert(doubleDigitYear(2025, '80')) == 1980
    assert(doubleDigitYear(2025, '90')) == 1990
    assert(doubleDigitYear(2026, '00')) == 2000
    assert(doubleDigitYear(2026, '10')) == 2010
    assert(doubleDigitYear(2026, '20')) == 2020
    assert(doubleDigitYear(2026, '30')) == 2030
    assert(doubleDigitYear(2026, '40')) == 2040
    assert(doubleDigitYear(2026, '50')) == 2050
    assert(doubleDigitYear(2026, '60')) == 2060
    assert(doubleDigitYear(2026, '70')) == 2070
    assert(doubleDigitYear(2026, '80')) == 1980
    assert(doubleDigitYear(2026, '90')) == 1990
    assert(doubleDigitYear(2027, '00')) == 2000
    assert(doubleDigitYear(2027, '10')) == 2010
    assert(doubleDigitYear(2027, '20')) == 2020
    assert(doubleDigitYear(2027, '30')) == 2030
    assert(doubleDigitYear(2027, '40')) == 2040
    assert(doubleDigitYear(2027, '50')) == 2050
    assert(doubleDigitYear(2027, '60')) == 2060
    assert(doubleDigitYear(2027, '70')) == 2070
    assert(doubleDigitYear(2027, '80')) == 1980
    assert(doubleDigitYear(2027, '90')) == 1990
    assert(doubleDigitYear(2028, '00')) == 2000
    assert(doubleDigitYear(2028, '10')) == 2010
    assert(doubleDigitYear(2028, '20')) == 2020
    assert(doubleDigitYear(2028, '30')) == 2030
    assert(doubleDigitYear(2028, '40')) == 2040
    assert(doubleDigitYear(2028, '50')) == 2050
    assert(doubleDigitYear(2028, '60')) == 2060
    assert(doubleDigitYear(2028, '70')) == 2070
    assert(doubleDigitYear(2028, '80')) == 1980
    assert(doubleDigitYear(2028, '90')) == 1990
    assert(doubleDigitYear(2029, '00')) == 2000
    assert(doubleDigitYear(2029, '10')) == 2010
    assert(doubleDigitYear(2029, '20')) == 2020
    assert(doubleDigitYear(2029, '30')) == 2030
    assert(doubleDigitYear(2029, '40')) == 2040
    assert(doubleDigitYear(2029, '50')) == 2050
    assert(doubleDigitYear(2029, '60')) == 2060
    assert(doubleDigitYear(2029, '70')) == 2070
    assert(doubleDigitYear(2029, '80')) == 1980
    assert(doubleDigitYear(2029, '90')) == 1990
    assert(doubleDigitYear(2030, '00')) == 2000
    assert(doubleDigitYear(2030, '10')) == 2010
    assert(doubleDigitYear(2030, '20')) == 2020
    assert(doubleDigitYear(2030, '30')) == 2030
    assert(doubleDigitYear(2030, '40')) == 2040
    assert(doubleDigitYear(2030, '50')) == 2050
    assert(doubleDigitYear(2030, '60')) == 2060
    assert(doubleDigitYear(2030, '70')) == 2070
    assert(doubleDigitYear(2030, '80')) == 1980
    assert(doubleDigitYear(2030, '90')) == 1990
