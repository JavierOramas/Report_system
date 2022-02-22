from flask import Flask, jsonify, request, session, redirect
import uuid
# from passlib.hash import pbkdf2_sha256
from termcolor import colored
import pandas as pd
from app import db
import os

class Registry:
    # Declare the model for the collection that will be added to MongoDB database
    def add_data(self):
        # Load data from csv pre-loaded from the client
        data = pd.read_csv('static/files/data.csv')
        # crete the collection entries
        for index,entry in data.iterrows():
            entry = {
                "_id":              uuid.uuid4().hex,
                "DateTimeFrom":     entry['DateTimeFrom'],
                "DateTimeTo":       entry['DateTimeTo'],
                "ProviderId":       entry['ProviderId'],
                "ClientId":         entry['ClientId'],
                "ProcedureCodeId":  entry['ProcedureCodeId'],
                "DateOfService":    entry['DateOfService'],
            }

            # Insert the data and log to the console the action
            if db.Registry.insert_one(entry):
                print('Log: ' + colored('Entry added successfully', 'green'))
            else:
                print('Log: ' + colored(f'Error adding entry to database \n {entry}', 'red'))
        # Return success code
        return {'status': 200}