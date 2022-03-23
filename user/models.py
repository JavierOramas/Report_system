from flask import Flask, jsonify, request, session, redirect
import uuid
from passlib.hash import pbkdf2_sha256
from app import db

class User:

    # Create Session for logged user
    def start_session(self, user):
        del user['password']
        del user['_id']
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
            "providerId":               request.form.get('providerId'),
        }

        # encrypt the password
        user['password'] = pbkdf2_sha256.encrypt(user['password'])

        # Verify uniqueness of the user and insert it in the database if no error
        if db.users.find_one({"email":user["email"]}): #or db.users.find_one({"providerId":user["providerId"]}):
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

    def add_data(self):
            # Load data from csv pre-loaded from the client
        # data = pd.read_csv('static/files/data.csv')
        
        # crete the collection entries
        for index,entry in data.iterrows():
            entry['DateTimeFrom'] = datetime.datetime.strptime(entry['DateTimeFrom'], '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')
            entry['DateTimeTo'] = datetime.datetime.strptime(entry['DateTimeTo'], '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')
            entry['DateOfService'] = datetime.datetime.strptime(entry['DateOfService'], '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')
            entry = {
                "_id":                      entry['ProviderId'],
                "name":                     entry['Name and Credential'],
                "first_name":               entry['ProviderFirstName'],
                "last_name":                entry['ProviderLastName'],
                "BACB_id":                  entry['BACB Account ID'],
                "credential":               entry['Credential'],
                "role":                     entry['Role'],
                "hired_date":               entry['Hired Date'],
                "fingerprint_background":   entry['DateOfService'],
                "background_date":          entry['Background Screening Date'],
                "background_exp_date":      entry['Background Screening'],
            }

            # Insert the data and log to the console the action
            if db.users.insert_one(entry):
                print('Log: ' + colored('Entry added successfully', 'green'))
            else:
                print('Log: ' + colored(f'Error adding entry to database \n {entry}', 'red'))
        # Return success code
        return {'status': 200}