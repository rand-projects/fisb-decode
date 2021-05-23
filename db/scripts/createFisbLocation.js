// create new fisb_location database and associated collections

// Drop any current database
conn = new Mongo();
db = conn.getDB("fisb_location");
db.dropDatabase();

// Create new database
conn = new Mongo();
db = conn.getDB("fisb_location");
db.createCollection('AIRPORTS')
db.createCollection('NAVAIDS')
db.createCollection('DESIGNATED_POINTS')
