from flask import Flask, jsonify, request, session, redirect
import uuid
from termcolor import colored
from app import db

class SupervisedHours:

    def add_month(self,providerId, month, year, hours):

        if db.SupervisedHours.find_one_and_update({"ProviderId": providerId,"Month":month, "Year":year}, 
                                                  {'$set':{"Hours":hours}},
                                                  return_document = ReturnDocument.AFTER
                                                  )
            print('Log: ' + colored('Entry updated successfully', 'green'))
            return

        else:
            entry = {
                "ProviderId": providerId,
                "Month": month,
                "Year": year,
                "Hours": hours
            }
            if db.SupervisedHors.insert_one(entry):
                print('Log: ' + colored('Entry added successfully', 'green'))
                return
        print('Log: ' + colored('Error adding overlapping ', 'red') + f'{providerId} {month} {year} ')

