from logger import log
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
            min_year = db.min_year.find_one({})['year']
        except TypeError:
            min_year = datetime.datetime.now().year
            db.min_year.delete_one({})
            db.min_year.insert_one({
                'year': min_year
            })
        try:
            data = pd.read_csv('static/files/data.csv')
        except:
            return {'status': 500}
        labels = ['ProviderId', 'TimeWorkedInHours', 'ProcedureCodeId']

        month = datetime.datetime.strptime(
            data['DateOfService'].iloc[0], '%m/%d/%Y %H:%M').month
        year = datetime.datetime.strptime(
            data['DateOfService'].iloc[0], '%m/%d/%Y %H:%M').year
        if int(year) < int(min_year):
            min_year = year
        data = data.drop(data.columns.difference(labels), 1)

        labels = [150580, 150582, 150583, 150553, 194640, 298632,
                  194641, 194641, 235184, 255975, 255910, 241573]

        df = data[data['ProcedureCodeId'] != 194642]
        df = df[df['ProcedureCodeId'] != 208672]
        df = df[df['ProcedureCodeId'] != 232824]
        df = df[df['ProcedureCodeId'] != 189444]
        df = df[df['ProcedureCodeId'] != 256962]
        idx = 0
        for i in labels:
            if idx != 0:
                data_for_time.append(
                    df[df['ProcedureCodeId'] == i], ingnore_index=True)
            else:
                data_for_time = df[df['ProcedureCodeId'] == i]

        data_for_time = df

        try:
            data_for_time['TimeWorkedInHours'] = data['TimeWorkedInHours'].apply(
                lambda x: x.replace(',', '.')).astype(float)
        except:
            data_for_time['TimeWorkedInHours'] = data['TimeWorkedInHours'].astype(
                float)
        total_time = data_for_time.groupby(['ProviderId']).sum()

        for name, entry in total_time.iterrows():

            item = {
                'ProviderId': name,
                'Month': month,
                'Year': year,
                'TotalTime': round(entry['TimeWorkedInHours'], 4)
            }
            if not db.TotalHours.find_one({'ProviderId': name, 'Month': month, 'Year': year}):
                db.TotalHours.insert_one(item)

        data = process('static/files/data.csv', 'providers.csv', db=db)
        # create the collection entries
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
                "Verified": True,
                "MeetingForm": False
            }

            entry['DateTimeFrom'] = datetime_format.format(
                entry['DateTimeFrom'])
            entry['DateTimeTo'] = datetime_format.format(entry['DateTimeTo'])
            entry['DateOfService'] = datetime_format.format(
                entry['DateOfService'])

            supervisor = db.users.find_one({'ProviderId': entry['Supervisor']})
            if not entry['MeetingDuration'] < 0 and supervisor != None:

                found = db.Registry.find_one({"ProviderId": entry['ProviderId'], "entryId": entry['entryId']})
                # print(found)
                same = True
                entry_without_id = {key: entry[key] for key in entry if key != "_id"}
                found_without_id = {key: found[key] for key in found if key != "_id"} if found else None
                if entry_without_id != found_without_id:
                    same = False
                
                if not found or not same:
                    # print(entry)
                    db.Registry.insert_one(entry)
                elif int(found['ProcedureCodeId']) in [194640, 194592] and entry["ProcedureCodeId"] != found['ProcedureCodeId']:
                    # db.Registry.delete_one({'_id': found['_id']})
                    db.Registry.insert_one(entry)
                
        db.min_year.delete_one({})
        db.min_year.insert_one({
            'year': min_year
        })
        return {'status': 200}
