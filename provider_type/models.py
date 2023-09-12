from flask import Flask, jsonify, request, session, redirect
import uuid
# from termcolor import colored
from app import db

class ProviderType:
    
    def add_entry(self, name):
        if not db.ProviderType.find_one({"type" : name}):
            db.ProviderType.insert_one(
                {"type" : name}
            )
            # print("Log: " + colored("New provider category added", "green"))
            return
        # print("Log: " + colored("Errors Occurred", "red"))