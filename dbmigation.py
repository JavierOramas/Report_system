import pymongo
import json
from bson.objectid import ObjectId

config = {}

with open('config.json', 'r') as file:
    config = json.load(file)

client = pymongo.MongoClient(
    config['database']['addr'], config['database']['port'])
db = client.abs_tracking_db

db.Registry.update_many({}, {"$set": {
    "MeetingForm": False,
}})

