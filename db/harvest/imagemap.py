"""Image maps used for producing images.

In Visual Studio Code, add the ``Color Highlight`` extention to
view the colors.
"""
import db.harvest.harvestConfig as cfg

# Value for 'not included'.
NOT_INCLUDED = (cfg.NOT_INCLUDED_RED << 16) | \
    (cfg.NOT_INCLUDED_GREEN << 8) | \
    cfg.NOT_INCLUDED_BLUE

# Types of image map configurations.
GENERAL = 0
TESTING = 1
SHOW_NO_DATA = 2

# String for no data value display.
NO_DATA_STR = 'No Data'

# String for 'not included' display.
NOT_INCL_STR = 'Not Incl'

IMAGE_MAP_CONFIGURATION = cfg.IMAGE_MAP_CONFIGURATION

radar0alpha = 0
radar1alpha = 0
NDalpha = 0
NIalpha = 0
lightning0alpha = 0
icing0alpha = 0
NDcolor = 0xb6b6b6

if IMAGE_MAP_CONFIGURATION == GENERAL:
    pass
elif IMAGE_MAP_CONFIGURATION == TESTING:
    radar0alpha = 255
    radar1alpha = 255
    lightning0alpha = 255
    icing0alpha = 255
    NDalpha = 255
    NIalpha = 255
elif IMAGE_MAP_CONFIGURATION == SHOW_NO_DATA:
    NDalpha = 255
    NIalpha = 255
    NDcolor = NOT_INCLUDED

#---- Radar ------------------------------------

#000000 <5
#00ff35 5-20
#0ba31e 20-30
#fffe3a 30-40
#ff0011 40-45
#990017 45-50
#ff00fb 50-55
#9a0096 >55
#ecda96 Not Included (may vary)

RADAR_MAP_0 = { \
               0: (0x000000, radar0alpha, '<5', 'dBZ'), \
               1: (0x00ff35, radar1alpha, '5-20', 'dBZ'), \
               2: (0x0ba31e, 255, '20-30', 'dBZ'), \
               3: (0xfffe3a, 255, '30-40', 'dBZ'), \
               4: (0xff0011, 255, '40-45', 'dBZ'), \
               5: (0x990017, 255, '45-50', 'dBZ'), \
               6: (0xff00fb, 255, '50-55', 'dBZ'), \
               7: (0x9a0096, 255, '>55', 'dBZ'), \
               255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'dBZ'), \
}

#ffffff <5
#00fffe 5-20
#00ee31 20-30
#0ba31e 30-40
#fffe3a 40-45
#ff973e 45-50
#ff0011 50-55
#ff00fb >55
#ecda96 Not Included (may vary)

RADAR_MAP_1 = { \
               0: (0x000000, radar0alpha, '<5', 'dBZ'), \
               1: (0x00fffe, radar1alpha, '5-20', 'dBZ'), \
               2: (0x00ee31, 255, '20-30', 'dBZ'), \
               3: (0x0ba31e, 255, '30-40', 'dBZ'), \
               4: (0xfffe3a, 255, '40-45', 'dBZ'), \
               5: (0xff973e, 255, '45-50', 'dBZ'), \
               6: (0xff0011, 255, '50-55', 'dBZ'), \
               7: (0xff00fb, 255, '>55', 'dBZ'), \
               255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'dBZ'), \
}

#---- Turbulence ------------------------------------

#000000 <7
#0000ff 7-14
#8686ff 14-21 (>=13 considered light, >= 16 moderate for light afct)
#76d3ff 21-28
#008600 28-35
#00ff00 35-42 (>=36 considered severe for light afct)
#c4ffc4 42-49
#ffff00 49-56
#f18635 56-63
#864613 63-70 (>=64 considered extreme for light afct)
#ff0000 70-77
#ffcdcd 77-84
#ff00ff 84-91
#a500a5 91-98
#000000 >98
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

