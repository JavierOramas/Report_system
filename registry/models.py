from flask import Flask, jsonify, request, session, redirect
import uuid
# from passlib.hash import pbkdf2_sha256
from termcolor import colored
from overlappings.tools import get_supervisor_codes, process
import pandas as pd
# from app import db
import datetime
import os
import datetime_format
from super_roles.super_roles import get_admins, get_supervisors


class Registry:

    def get_55_code(self):
        return [150582, 194640]
    # Declare the model for the collection that will be added to MongoDB database

    def get_observed(self, entry):

        if entry["ProcedureCodeId"] in [255975]:
            return 'yes', 'Remote'

        if entry["ProcedureCodeId"] in self.get_55_code():
            return 'yes', 'In Person'
        else:
            return 'no', 'Remote'

    def get_group_individual(self, entry):
        if entry["ProcedureCodeId"] in [194641]:
            return 'yes', 'no'
        else:
            return 'no', 'yes'

    def add_data(self, db):
        # Load data from csv pre-loaded from the client
        try:
            data = pd.read_csv('static/files/data.csv')
        except:
            return {'status': 500}
        labels = ['ProviderId', 'TimeWorkedInHours']

        month = datetime.datetime.strptime(
            data['DateOfService'].iloc[0], '%m/%d/%Y %H:%M').month
        year = datetime.datetime.strptime(
            data['DateOfService'].iloc[0], '%m/%d/%Y %H:%M').year
        data = data.drop(data.columns.difference(labels), 1)
        try:
            data['TimeWorkedInHours'] = data['TimeWorkedInHours'].apply(
                lambda x: x.replace(',', '.')).astype(float)
        except:
            data['TimeWorkedInHours'] = data['TimeWorkedInHours'].astype(float)
        total_time = data.groupby(['ProviderId']).sum()

        for name, entry in total_time.iterrows():
            # entry['ProviderId'] = entry['Name']
            item = {
                'ProviderId': name,
                'Month': month,
                'Year': year,
                'TotalTime': entry['TimeWorkedInHours']
            }

            if not db.TotalHours.find_one({'ProviderId': name, 'Month': month, 'Year': year}):
                db.TotalHours.insert_one(item)

        data = process('static/files/data.csv', 'providers.csv')
        # crete the collection entries
        for index, entry in data.iterrows():
            entry = {
                "entryId": entry["Id"],
                "ProviderId": entry["ProvId"],
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
                "Verified": True
            }

            entry['DateTimeFrom'] = datetime_format.format(
                entry['DateTimeFrom'])
            entry['DateTimeTo'] = datetime_format.format(entry['DateTimeTo'])
            entry['DateOfService'] = datetime_format.format(
                entry['DateOfService'])

            supervisor = db.users.find_one({'ProviderId': entry['Supervisor']})
            print(entry['Supervisor'])
            print(supervisor)
            if not entry['MeetingDuration'] < 1 and supervisor != None and supervisor['role'] in get_supervisors():
        # Insert the data and log to the console the action
                if not db.Registry.find_one({"ProviderId": entry['ProviderId'], "entryId": entry['entryId']}):
                    db.Registry.insert_one(entry)
            # print('Log: ' + colored('Entry added successfully', 'green'))
        # else:
            # print('Log: ' + colored(f'Error adding entry to database \n {entry}', 'red'))
    # Return success code
    # errors, notif, ol = process(db.Registry.find())
        return {'status': 200}
    # except:
        # pass
        # TODO notify errors
