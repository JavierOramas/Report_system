from flask import Flask, jsonify, request, session, redirect
import uuid
# from passlib.hash import pbkdf2_sha256
from termcolor import colored
from overlappings.tools import process
import pandas as pd
from app import db
import datetime
import os


class Registry:
    # Declare the model for the collection that will be added to MongoDB database
    def add_data(self):
        # Load data from csv pre-loaded from the client
        try:
            data = pd.read_csv('static/files/data.csv')

            data =process('static/files/data.csv', 'providers.csv')

            # crete the collection entries
            for index,entry in data.iterrows():
                entry = {
                    "TimeWorkedInHours": entry["TimeWorkedInHours"],
                    "MeetingDuration": entry["MeetingDuration"],
                    "DateOfService": entry['DateOfService'],
                    "DateTimeFrom": entry['DateTimeFrom'],
                    "DateTimeTo": entry['DateTimeTo'],
                    "individual": 'No',
                    "Group": 'No',
                    "ModeofMeeting": "no",
                    "ObservedwithClient": "no",
                    "Supervisor": entry["ProviderId"],
                    "ClientId": entry["ClientId"],
                    "ProviderId": entry["Id"],
                    "ProcedureCodeId": entry["ProcedureCodeId"]
                }

                entry['DateTimeFrom'] = datetime.datetime.strptime(entry['DateTimeFrom'], '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')
                entry['DateTimeTo'] = datetime.datetime.strptime(entry['DateTimeTo'], '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')
                entry['DateOfService'] = datetime.datetime.strptime(entry['DateOfService'], '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')

            # Insert the data and log to the console the action
            # if not db.Registry.find_one({"_id":entry['_id']}):
                db.Registry.insert_one(entry)
                # print('Log: ' + colored('Entry added successfully', 'green'))
            # else:
                # print('Log: ' + colored(f'Error adding entry to database \n {entry}', 'red'))
        # Return success code
        # errors, notif, ol = process(db.Registry.find())
            return {'status': 200}
        except:
            pass
            #TODO notify errors