TURB_MAP_0 = { \
              0: (0x0, 255, '<7', 'EDR*100'), \
              1: (0x0000ff, 255, '7-14', 'EDR*100'), \
              2: (0x8686ff, 255, '14-21', 'EDR*100'), \
              3: (0x76d3ff, 255, '21-28', 'EDR*100'), \
              4: (0x008600, 255, '28-35', 'EDR*100'), \
              5: (0x00ff00, 255, '35-42', 'EDR*100'), \
              6: (0xc4ffc4, 255, '42-49', 'EDR*100'), \
              7: (0xffff00, 255, '49-56', 'EDR*100'), \
              8: (0xf18635, 255, '56-63', 'EDR*100'), \
              9: (0x864613, 255, '63-70', 'EDR*100'), \
              10: (0xff0000, 255, '70-77', 'EDR*100'), \
              11: (0xffcdcd, 255, '77-84', 'EDR*100'), \
              12: (0xff00ff, 255, '84-91', 'EDR*100'), \
              13: (0xa500a5, 255, '91-98', 'EDR*100'), \
              14: (0x000000, 255, '>98', 'EDR*100'), \
              15: (0xb6b6b6, 255, NO_DATA_STR, 'EDR*100'), \
              255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'EDR*100'), \
}

# Alternate map mimics Aviation Weather Center turbulence
#ffffff <7
#c8ffff 7-14
#ccfe71 14-21 (>=13 considered light, >= 16 moderate for light afct)
#edde35 21-28
#ffb42e 28-35
#ff9528 35-42 (>=36 considered severe for light afct)
#ff7623 42-49
#ff4c1d 49-56
#ff0018 56-63
#e30015 63-70 (>=64 considered extreme for light afct)
#b90011 70-77
#8f000d 77-84
#7b000c 84-91
#530008 91-98
#410006 >98
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

TURB_MAP_1 = { \
              0: (0xffffff, 0, '<7', 'EDR*100'), \
              1: (0xc8ffff, 0, '7-14', 'EDR*100'), \
              2: (0xccfe71, 255, '14-21', 'EDR*100'), \
              3: (0xedde35, 255, '21-28', 'EDR*100'), \
              4: (0xffb42e, 255, '28-35', 'EDR*100'), \
              5: (0xff9528, 255, '35-42', 'EDR*100'), \
              6: (0xff7623, 255, '42-49', 'EDR*100'), \
              7: (0xff4c1d, 255, '49-56', 'EDR*100'), \
              8: (0xff0018, 255, '56-63', 'EDR*100'), \
              9: (0xe30015, 255, '63-70', 'EDR*100'), \
              10: (0xb90011, 255, '70-77', 'EDR*100'), \
              11: (0x8f000d, 255, '77-84', 'EDR*100'), \
              12: (0x7b000c, 255, '84-91', 'EDR*100'), \
              13: (0x530008, 255, '91-98', 'EDR*100'), \
              14: (0x410006, 255, '>98', 'EDR*100'), \
              15: (NDcolor, NDalpha, NO_DATA_STR, 'EDR*100'), \
              255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'EDR*100'), \
}

#---- Cloud Tops ------------------------------------

#000000 No Clouds
#0000ff < 1500
#8686ff 1500-3000
#76d3ff 3000-4500
#008600 4500-6000
#00ff00 6000-7500
#c4ffc4 7500-9000
#ffff00 9000-10500
#f18635 10500-12000
#864613 12000-13500
#ff0000 13500-15000
#ffcdcd 15000-18000
#ff00ff 18000-21000
#a500a5 21000-24000
#ff0000 >24000
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

CLOUDTOP_MAP_0 = { \
                  0: (0x000000, 255, 'No Clouds', 'ft MSL'), \
                  1: (0x0000ff, 255, '< 1500', 'ft MSL'), \
                  2: (0x8686ff, 255, '1500-3000', 'ft MSL'), \
                  3: (0x76d3ff, 255, '3000-4500', 'ft MSL'), \
                  4: (0x008600, 255, '4500-6000', 'ft MSL'), \
                  5: (0x00ff00, 255, '6000-7500', 'ft MSL'), \
                  6: (0xc4ffc4, 255, '7500-9000', 'ft MSL'), \
                  7: (0xffff00, 255, '9000-10500', 'ft MSL'), \
                  8: (0xf18635, 255, '10500-12000', 'ft MSL'), \
                  9: (0x864613, 255, '12000-13500', 'ft MSL'), \
                  10: (0xff0000, 255, '13500-15000', 'ft MSL'), \
                  11: (0xffcdcd, 255, '15000-18000', 'ft MSL'), \
                  12: (0xff00ff, 255, '18000-21000', 'ft MSL'), \
                  13: (0xa500a5, 255, '21000-24000', 'ft MSL'), \
                  14: (0xff0000, 255, '>24000', 'ft MSL'), \
                  15: (0xb6b6b6, 255, NO_DATA_STR, 'ft MSL'), \
                  255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'ft MSL'), \
}

