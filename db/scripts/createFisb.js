// create new fisb database and associated collections

// Drop any current database
conn = new Mongo();
db = conn.getDB("fisb");
db.dropDatabase();

// Create new database
conn = new Mongo();
db = conn.getDB("fisb");
db.createCollection('METAR')
db.createCollection('TAF')
db.createCollection('CRL_8')
db.createCollection('CRL_11')
db.createCollection('CRL_12')
db.createCollection('CRL_14')
db.createCollection('CRL_15')
db.createCollection('CRL_16')
db.createCollection('CRL_17')
db.createCollection('PIREP')
db.createCollection('SUA')
db.createCollection('WINDS_06_HR')
db.createCollection('WINDS_12_HR')
db.createCollection('WINDS_24_HR')
db.createCollection('NOTAM')
db.NOTAM.createIndex( { location: 1}, { unique:false} );

db.createCollection('NOTAM_TFR')
db.createCollection('SIGWX')
db.createCollection('SERVICE_STATUS')
db.createCollection('G_AIRMET')
db.createCollection('FIS_B_UNAVAILABLE')
db.createCollection('RSR')
db.createCollection('LEGEND')
