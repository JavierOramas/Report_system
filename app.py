from flask import Flask, render_template, redirect, session, request, url_for, jsonify
from functools import wraps
import os
import pymongo
import json
import datetime

app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = 'testing'

UPLOAD_FOLDER = 'static/files'
app.config['UPLOAD_FOLDER'] =  UPLOAD_FOLDER

#Database
config = {}

with open('config.json', 'r') as file:
    config = json.load(file)

client = pymongo.MongoClient(config['database']['addr'], config['database']['port'])
db = client.abs_tracking_db

# Decorators
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect('/')
    return wrap

#routes
from user import routes
from registry import routes

### Home Page

# Home Route with login form
@app.route('/')
def home():
    return render_template('home.html', register=False)
# Home Route With Regiter form
@app.route('/register/')
def register():
    return render_template('home.html', register=True)


### Dashboard

# Post endpoint to upoad file
@app.route("/dashboard/", methods=['POST'])
@login_required
def upload_files():
      # get the uploaded file
      uploaded_file = request.files['file']
      if uploaded_file.filename != '':
           file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.csv')
          # set the file path
           uploaded_file.save(file_path)
          # save the file
      return redirect(url_for('upload'))

# Dashoard for client (login Needed)
@app.route('/dashboard/')
@login_required
def dashboard():

    # Find all the entries
    entries = db.Registry.find()
    entries = [entry for entry in entries]

    # Detect the role of the loged user to determine the permissions
    if 'role' in session['user']:
        role = session['user']['role']
    else:
        role = 'basic'

    # If user is not admin, remove the entries thet dont belong to him/her 
    if role == 'basic':
        temp = []
        for entry in entries:
            if 'providerId' in session['user'] and int(entry['ProviderId']) == int(session['user']['providerId']):
                temp.append(entry)

        entries = temp

    return render_template('dashboard.html', role=role, entries=entries)

### Config

# Onlyadmins will see this page and it will let edit users and provider ids
# For now it blank
@app.route('/config/')
@login_required
def config():
    if session['user']['role'] == 'admin':
        return render_template('config.html')