#ffffff No Clouds
#eeeeee < 1500
#dddddd 1500-3000
#cdcdcd 3000-4500 
#bbbbbb 4500-6000
#aaaaaa 6000-7500
#999999 7500-9000
#888888 9000-10500
#777777 10500-12000
#666666 12000-13500
#555555 13500-15000
#444444 15000-18000
#333333 18000-21000
#222222 21000-24000
#111111 >24000
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

CLOUDTOP_MAP_1 = { \
                  0: (0xffffff, 0, 'No Clouds', 'ft MSL'), \
                  1: (0xeeeeee, 255, '< 1500', 'ft MSL'), \
                  2: (0xdddddd, 255, '1500-3000', 'ft MSL'), \
                  3: (0xcdcdcd, 255, '3000-4500', 'ft MSL'), \
                  4: (0xbbbbbb, 255, '4500-6000', 'ft MSL'), \
                  5: (0xaaaaaa, 255, '6000-7500', 'ft MSL'), \
                  6: (0x999999, 255, '7500-9000', 'ft MSL'), \
                  7: (0x888888, 255, '9000-10500', 'ft MSL'), \
                  8: (0x777777, 255, '10500-12000', 'ft MSL'), \
                  9: (0x666666, 255, '12000-13500', 'ft MSL'), \
                  10: (0x555555, 255, '13500-15000', 'ft MSL'), \
                  11: (0x444444, 255, '15000-18000', 'ft MSL'), \
                  12: (0x333333, 255, '18000-21000', 'ft MSL'), \
                  13: (0x222222, 255, '21000-24000', 'ft MSL'), \
                  14: (0x111111, 255, '>24000', 'ft MSL'), \
                  15: (NDcolor, NDalpha, NO_DATA_STR, 'ft MSL'), \
                  255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'ft MSL'), \
}

#ffffff No Clouds
#27862f < 1500
#00f439 1500-3000
#8ffb3b 3000-4500 
#abfb4d 4500-6000
#fff93d 6000-7500
#ffa22e 7500-9000
#d56830 9000-10500
#9f5239 10500-12000
#864724 12000-13500
#a62f34 13500-15000
#b3242b 15000-18000
#7c0015 18000-21000
#8c0014 21000-24000
#f9001c >24000
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

CLOUDTOP_MAP_2 = { \
                  0: (0xffffff, 0, 'No Clouds', 'ft MSL'), \
                  1: (0x27862f, 255, '< 1500', 'ft MSL'), \
                  2: (0x00f439, 255, '1500-3000', 'ft MSL'), \
                  3: (0x8ffb3b, 255, '3000-4500', 'ft MSL'), \
                  4: (0xabfb4d, 255, '4500-6000', 'ft MSL'), \
                  5: (0xfff93d, 255, '6000-7500', 'ft MSL'), \
                  6: (0xffa22e, 255, '7500-9000', 'ft MSL'), \
                  7: (0xd56830, 255, '9000-10500', 'ft MSL'), \
                  8: (0x9f5239, 255, '10500-12000', 'ft MSL'), \
                  9: (0x864724, 255, '12000-13500', 'ft MSL'), \
                  10: (0xa62f34, 255, '13500-15000', 'ft MSL'), \
                  11: (0xb3242b, 255, '15000-18000', 'ft MSL'), \
                  12: (0x7c0015, 255, '18000-21000', 'ft MSL'), \
                  13: (0x8c0014, 255, '21000-24000', 'ft MSL'), \
                  14: (0xf9001c, 255, '>24000', 'ft MSL'), \
                  15: (NDcolor, NDalpha, NO_DATA_STR, 'ft MSL'), \
                  255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'ft MSL'), \
}

# https://hihayk.github.io/scale/#7/7/59/63/0/0/-77/47/ED0000/255/0/0/white
# used to help generate this.

#ffffff No Clouds
#d8c2c2 < 1500
#d3aeae 1500-3000
#d19797 3000-4500 
#d27d7d 4500-6000
#d56161 6000-7500
#db4343 7500-9000
#ed0000 9000-10500
#e00000 10500-12000
#d20000 12000-13500
#bf0000 13500-15000
#a90000 15000-18000
#940000 18000-21000
#7e0000 21000-24000
#6b0003 >24000
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

