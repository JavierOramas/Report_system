import email
from flask import Flask, jsonify, request, session, redirect
import uuid
from passlib.hash import pbkdf2_sha256
import pandas as pd
import datetime
import os
from termcolor import colored
import datetime_format
# from app import db


class User:

    # Create Session for logged user
    def start_session(self, user):
        del user['password']
        # del user['_id']
        user['_id'] = str(user['_id'])
        session['logged_in'] = True
        session['user'] = user
        return jsonify(user), 200

    # create new user
    def signup(self):
        user = {
            "name":                     request.form.get('name'),
            "role":                     'basic',
            "password":                 request.form.get('password'),
            "email":                    request.form.get('email'),
            "ProviderId":               request.form.get('providerId'),
        }

        # encrypt the password
        user['password'] = pbkdf2_sha256.encrypt(user['password'])

        # Verify uniqueness of the user and insert it in the database if no error
        # or db.users.find_one({"providerId":user["providerId"]}):
        if db.users.find_one({"email": user["email"]}):
            return jsonify({"error": "Email Address or ProviderId Already exists"}), 400

        if db.users.insert_one(user):
            return self.start_session(user)

        # If this is reached something wrong Happened
        return jsonify({"error": "Sign Up failed"}), 400

    def login(self, db):

        # Find user and login
        user = {
            "email": request.form.get('email'),
        }
        user = db.users.find_one({'email':request.form.get('email')})
        if user and pbkdf2_sha256.verify(request.form.get('password'), user['password']):
            return self.start_session(user)

        # If this is reached something wrong Happened
        return jsonify({"error": "Login failed"}), 401

    def signout(self):
        session.clear()
        return redirect('/')

    def add_data(self, db):
        # Load data from csv pre-loaded from the client
        data = pd.read_csv('static/files/data.csv', dtype={ 'Credential':str, 'Hired Date':str, 'Background Screening Date':str, 'Background Screening':str})
        # crete the collection entries
        for index, entry in data.iterrows():
            item = {
                "ProviderId": entry['ProviderId'],
                "name": f'{entry["ProviderFirstName"]} {entry["ProviderLastName"]} {entry["Credential"]}',
                "email": entry["Email"],
                "first_name": entry["ProviderFirstName"],
                "last_name": entry["ProviderLastName"],
                "BACB_id": entry["BACB Account ID"],
                "credential": entry["Credential"],
                "role": entry["Status"],
                "background_screening_type" : entry["Background Screening Type"], 
            }
            
            try:
                if 'Hired Date' in entry and entry['Hired Date'] != None and entry['Hired Date'] != '':
                    item["hired_date"]= datetime.datetime.strptime(entry['Hired Date'], '%m/%d/%Y').strftime('%m/%d/%y')
            except:
                pass
            try:
                if 'Background Screening Date' in entry and entry['Background Screening Date'] != None and entry['Background Screening Date'] != '':
                    item["background_date"]= datetime.datetime.strptime(str(entry['Background Screening Date']), '%m/%d/%Y').strftime('%m/%d/%Y')
            except:
                try:
                    if 'Background Screening Date' in entry and entry['Background Screening Date'] != None and entry['Background Screening Date'] != '':
                        item["background_date"]= datetime.datetime.strptime(str(entry['Background Screening Date']), '%m/%d/%y').strftime('%m/%d/%Y')
                except:
                    # print("failed to parse date screening")
                    pass

            try:
                if 'Background Screening ' in entry and entry['Background Screening '] != None and entry['Background Screening '] != '':
                    item["background_exp_date"]= datetime.datetime.strptime(str(entry['Background Screening ']), '%m/%d/%Y').strftime('%m/%d/%Y')
            except:
                try:
                    if 'Background Screening ' in entry and entry['Background Screening '] != None and entry['Background Screening '] != '':
                        item["background_exp_date"]= datetime.datetime.strptime(str(entry['Background Screening ']), '%m/%d/%y').strftime('%m/%d/%Y')
                except:
                    pass

            if db.users.find_one({"ProviderId": item["ProviderId"]}) in [[], None, False] and db.users.find_one({"ProviderId": str(item["ProviderId"])}) in [[], None, False]:
                # Insert the data and log to the console the action
                try:
                    db.users.insert_one(item)
                except:
                    pass
            else:
                db.users.update_one({'ProviderId': item["ProviderId"]}, {'$set': item})
                
        return {'status': 200}
