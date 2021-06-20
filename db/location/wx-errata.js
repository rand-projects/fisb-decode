// Add missing items to WX collection

// Commands to find stations with missing location information:
//
// use fisb
// db.MSG.find({'type': 'METAR', 'geojson': {$exists: false}}).pretty()
// db.MSG.find({'type': 'WINDS_06_HR', 'geojson': {$exists: false}}).pretty()

// Connect to database
conn = new Mongo();
db = conn.getDB("fisb_location");

// Add missing items
db.WX.replaceOne({"_id": "KK62"},{"_id": "KK62", "coordinates": [-84.391833, 38.704083]},{upsert: true})
db.WX.replaceOne({"_id": "KSMD"},{"_id": "KSMD", "coordinates": [-85.152778, 41.143361]},{upsert: true})
