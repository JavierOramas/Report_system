from registry.models import Registry
from user import routes
from user.models import User
from flask import Flask, render_template, redirect, session, request, url_for, jsonify
from bson.objectid import ObjectId
from functools import wraps
import os
import pymongo
import json
import datetime
import math
import datetime_format
import pdfkit

app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = 'testing'

UPLOAD_FOLDER = 'static/files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database
config = {}

with open('config.json', 'r') as file:
    config = json.load(file)

client = pymongo.MongoClient(
    config['database']['addr'], config['database']['port'])
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


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(int(n)*multiplier + 0.5) / multiplier


def get_entries(role, year, month):
    entries = db.Registry.find()
    entries = [entry for entry in entries]

    temp = []
    clients = []
    dates = []
    supervisors = []

    for entry in entries:
        if datetime_format.get_date(entry["DateOfService"]).year == year and datetime_format.get_date(entry["DateOfService"]).month == month:
            entry['ProviderId'] = int(entry['ProviderId'])
            if 'providerId' in session['user'] and int(entry['ProviderId']) == int(session['user']['providerId']) and "ClientId" in entry:
                clients.append(entry['ClientId'])
                supervisors.append(entry['Supervisor'])
                dates.append(entry['DateOfService'])
                temp.append(entry)
    entries = temp
    entries = sorted(entries, key=lambda d: d['DateOfService'])

    ids = ['all']
    supervised_time = 0
    meetings = 0
    min_year = int(datetime.datetime.now().year)
    for i in entries:
        min_year = min(min_year, int(
            datetime_format.get_date(i["DateOfService"]).year))

        i['MeetingDuration'] = round_half_up(i['MeetingDuration'], 1)
        supervised_time += i['MeetingDuration']

        # TODO get this condition from other table that gives clinical meeting info
        condition = True
        if i['ProcedureCodeId'] == 194641 and condition == True:
            meetings += 1

        if 'ProviderId' in i:
            ids += list(set([i['ProviderId'] for i in entries]))
    if role == 'basic':
        # , 'Year': datetime.datetime.now().year, 'Month': datetime.datetime.now().month})
        total_hours = db.TotalHours.find_one({'ProviderId': int(
            session['user']['providerId']), 'Month': month, 'Year': year})
        if total_hours == None:
            total_hours = 0
        else:
            # print(total_hours, year ,month)
            total_hours = total_hours['TotalTime']
    else:
        total_hours = 0

    return entries, total_hours, supervised_time, ids, meetings, min_year, set(supervisors)

# routes.

# Home Page

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


# Dashboard

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
    return render_template('dashboard.html', role='admin', entries=entries, providerIds=ids, session=session)

# Dashoard for client (login Needed)


@app.route('/dashboard/')
@login_required
def dashboard(month=datetime.datetime.now().month, year=datetime.datetime.now().year):
    if 'providerId' in session['user']:
        session['user']['providerId'] = int(session['user']['providerId'])

    # Detect the role of the loged user to determine the permissions
    if 'role' in session['user'] and session['user']['role'] != None:
        role = session['user']['role']
    else:
        role = 'basic'

    # If user is not admin, remove the entries that dont belong to him/her
    if role == 'basic':
        entries, total_hours, supervised_time, ids, meetings, min_year,supervisors = get_entries(
            role, year, month)
        return render_template('dashboard.html', role=role, entries=entries, providerIds=ids, session=session, total_hours=round_half_up(total_hours), minimum_supervised=round_half_up(5/100*total_hours, 1), supervised_hours=round_half_up(supervised_time, 1), meeting_group=meetings, year=year, min_year=min_year, month=month)

    if role == 'admin':
        users = db.users.find()
        return render_template('config.html', users=users, session=session, role=role, total_hours=0, supervised_hours=0, meeting_group=0, minimum_supervised=0, year=year, month=month)
# Config

# Onlyadmins will see this page and it will let edit users and provider ids
# For now it blank


@app.route('/user/edit/<id>/')
@login_required
@admin_required
def config(id):
    user = db.users.find_one({'_id': str(id)})
    print(user)
    if user:
        return render_template('edit_user.html', user=user)


