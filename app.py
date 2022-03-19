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

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'role' in session['user']:
            if session['user']['role'] == 'admin':
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
    if 'logged_in' in session:
        return redirect('/dashboard/')
    return render_template('home.html', register=False)
# Home Route With Regiter form
@app.route('/register/')
def register():
    types = ['None'] + [i['type'] for i in db.providerType.find()]
    return render_template('home.html', register=True, types=types)


### Dashboard

# Post endpoint to upoad file
@app.route("/dashboard/", methods=['POST'])
@login_required
@admin_required
def upload_files():
      # get the uploaded file
      uploaded_file = request.files['file']
      if uploaded_file.filename != '':
           file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.csv')
          # set the file path
           uploaded_file.save(file_path)
          # save the file
      return redirect(url_for('upload'))

@app.route("/dashboard/providers/", methods=['POST'])
@login_required
@admin_required
def upload_file():
      # get the uploaded file
      uploaded_file = request.files['file']
      if uploaded_file.filename != '':
           file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.csv')
          # set the file path
           uploaded_file.save(file_path)
          # save the file
      return redirect(url_for('upload-providers'))

@app.route('/providers/')
@login_required
@admin_required
def providers():

    entries = db.user.find()
    return render_template('dashboard.html', role='admin', entries=entries, providerIds=ids, session = session)

# Dashoard for client (login Needed)
@app.route('/dashboard/')
@login_required
def dashboard():
    if 'providerId' in session['user']:
        session['user']['providerId'] = int(session['user']['providerId'])
    # Find all the entries
    entries = db.Registry.find()
    entries = [entry for entry in entries]

    # Detect the role of the loged user to determine the permissions
    if 'role' in session['user'] and session['user']['role'] != None:
        role = session['user']['role']
    else:
        role = 'basic'

    # If user is not admin, remove the entries that dont belong to him/her 
    if role == 'basic':
        temp = []
        clients = []
        dates = []
        for entry in entries:
            entry['ProviderId'] = int(entry['ProviderId'])
            # print(int(session['user']['providerId']))
            if 'providerId' in session['user'] and int(entry['ProviderId']) == int(session['user']['providerId']) and "ClientId" in entry:
                clients.append(entry['ClientId'])
                dates.append(entry['DateOfService'])
                temp.append(entry)
        entries = temp
        entries = sorted(entries, key=lambda d: d['DateOfService']) 
    print(len(entries))
    ids = ['all']
    for i in entries:
        # print(i)
        if 'ProviderId' in i:
            ids += list(set([i['ProviderId'] for i in entries]))

    return render_template('dashboard.html', role=role, entries=entries, providerIds=ids, session = session)

### Config

# Onlyadmins will see this page and it will let edit users and provider ids
# For now it blank
@app.route('/config/')
@login_required
def config():
    if session['user']['role'] == 'admin':
        return render_template('config.html')