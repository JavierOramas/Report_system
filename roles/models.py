from flask import Flask, jsonify, request, session, redirect
import uuid
from passlib.hash import pbkdf2_sha256
import pandas as pd
import datetime
import os
from termcolor import colored
import datetime_format
# from app import db


class Role:

    # create new user
    def add_role(self):
        role = {
            "role_name": request.form.get('role_name').lower(),
        }
        # Verify uniqueness of the user and insert it in the database if no error
        # or db.users.find_one({"providerId":user["providerId"]}):
        if db.roles.find_one({"role_name": role["role_name"]}):
            return jsonify({"error": "Role Name Already exists"}), 400

        if db.users.insert_one(role):
            return self.start_session(role)

        # If this is reached something wrong Happened
        return jsonify({"error": "Role Creation failed"}), 400

    def delete_role(self, role_id):
        # Delete the role
        if db.roles.delete_one({"_id": role_id}):
            return {'status': 200}
        else:
            return {'status': 400}