CLOUDTOP_MAP_3 = { \
                  0: (0xffffff, 0, 'No Clouds', 'ft MSL'), \
                  1: (0xd8c2c2, 255, '< 1500', 'ft MSL'), \
                  2: (0xd3aeae, 255, '1500-3000', 'ft MSL'), \
                  3: (0xd19797, 255, '3000-4500', 'ft MSL'), \
                  4: (0xd27d7d, 255, '4500-6000', 'ft MSL'), \
                  5: (0xd56161, 255, '6000-7500', 'ft MSL'), \
                  6: (0xdb4343, 255, '7500-9000', 'ft MSL'), \
                  7: (0xed0000, 255, '9000-10500', 'ft MSL'), \
                  8: (0xe00000, 255, '10500-12000', 'ft MSL'), \
                  9: (0xd20000, 255, '12000-13500', 'ft MSL'), \
                  10: (0xbf0000, 255, '13500-15000', 'ft MSL'), \
                  11: (0xa90000, 255, '15000-18000', 'ft MSL'), \
                  12: (0x940000, 255, '18000-21000', 'ft MSL'), \
                  13: (0x7e0000, 255, '21000-24000', 'ft MSL'), \
                  14: (0x6b0003, 255, '>24000', 'ft MSL'), \
                  15: (NDcolor, NDalpha, NO_DATA_STR, 'ft MSL'), \
                  255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'ft MSL'), \
}

# https://hihayk.github.io/scale/#7/7/59/63/0/0/-77/47/FFA232/255/162/0/white
# used to create this.

#ffffff No Clouds
#e2dad0 < 1500
#e0d1c0 1500-3000
#e0c9ad 3000-4500 
#e2c199 4500-6000
#e6b982 6000-7500
#edb169 7500-9000
#ffa232 9000-10500
#ea9528 10500-12000
#d4881e 12000-13500
#bf7b16 13500-15000
#a96d0f 15000-18000
#946009 18000-21000
#7e5204 21000-24000
#694401 >24000
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

CLOUDTOP_MAP_4 = { \
                  0: (0xffffff, 0, 'No Clouds', 'ft MSL'), \
                  1: (0xe2dad0, 255, '< 1500', 'ft MSL'), \
                  2: (0xe0d1c0, 255, '1500-3000', 'ft MSL'), \
                  3: (0xe0c9ad, 255, '3000-4500', 'ft MSL'), \
                  4: (0xe2c199, 255, '4500-6000', 'ft MSL'), \
                  5: (0xe6b982, 255, '6000-7500', 'ft MSL'), \
                  6: (0xedb169, 255, '7500-9000', 'ft MSL'), \
                  7: (0xffa232, 255, '9000-10500', 'ft MSL'), \
                  8: (0xea9528, 255, '10500-12000', 'ft MSL'), \
                  9: (0xd4881e, 255, '12000-13500', 'ft MSL'), \
                  10: (0xbf7b16, 255, '13500-15000', 'ft MSL'), \
                  11: (0xa96d0f, 255, '15000-18000', 'ft MSL'), \
                  12: (0x946009, 255, '18000-21000', 'ft MSL'), \
                  13: (0x7e5204, 255, '21000-24000', 'ft MSL'), \
                  14: (0x694401, 255, '>24000', 'ft MSL'), \
                  15: (NDcolor, NDalpha, NO_DATA_STR, 'ft MSL'), \
                  255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'ft MSL'), \
}

#---- Lightning ------------------------------------

#000000  0
#00b4f1  1
#c1d9ef  2
#5a883b 3-5
#c9e2b8 6-10
#ffff00 11-15
#c95f14 >15
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

LIGHTNING_MAP_0 = { \
                   0: (0x0, lightning0alpha, '0', 'Strike Density'), \
                   1: (0x00b4f1, 255, '1', 'Strike Density'), \
                   2: (0xc1d9ef, 255, '2', 'Strike Density'), \
                   3: (0x5a883b, 255, '3-5', 'Strike Density'), \
                   4: (0xc9e2b8, 255, '6-10', 'Strike Density'), \
                   5: (0xffff00, 255, '11-15', 'Strike Density'), \
                   6: (0xc95f14, 255, '>15', 'Strike Density'), \
                   7: (NDcolor, NDalpha, NO_DATA_STR, 'Strike Density'), \
                   255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'Strike Density'), \
}

#---- Icing Super Large Droplets ------------------------------------

#000000 <= 5
#ffff00 5-50
#ff0000 >50
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

