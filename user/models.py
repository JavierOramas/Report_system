from flask import Flask, jsonify, request, session, redirect
import uuid
from passlib.hash import pbkdf2_sha256
from app import db

class User:

    # Create Session for logged user
    def start_session(self, user):
        del user['password']
        session['logged_in'] = True
        session['user'] = user
        return jsonify(user), 200

    # create new user
    def signup(self):

        user = {
            "_id" : uuid.uuid4().hex,
            "name" : request.form.get('name'),
            "email" : request.form.get('email'),
            "password": request.form.get('password'),
            "providerId": request.form.get('providerId'),
            "providertype":request.form.get('providerType'),
            "role": 'basic',
            "active": False,
        }

        # encrypt the password
        user['password'] = pbkdf2_sha256.encrypt(user['password'])

        # Verify uniqueness of the user and insert it in the database if no error
        if db.users.find_one({"email":user["email"]}) or db.users.find_one({"providerId":user["providerId"]}):
            return jsonify({"error": "Email Address or ProviderId Already exists"}),400

        if db.users.insert_one(user):
            return self.start_session(user)

        # If this is reached something wrong Happened
        return jsonify({"error":"Sign Up failed"}), 400

    def login(self):

        # Find user and login
        user = {
            "email" : request.form.get('email'),
        }
        user = db.users.find_one(user)
        if user and pbkdf2_sha256.verify(request.form.get('password'), user['password']):
            return self.start_session(user)

        # If this is reached something wrong Happened
        return jsonify({"error":"Login failed"}), 401

    def signout(self):
        session.clear()
        return redirect('/')
