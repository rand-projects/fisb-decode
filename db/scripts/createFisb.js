// create new fisb database and associated collections

// Drop any current database
conn = new Mongo();
db = conn.getDB("fisb");
db.dropDatabase();

// Create new database
conn = new Mongo();
db = conn.getDB("fisb");
db.createCollection('MSG')
db.MSG.createIndex({unique_name: 1})
db.MSG.createIndex({type: 1})
db.MSG.createIndex({insert_time: 1})
db.MSG.createIndex({expiration_time: 1})

db.createCollection('STATIC')
