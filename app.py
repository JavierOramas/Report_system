from flask import Flask, render_template, redirect, session, request, url_for, jsonify
from functools import wraps
import os
import pymongo
import json

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
@app.route('/')
def home():
    # print('here')
    return render_template('home.html')


# Get the uploaded files
@app.route("/dasboard/", methods=['POST'])
def uploadFiles():
      # get the uploaded file
      uploaded_file = request.files['file']
      if uploaded_file.filename != '':
           file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.csv')
          # set the file path
           uploaded_file.save(file_path)
          # save the file
      return redirect(url_for('upload'))


@app.route('/dashboard/')
@login_required
def dashboard():
    entries = db.Registry.find()
    entries = [entry for entry in entries]
    user = session
    return render_template('dashboard.html', user=user, entries=entries)


@app.route('/config/')
@login_required
def config():
    return render_template('config.html')