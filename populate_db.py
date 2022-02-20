import os
import pymongo
import json
import uuid
from passlib.hash import pbkdf2_sha256


def signup(name, email, passwd):
    
        user = {
            "_id" : uuid.uuid4().hex,
            "name" : name,
            "email" : email,
            "password": passwd,
            "role": 'admin',
            "active": True,
        }

        # encrypt the password
        user['password'] = pbkdf2_sha256.encrypt(user['password'])

        if db.users.find_one({"email":user["email"]}):
            return jsonify({"error": "Email Address Already exists"}),400

        if db.users.insert_one(user):
            return user

        return jsonify({"error":"Sign Up failed"}), 400

#Database
config = {}

with open('config.json', 'r') as file:
    config = json.load(file)

client = pymongo.MongoClient(config['database']['addr'], config['database']['port'])
db = client.abs_tracking_db

name = input("Admin account name: ")
passwd = input("Admin account password: ")
email = input("Admin account email: ")

print(signup(name, email, passwd))