@app.route('/edit/new', methods=('GET', 'POST'))
@login_required
def add():
    if request.method == 'GET':
        entry = {
            # "entryId": entry["Id"],
            "ProviderId": session['user']['providerId'],
            "ProcedureCodeId": '',
            "TimeWorkedInHours": 0,
            "MeetingDuration": 0,
            "DateOfService": '',
            "DateTimeFrom": '',
            "DateTimeTo": '',
            "Supervisor": '',
            "ClientId": '',
            "ObservedwithClient": '',
            "ModeofMeeting": '',
            "Group":  '',
            "Individual": '',
            "Verified": False
        }
        supervisors = [1]
        return render_template('edit.html', entry=entry, supervisors=supervisors)
        # return redirect(url_for('/', message={'error':'you cant edit that entry'}))
    else:
        db.Registry.insert_one({
            "ProcedureCodeId": int(request.form.get('ProcedureCodeId')),
            "MeetingDuration": int(request.form.get("MeetingDuration")),
            "DateOfService": request.form.get('DateOfService'),
            "Verified": False
        })

        return redirect('/')


@app.route('/edit/<id>', methods=('GET', 'POST'))
@login_required
def edit(id):
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    if request.method == 'GET':
        if entry and 'providerId' in session['user'] and int(entry["ProviderId"]) == int(session['user']['providerId']):
            # print(entry)
            supervisors = [entry['Supervisor']]
            return render_template('edit.html', entry=entry, supervisors=supervisors)
        else:
            return redirect(url_for('/', message={'error': 'you cant edit that entry'}))
    else:
        if entry["ProcedureCodeId"] != request.form.get('ProcedureCodeId') or entry["DateOfService"] != request.form.get('DateOfService') or entry["MeetingDuration"] != request.form.get('MeetingDuration'):

            db.Registry.update_one({"_id": ObjectId(id)}, {"$set": {
                "ProcedureCodeId": int(request.form.get('ProcedureCodeId')),
                "MeetingDuration": int(request.form.get("MeetingDuration")),
                "DateOfService": request.form.get('DateOfService'),
                "Verified": False
            }})

        return redirect('/')


@app.route('/del/<id>', methods=('GET', 'POST'))
@login_required
def delete(id):
    if session['user']['role'] == 'admin' and db.users.find_one({"_id": ObjectId(id)}):
        db.users.delete_one({"_id": ObjectId(id)})

    return redirect('/users/')


@app.route('/user/signup/', methods=['POST'])
def signup():
    return User().signup()


@app.route('/user/login/', methods=['POST'])
def login():
    return User().login(db)


@app.route('/user/signout/')
def signout():
    return User().signout()


@app.route('/user/logout/')
def logout():
    pass


@app.route('/upload/', methods=['POST', 'GET'])
def upload():
    Registry().add_data(db)
    return redirect('/')

@app.route("/filter/", methods=['POST', 'GET'])
def filter_data():
    month = request.form.get('month')
    year = request.form.get('year')
    # return redirect(url_for('dashboard', year=year, month=month))
    return dashboard(int(month), int(year))

@app.route("/filter/<year>/<month>", methods=['POST', 'GET'])
def filter_data_args(year,month):
    # return redirect(url_for('dashboard', year=year, month=month))
    return dashboard(int(month), int(year))

@app.route("/report/<year>/<month>/")
def get_report(year, month):
    # Detect the role of the loged user to determine the permissions
    if 'role' in session['user'] and session['user']['role'] != None:
        role = session['user']['role']
    else:
        role = 'basic'

    year = int(year)
    month = int(month)
    user = session['user']
    entries, total_hours, supervised_time, ids, meetings, min_year,supervisors = get_entries(
        role, year, month)
    if user and entries:
        user['hired_date'] = ' '
        month_year = f'{month} {year}'

        # supervisors = list(supervisors)
        # print(supervisors)
        supervisors = list(db.user.find({'ProviderId':{'$in': supervisors}}))
        # print(supervisors)
        template = render_template(
            'report_rbt.html', rbt_name=user['name'], hired_date=user['hired_date'], month_year=month_year, entries=entries, total_hours=round_half_up(total_hours,2),minimum_supervision_hours=round(total_hours*0.05,1), supervised_hours=round_half_up(supervised_time), supervisors=supervisors)
        options = {
        'page-size': 'A4',
        'enable-local-file-access': None, # to avoid blanks
        'javascript-delay': 1000,
        'no-stop-slow-scripts': None,
        'debug-javascript': None,
        'enable-javascript': None
    }

        # print('ready')
        pdfkit.from_string(template,'report.pdf')
        # print(template)
        return redirect(f'/filter/{year}/{month}')
    else:
        print("Something went Wrong!")
        return dashboard(year, month)
