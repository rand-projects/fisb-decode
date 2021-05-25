"""LocationDb configuration information.
"""

#: MongoDb URI where fisb_location DB is located.
MONGO_URI = 'mongodb://localhost:27017/'

#: Directory to store the intermediate coordinates
#: for finding declination. Also where the
#: results are written to.
DECLINATION_DIR = '/tmp'

#: Where the program ``wmm_file`` is located.
WMM_FILE_HOME = '/home/mbarnes/WMM2020_Linux/bin'
