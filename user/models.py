from flask import Flask, jsonify, request
import uuid
from passlib.hash import pbkdf2_sha256
from app import db

class User:

    # create new user
    def signup(self):
        user = {
            "_id" : uuid.uuid4().hex,
            "name" : request.form.get('name'),
            "email" : request.form.get('email'),
            "password": request.form.get('password')
        }

        # encrypt the password
        user['password'] = pbkdf2_sha256.encrypt(user['password'])

        if db.users.find_one({"email":user["email"]}):
            return jsonify({"error": "Email Address Already exists"}),400

        db.users.insert_one(user)
        # print(user)

        return jsonify(user), 200