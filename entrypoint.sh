#!/bin/bash

# Start MongoDB in the background
mongod --fork --logpath /var/log/mongod.log

# Populate the database
python3 populate_db.py

# Run the Python code
exec python3 wsgi.py