ICING_SLD_MAP_0 = { \
                   0: (0x0, icing0alpha, '<= 5', 'SLD %'), \
                   1: (0xffff00, 255, '5-50', 'SLD %'), \
                   2: (0xff0000, 255, '>50', 'SLD %'), \
                   3: (NDcolor, NDalpha, NO_DATA_STR, 'SLD %'), \
                   255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'SLD %'), \
}

#---- Icing Severity ------------------------------------

#000000 None
#76d3ff Trace
#00ff00 Light
#ffff00 Moderate
#ff00ff Severe
#ff0000 Heavy
#000000 Reserved
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

ICING_SEV_MAP_0 = { \
                   0: (0x0, icing0alpha, 'None', 'Type'), \
                   1: (0x76d3ff, 255, 'Trace', 'Type'), \
                   2: (0x00ff00, 255, 'Light', 'Type'), \
                   3: (0xffff00, 255, 'Moderate', 'Type'), \
                   4: (0xff00ff, 255, 'Severe', 'Type'), \
                   5: (0xff0000, 255, 'Heavy', 'Type'), \
                   6: (0x0, 0, 'Reserved', 'Type'), \
                   7: (NDcolor, NDalpha, NO_DATA_STR, 'Type'), \
                   255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, 'Type'), \
}

#---- Icing Probability ------------------------------------

#000000 <= 5
#76d3ff 5-20
#00ff00 20-30
#ffff00 30-40
#f18635 40-60
#ff0000 60-80
#ff00ff >80
#b6b6b6 No Data (may vary)
#ecda96 Not Included (may vary)

ICING_PRB_MAP_0 = { \
                   0: (0x0, icing0alpha, '<= 5', '%'), \
                   1: (0x76d3ff, 255, '5-20', '%'), \
                   2: (0x00ff00, 255, '20-30', '%'), \
                   3: (0xffff00, 255, '30-40', '%'), \
                   4: (0xf18635, 255, '40-60', '%'), \
                   5: (0xff0000, 255, '60-80', '%'), \
                   6: (0xff00ff, 255, '>80', '%'), \
                   7: (NDcolor, NDalpha, NO_DATA_STR, '%'), \
                   255: (NOT_INCLUDED, NIalpha, NOT_INCL_STR, '%'), \
}

#-----------------------------------------------------------

if IMAGE_MAP_CONFIGURATION == TESTING:
    # Don't get any choices for the test image maps
    RADAR_MAP = RADAR_MAP_0
    TURB_MAP = TURB_MAP_0
    CLOUDTOP_MAP = CLOUDTOP_MAP_0
    LIGHTNING_MAP = LIGHTNING_MAP_0
    ICING_SLD_MAP = ICING_SLD_MAP_0
    ICING_SEV_MAP = ICING_SEV_MAP_0
    ICING_PRB_MAP = ICING_PRB_MAP_0
else:
    # Non-testing maps
    if cfg.RADAR_MAP == 1:
        RADAR_MAP = RADAR_MAP_1
    else:
        # Default
        RADAR_MAP = RADAR_MAP_0
    
    TURB_MAP = TURB_MAP_1

    if cfg.CLOUDTOP_MAP == 2:
        CLOUDTOP_MAP = CLOUDTOP_MAP_2
    elif cfg.CLOUDTOP_MAP == 3:
        CLOUDTOP_MAP = CLOUDTOP_MAP_3
    elif cfg.CLOUDTOP_MAP == 4:
        CLOUDTOP_MAP = CLOUDTOP_MAP_4
    elif cfg.CLOUDTOP_MAP == 0:
        CLOUDTOP_MAP = CLOUDTOP_MAP_0
    else:
        # Default
        CLOUDTOP_MAP = CLOUDTOP_MAP_1

    LIGHTNING_MAP = LIGHTNING_MAP_0
    ICING_SLD_MAP = ICING_SLD_MAP_0
    ICING_SEV_MAP = ICING_SEV_MAP_0
    ICING_PRB_MAP = ICING_PRB_MAP_0

# List of all the image maps. Used by getLegendDict().
IMAGE_MAPS = [RADAR_MAP, TURB_MAP, CLOUDTOP_MAP, LIGHTNING_MAP, \
    ICING_SLD_MAP, ICING_SEV_MAP, ICING_PRB_MAP]

# Text names of all the image maps. Must have the same length and
# be in the same order as IMAGE_MAPS. Used by getLegendDict().
IMAGE_MAP_NAMES = ['RADAR', 'TURBULENCE', 'CLOUDTOP', 'LIGHTNING', \
    'ICING_SLD', 'ICING_SEV', 'ICING_PRB']
