from flask import Flask, jsonify, request, session, redirect
import uuid
# from passlib.hash import pbkdf2_sha256
from termcolor import colored
import pandas as pd
from app import db
import os

class Registry:

    def add_data(self):
        data = pd.read_csv('static/files/data.csv')
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
        
            if db.Registry.insert_one(entry):
                print('Log: ' + colored('Entry added successfully', 'green'))
            else:
                print('Log: ' + colored(f'Error adding entry to database \n {entry}', 'red'))
        return {'status': 200}