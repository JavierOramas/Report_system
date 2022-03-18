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
    
    def get_55_code(self):
        return [150582, 194640]
    # Declare the model for the collection that will be added to MongoDB database
    def get_observed(self,entry):

        if entry["ProcedureCodeId"] in [255975]:
            return 'yes','Remote'

        if entry["ProcedureCodeId"] in self.get_55_code():
            return 'yes','In Person'
        else:
            return 'no','Remote'

    def get_group_individual(self,entry):
        if entry["ProcedureCodeId"] in [194641]:
            return 'yes','no'
        else:
            return 'no','yes'

    def add_data(self):
        # Load data from csv pre-loaded from the client
        try:
            data = pd.read_csv('static/files/data.csv')
        except:
            return {'status' : 500}

        data = process('static/files/data.csv', 'providers.csv')

            # crete the collection entries
        for index,entry in data.iterrows():
            entry = {
                "ProviderId": entry["Id"],
                "ProcedureCodeId": entry["ProcedureCodeId"],
                "TimeWorkedInHours": entry["TimeWorkedInHours"],
                "MeetingDuration": entry["MeetingDuration"],
                "DateOfService": entry['DateOfService'],
                "DateTimeFrom": entry['DateTimeFrom'],
                "DateTimeTo": entry['DateTimeTo'],
                "Supervisor": entry["ProviderId"],
                "ClientId": entry["ClientId"],
                "ObservedwithClient": self.get_observed(entry)[0],
                "ModeofMeeting": self.get_observed(entry)[1],
                "Group":  self.get_group_individual(entry)[0],
                "Individual": self.get_group_individual(entry)[1],
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
    # except:
        # pass
            #TODO notify errors