from cmath import nan
from inspect import signature
from time import sleep
from logger import log
from colorama import Cursor
import pandas as pd
from registry.models import Registry
from super_roles.super_roles import get_admins, get_supervisors
from user import routes
from user.models import User
from flask import Flask, render_template, redirect, session, request, url_for, jsonify, send_file, flash
from bson.objectid import ObjectId
from functools import wraps
import os
import pymongo
import json
import datetime
import math
import datetime_format
import pdfkit
from passlib.hash import pbkdf2_sha256
from utils import get_rbt_coordinator, get_second_monday, round_half_up
from roles.models import get_all_roles
from sup_view import inspect_supervisor
from werkzeug.utils import secure_filename
from flask_sslify import SSLify

app = Flask(__name__)

# Enforce SSL
sslify = SSLify(app)


# Configuration
app.secret_key = 'testing'

UPLOAD_FOLDER = 'static/files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_database_name():
    try:
        with open("database_name.txt") as d:
            name = d.read().strip()

        if name:
            return name
        else:
            return 'abs_tracking_db'
    except FileNotFoundError:
        return 'abs_tracking_db'

def initialize_database():
    try:
        with open('config.json', 'r') as file:
            config = json.load(file)
    except FileNotFoundError:
        # print("Error: 'config.json' file not found.")
        return None

    try:
        client = pymongo.MongoClient(config['database']['addr'], config['database']['port'], connect=False)
        db_name = get_database_name()
        db = client[db_name]
        print("OK")
        return db
    except Exception as e:
        # print(f"Error initializing the database: {str(e)}")
        return None

db = initialize_database()

# Decorators
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        log(args)
        log(kwargs)
        if 'logged_in' in session:
            log("redirecting to the called site")
            return f(*args, **kwargs)
        else:
            log("redirecting to login")
            return redirect('/')
    return wrap


def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user' in session and 'role' in session['user']:
            allowed_roles = get_admins()
            if session['user']['role'].lower() in allowed_roles:
                return f(*args, **kwargs)
        return redirect('/')
    return wrap


import datetime

def get_entries(role, year, month, user):
    entries = []
    total_hours = 0
    supervised_time = 0
    ids = []
    meetings = 0
    min_year = datetime.datetime.now().year
    supervisors = set()
    observed_with_client = 0
    face_to_face = 0

    if 'providerId' not in user:
        if 'ProviderId' in user and user['ProviderId'] != '' and user['ProviderId'] is not None:
            user['providerId'] = user['ProviderId']
        else:
            return entries, total_hours, supervised_time, ids, meetings, min_year, supervisors, observed_with_client, face_to_face

    year = int(year)
    month = int(month) 
    
    db = initialize_database()
    entries_query = list(db.Registry.find({'ProviderId': int(user['providerId'])}))
    for entry in entries_query:
        entry_year = datetime_format.get_date(entry["DateOfService"]).year
        entry_month = datetime_format.get_date(entry["DateOfService"]).month
        print(entry_year, entry_month)
        print("filter", year, month)
        if entry_year < min_year:
            min_year = entry_year

        if (entry_year == year or entry_year + 2000 == year) and entry_month == month:
            entry['ProviderId'] = int(entry['ProviderId'])
            clients = entry.get('ClientId', None)
            if clients:
                clients = [clients]
            supervisors.add(entry['Supervisor'])
            dates = entry['DateOfService']
            entries.append(entry)

    entries = sorted(entries, key=lambda d: d['DateOfService'])

    for entry in entries:
        if (entry['ObservedwithClient'] == True or entry['ObservedwithClient'] == 'yes') and entry["Verified"] == True:
            observed_with_client += 1
            
        if entry['Verified'] == True and entry['MeetingForm'] == True:
            face_to_face += 1
            
        if entry['Verified'] == True and entry['MeetingForm'] == True:
            supervised_time += entry['MeetingDuration']

        if int(entry['ProcedureCodeId']) == 194641 and entry["Verified"] == True and entry['MeetingForm'] == True:
            meetings += 1

        if 'ProviderId' in entry:
            ids.append(entry['ProviderId'])

    if role is not None:
        total_hours_data = db.TotalHours.find_one({'ProviderId': user['providerId'], 'Month': month, 'Year': year})
        total_hours = total_hours_data['TotalTime'] if total_hours_data else 0

    return entries, total_hours, supervised_time, ids, meetings, min_year, supervisors, observed_with_client, face_to_face


def get_pending(role, user):
    db = initialize_database()
    if role.lower() == 'admin':
        entries = list(db.Registry.find({'Verified': False}))
    elif role.lower() in [i.lower() for i in get_supervisors()]:
        entries = list(db.Registry.find({'Verified': False, "Supervisor": int(user['providerId'])}))
    elif role.lower() in ['basic', 'rbt', 'rbt/trainee', 'rbt/ba trainee']:
        provider_id = user.get('providerId') or user.get('ProviderId')
        if provider_id is not None:
            entries = list(db.Registry.find({'Verified': False, 'ProviderId': int(provider_id)}))
        else:
            entries = []
    else:
        entries = []

    return entries

# Home Route with login form
@app.route("/")
def home():
    if 'logged_in' in session:
        print(f"Session Data: {session.__dict__}")
        return redirect('/dashboard')
    # Render the home page with the login form
    return render_template('home.html', register=False)

# Home Route With Regiter form
@app.route('/register')
def register():
    db = initialize_database()
    types = ['None'] + [i['type'] for i in db.providerType.find()]
    return render_template('home.html', register=True, types=types)


# Dashboard

# Post endpoint to upoad file
@app.route("/dashboard", methods=['POST'])
@login_required
@admin_required
def upload_files():
    # Check if a file was uploaded
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)

    uploaded_file = request.files['file']

    # Check if the file has a filename
    if uploaded_file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)

    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.csv')
        
        # Save the uploaded file to the specified path
        uploaded_file.save(file_path)
        flash('File uploaded successfully', 'success')
    except Exception as e:
        flash(f'Error uploading file: {str(e)}', 'error')

    return redirect(url_for('upload'))

@app.route("/dashboard/providers", methods=['POST'])
@login_required
@admin_required
def upload_users_file():
    # Check if a file was uploaded
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)

    uploaded_file = request.files['file']

    # Check if the file has a filename
    if uploaded_file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)

    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.csv')

        # Save the uploaded file to the specified path
        uploaded_file.save(file_path)
        flash('File uploaded successfully', 'success')
    except Exception as e:
        flash(f'Error uploading file: {str(e)}', 'error')

    return redirect(url_for('upload_provider'))



@app.route('/providers')
@login_required
@admin_required
def providers():
    entries = db.users.find()
    # entries = sorted(entries, key=lambda d: (d['first_name'], d['role']))
    return render_template('dashboard.html', roles=get_roles(entries), role='admin', entries=entries, providerIds=[], session=session, report=False)


@app.route('/manage_roles', methods=['GET', 'POST'])
# @app.route('/manage_procedure_codes', methods=['GET', 'POST'])
@login_required
@admin_required
def role_manager():
    
    if request.method == 'POST':
        if 'admin' in request.form:
            admin = request.form['admin']
        else:
            admin = 'no'
        db.roles.insert_one(
            {'name': request.form['role'], 'admin': admin})
        return redirect(url_for('role_manager'))

    if request.method == 'GET':
        roles = db.roles.find()
        roles = list(roles)
        # print(roles)
        return render_template('roles.html', role=session['user']['role'], roles=list(roles))


@app.route('/del/role/<id>')
@login_required
@admin_required
def del_role(id):
    db.roles.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('role_manager'))


@app.route('/manage_procedure_codes', methods=['GET', 'POST'])
# @app.route('/manage_procedure_codes', methods=['GET', 'POST'])
@login_required
@admin_required
def procedure_codes():
    if request.method == 'POST':
        db.procedure_codes.insert_one(
            {'code': request.form['code'], 'name': request.form['name']})
        return redirect(url_for('procedure_codes'))
    if request.method == 'GET':
        codes = db.procedure_codes.find()
        return render_template('procedure_codes.html', codes=list(codes), role=session['user']['role'])


@app.route('/del/procedure/<id>')
@login_required
@admin_required
def del_procedure_code(id):
    db.procedure_codes.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('procedure_codes'))


@app.route('/cancel/<id>/<year>/<month>')
def redirecting(id, year, month):
    return report(id=id, year=year, month=month)


@app.route('/user_report/<id>/<year>/<month>/<alert>', methods=["POST", "GET"])
@app.route('/user_report/<id>/<year>/<month>', methods=["POST", "GET"])
@app.route('/user_report/<id>', methods=["POST", "GET"])
@login_required
def report(id, year=None, month=None, alert=None, curr_year=datetime.datetime.now().year):

    if year is None and month is None:
        year = int(request.form.get("year")) if request.form.get(
            "year") else datetime.datetime.now().year
        month = int(request.form.get("month")) if request.form.get(
            "month") else datetime.datetime.now().month-1

    try:
        user = db.users.find_one({"_id": ObjectId(id)})
    except:
        user = db.users.find_one({"_id": id})

    if user and "ProviderId" in user:
        user['providerId'] = user['ProviderId']
        entries, total_hours, supervised_time, ids, meetings, min_year, supervisors, observed_with_client, face_to_face = get_entries(
            'basic', year, month, user)

        for entry in entries:
            name = db.users.find_one({"ProviderId": int(entry['Supervisor'])})
            if name:
                entry['Supervisor'] = name['name']

        # 5th percent of total hours
        minimum_supervised = total_hours * 0.05
        if minimum_supervised == 0:
            minimum_supervised = total_hours * 0.05
        # print(minimum_supervised)

        missing = []

        for i in ["ProviderId", "name", "email", "first_name", "last_name", "credential", "background_date", "hired_date", "background_screening_type", "background_exp_date"]:

            if i in user and user[i] != None and user[i] != "" and user[i] != "None" and user[i] != nan:
                continue
            missing.append(i)
        exp = supervised_time >= minimum_supervised and observed_with_client >= 1 and face_to_face >= 2
        role = user['role'] or 'rbt'
        # print(exp)
        curr_year = int(curr_year)+1

        return render_template("user_work.html", face_to_face = face_to_face,  id=id, curr_year=curr_year, session=session, year=year, month=month, entries=entries, total_hours=total_hours, supervised_time=supervised_time, minimum_supervised=round(minimum_supervised, 2), ids=ids, meetings=meetings, min_year=min_year, supervisors=supervisors, report=True, user=user, observed_with_client=observed_with_client, alert=alert, pending=get_pending('basic', user), missing=missing, codes=list(db.procedure_codes.find()), code_id=[int(i['code']) for i in db.procedure_codes.find()], role=role, exp=exp)

    return redirect("/")

# Dashoard for client (login Needed)

@app.route("/edit_total_hours/<id>/<year>/<month>", methods=["POST", "GET"])
def edit_total_hours(id, year, month):
    
    if year is None and month is None:
        year = datetime.datetime.now().year
        month = datetime.datetime.now().month-1

    if request.method == "GET":
        criteria = {'ProviderId': int(id), 'Month': int(month), 'Year': int(year)}
        total_hours = db.TotalHours.find_one(criteria)
        
        if not total_hours:
            h = 0
        else:
            h = total_hours['TotalTime']
        return render_template("edit_total_hours.html", id=id, month=month, year=year, total_hours=h)
    else:
        number = request.form.get('number')
        try:
            number = float(number)
        except ValueError:
            error = "Invalid number. Please enter a valid float."
    
        # Update the document in the 'TotalHours' collection
        filter = {'ProviderId': int(id),
                  'Month': int(month), 'Year': int(year)}
        update = {'$set': {'TotalTime': round_half_up(number)}}
        db.TotalHours.update_one(filter, update, upsert=True)
        
        return redirect(f"/user_report/{id}/{year}/{month}")

def get_roles(users):
    roles = ['all']
    for u in users:
        roles.append(u['role'])
    return set(roles)


@app.route('/dashboard', methods=['GET'])
@app.route('/dashboard/<month>/<year>', methods=['GET'])
@login_required
def dashboard(
    month=datetime.datetime.now().month-1, 
    year=(datetime.datetime.now().year if datetime.datetime.now().month-1 else datetime.datetime.now().year-1), 
    alert=None
    ):

    if alert == None:
        alert = session['messages'] if 'messages' in session else None
        session['messages'] = None

    if 'providerId' in session['user']:
        session['user']['providerId'] = int(session['user']['providerId'])

    # Detect the role of the loged user to determine the permissions
    if 'role' in session['user'] and session['user']['role'] != None:
        role = session['user']['role']
    else:
        role = 'basic'
        
    users = db.users.find()
    users = sorted(users, key=lambda d: (d['role'], d['name']))
    print(year, month)
    entries, total_hours, supervised_time, ids, meetings, min_year, supervisors, observed_with_client, face_to_face = get_entries(
        role, year, month, session['user'])
    print(face_to_face)
    if role in get_supervisors():
        us = inspect_supervisor(
            db=db, year=year, month=month, pid=session['user']['providerId'])
        nus = []
        for it in users:
            if 'ProviderId' in it and it['ProviderId'] in us and it['ProviderId'] != session['user']['providerId']:
                nus.append(it)
        users = nus

    pending = get_pending(role, session['user'])

    for entry in entries:
        name = db.users.find_one({"ProviderId": int(entry['Supervisor'])})
        if name:
            entry['Supervisor'] = name['first_name']

    for entry in pending:
        if not 'Supervisor' in entry or entry['Supervisor'] == None:
            continue
        name = db.users.find_one({"ProviderId": int(entry['Supervisor'])})
        # log(name)
        if name:
            entry['Supervisor'] = name['first_name']
    # log(observed_with_client)

    missing = []
    user = session['user']
    
    if not (role in get_admins()):
        for i in ["ProviderId", "name", "email", "first_name", "last_name", "BACB_id", "credential", "role", "background_screening_type"]:
            if i in user and user[i] != None and user[i] != "" and user[i] != "None" and user[i] != nan:
                continue
            missing.append(i)
    exp = supervised_time >= 5/100*total_hours and observed_with_client >= 1 and face_to_face >= 2
    return render_template('dashboard.html', user=user,  face_to_face=face_to_face, role=role, entries=entries, providerIds=ids, supervisors=supervisors, session=session, total_hours=round_half_up(total_hours, 2), minimum_supervised=round(5/100*total_hours, 2), supervised_hours=supervised_time, meeting_group=meetings, year=year, min_year=min_year, month=month, users=users, pending=pending, id=str(session['user']['_id']), alert=alert, report=not (role in get_admins()), observed_with_client=observed_with_client,exp = exp, missing=missing)

# Only admins will see this page and it will let edit users and provider ids


@app.route('/user/edit/<id>', methods=('GET', 'POST'))
@login_required
def config_edit(id):
    try:
        flag = (session['user']['_id'] == str(id))
    except:
        flag = (session['user']['_id'] == ObjectId(str(id)))
    is_admin = ('role' in session['user']
                and session['user']['role'] in get_admins())
    if (flag) or is_admin:
        if request.method == 'POST':
            try:
                prov_id = int(request.form.get('provider_id'))
            except:
                prov_id = ''
            try:
                if is_admin:
                    data = {
                        "name": f'{request.form.get("first_name")} {request.form.get("last_name")} {request.form.get("credential")}',
                        "ProviderId": prov_id,
                        "email": request.form.get('email'),
                        "first_name": request.form.get('first_name'),
                        "last_name": request.form.get('last_name'),
                        "BACB_id": request.form.get('BACB_id'),
                        "credential": request.form.get('credential'),
                        "role": request.form.get('role'),
                        "hired_date": request.form.get('hired_date'),
                        "background_screening_type": request.form.get('fingerprint'),
                        "background_date": request.form.get('background_date'),
                        "background_exp_date": request.form.get('background_exp_date'),
                        "active": (request.form.get('active') == 'on'),
                    }
                else:
                    data = {
                        "name": f'{request.form.get("first_name")} {request.form.get("last_name")} {request.form.get("credential")}',
                        "ProviderId": prov_id,
                        "email": request.form.get('email'),
                        "first_name": request.form.get('first_name'),
                        "last_name": request.form.get('last_name'),
                        "BACB_id": request.form.get('BACB_id'),
                        "credential": request.form.get('credential'),
                        "hired_date": request.form.get('hired_date'),
                        "background_screening_type": request.form.get('fingerprint'),
                        "background_date": request.form.get('background_date'),
                        "background_exp_date": request.form.get('background_exp_date'),
                    }
                pwd = request.form.get("password")
                if pwd != '':
                    data['password'] = pbkdf2_sha256.encrypt(pwd)
                db.users.update_one({"_id": ObjectId(str(id))}, {'$set': data})
            except:
                data = {
                    "name": f'{request.form.get("first_name")} {request.form.get("last_name")} {request.form.get("credential")}',
                    "ProviderId": prov_id,
                    "first_name": request.form.get('first_name'),
                    "last_name": request.form.get('last_name'),
                    "BACB_id": request.form.get('BACB_id'),
                    "credential": request.form.get('credential'),
                    "role": request.form.get('role'),
                    "hired_date": request.form.get('hired_date'),
                    "background_screening_type": request.form.get('fingerprint'),
                    "background_date": request.form.get('background_date'),
                    "background_exp_date": request.form.get('background_exp_date'),
                }
                pwd = request.form.get("password")
                if pwd != '':
                    data['password'] = pbkdf2_sha256.encrypt(pwd)

                db.users.update_one({"_id": str(id)}, {
                    '$set': data})
            return redirect("/")

        if request.method == 'GET':
            try:
                user = db.users.find_one({'_id': str(id)})
                if user:
                    return render_template('edit_user.html', user=user, admin=is_admin, roles=get_all_roles(db))
                else:
                    user = db.users.find_one({'_id': ObjectId(str(id))})
                    return render_template('edit_user.html', user=user, admin=is_admin, roles=get_all_roles(db))

            except:
                user = db.users.find_one({'_id': ObjectId(str(id))})
                return render_template('edit_user.html', user=user, admin=is_admin)


@ app.route('/user/new', methods=('GET', 'POST'))
@ login_required
@ admin_required
def new_user():
    if request.method == 'GET':
        user = {
            "name": '',
            "first_name": '',
            "last_name": '',
            "BACB_id": '',
            "provider_id": '',
            "credential": '',
            "role": '',
            "hired_date": '',
            "fingerprint_background": '',
            "background_date": '',
            "background_exp_date": '',
        }
        return render_template('edit_user.html', user=user, admin=True, roles=get_all_roles(db))

    if request.method == 'POST':

        db.users.insert_one({
            "name": f'{request.form.get("first_name")} {request.form.get("last_name")} {request.form.get("credential")}',
            "email": request.form.get('email'),
            "first_name": request.form.get('first_name'),
            "last_name": request.form.get('last_name'),
            "ProviderId": request.form.get('provider_id'),
            "BACB_id": request.form.get('BACB_id'),
            "credential": request.form.get('credential'),
            "role": request.form.get('role'),
            "hired_date": request.form.get('hired_date'),
            "fingerprint_background": request.form.get('fingerprint'),
            "background_date": request.form.get('background_date'),
            "background_exp_date": request.form.get('background_exp_date'),
        })

        return redirect("/")

    if request.method == 'GET':
        user = db.users.find_one({'_id': str(id)})
        if user:
            return render_template('edit_user.html', user=user)


@ app.route('/edit/new/<id>', methods=('GET', 'POST'))
@ app.route('/edit/new', methods=('GET', 'POST'))
@ login_required
def add(id=None):

    if id is None:
        id = session['user']['providerId']
    else:
        try:
            user = db.users.find_one({"_id": ObjectId(id)})
        except:
            user = db.users.find_one({"_id": id})
        id = user['ProviderId']

    if request.method == 'GET':
        entry = {
            # "entryId": entry["Id"],
            "ProviderId": id,
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
            "Verified": True,
            "MeetingForm": False
        }

        supervisor_roles = ["BCBA (L)", "BCBA", "BCaBA"]
        supervisors = []
        for role in supervisor_roles:
            temp = db.users.find({"role": role})
            supervisors += list(temp) 

        return render_template('edit.html', role=session['user']['role'], id=id, entry=entry, supervisors=supervisors, codes=list(db.procedure_codes.find()))
        # return redirect(url_for('/', message={'error':'you cant edit that entry'}))
    else:
        group = individual = 'no'
        if request.form.get("supervision_type") == 'yes':
            group = 'yes'
        if request.form.get("supervision_type") == 'no':
            individual = 'yes'

        db.Registry.insert_one({
            "ProviderId": id,
            "ProcedureCodeId": int(request.form.get('ProcedureCodeId')),
            "MeetingDuration": float(request.form.get("MeetingDuration")),
            "ModeofMeeting": request.form.get("meeting_type"),
            "ObservedwithClient": request.form.get("observed"),
            "Group": group,
            "Individual": individual,
            "DateOfService": request.form.get('DateOfService'),
            "Supervisor": int(request.form.get('sup')),
            "Verified": False,
            "MeetingForm": False
        })
        date = datetime_format.get_date(request.form.get('DateOfService'))
        year, month = date.year, date.month
        
        if not session['user']['role'] in get_admins():
            return redirect('/')
        else:
            if not user:
                user = session["user"]
            return report(id=user['_id'], year=year, month=month)
            # return redirect(url_for('report', id=user['_id'], curr_year=datetime.datetime.now().year))


@ app.route('/verify/<id>/<year>/<month>', methods=('GET', 'POST'))
@ login_required
def verify(id, year, month):
    # log('verifying')
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    date = datetime_format.get_date(entry['DateOfService'])
    year, month = date.year, date.month
    if session['user']['role'].lower() in ['admin', 'bcba', 'bcba (l)'] or session['user']['providerId'] == entry['Supervisor']:
        # log('here')
        db.Registry.update_one({"_id": ObjectId(id)}, {"$set": {
            "Verified": True,
        }})
    # log(db.Registry.find_one({"_id": ObjectId(id)}))
    # log(db.Registry.find_one({"_id": ObjectId(id)}))
    if not session['user']['role'] in get_admins():
        return redirect(url_for('dashboard', month=month, year=year))
    else:
        rbt = db.users.find_one({"ProviderId": entry['ProviderId']})
        
        return report(id=rbt['_id'], year=year, month=month)


@ app.route('/meeting/<id>/<year>/<month>', methods=('GET', 'POST'))
@ login_required
def meeting(id, year, month):
    # log('verifying')
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    date = datetime_format.get_date(entry['DateOfService'])
    year, month = date.year, date.month
    # print(entry)
    if session['user']['role'].lower() in ['admin', 'bcba', 'bcba (l)'] or session['user']['providerId'] == entry['ProviderId']:
        # log('here')
        en = db.Registry.find_one({"_id": ObjectId(id)})
        db.Registry.update_one({"_id": ObjectId(id)}, {"$set": {
            "MeetingForm": not en["MeetingForm"],
        }})
    if not session['user']['role'] in get_admins():
        return redirect(url_for('dashboard', month=month, year=year))
    else:
        rbt = db.users.find_one({"ProviderId": entry['ProviderId']})
        # print(rbt)
        if rbt:
            return report(id=rbt['_id'], year=year, month=month)
            # return redirect(url_for('report', id=rbt["_id"], alert=None, year=year, month=month, curr_year=datetime.datetime.now().year))
        return redirect("/")


@ app.route('/del/entry/<id>', methods=('GET', 'POST'))
@ login_required
def delete_entry(id):
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    date = datetime_format.get_date(entry['DateOfService'])
    year, month = date.year, date.month,
    db.Registry.delete_one({"_id": ObjectId(id)})

    if entry:
        if not session['user']['role'] in get_admins():
            return redirect('/')
        else:
            rbt = db.users.find_one({"ProviderId": entry['ProviderId']})
            return report(id=rbt['_id'], year=year, month=month)
            # return redirect(url_for('report', id=rbt['_id'], curr_year=datetime.datetime.now().year))


@ app.route('/edit/<id>/<year>/<month>', methods=('GET', 'POST'))
@ app.route('/edit/<id>', methods=('GET', 'POST'))
@ login_required
def edit(id, year=None, month=None):
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    # log(entry)
    if request.method == 'GET':

        supervisor_roles = ["BCBA (L)", "BCBA", "BCaBA"]
        supervisors = []
        for role in supervisor_roles:
            temp = db.users.find({"role": role})
            supervisors += list(temp)

        user = db.users.find_one({"ProviderId": entry['ProviderId']})
        date = datetime_format.get_date(entry['DateOfService'])
        year, month = date.year, date.month
        return render_template('edit.html', role=session['user']['role'], entry=entry, supervisors=supervisors, id=user['_id'], codes=list(db.procedure_codes.find()), year=year, month=month)

    elif request.method == "POST":
        if entry["ProcedureCodeId"] != request.form.get('ProcedureCodeId') or entry["DateOfService"] != request.form.get('DateOfService') or entry["MeetingDuration"] != request.form.get('MeetingDuration'):
            db.Registry.update_one({"_id": ObjectId(id)}, {"$set": {
                "ProcedureCodeId": int(request.form.get('ProcedureCodeId')),
                "MeetingDuration": float(request.form.get("MeetingDuration")),
                "Group": 'yes' if request.form.get('supervision_type') == 'yes' else 'no',
                "Individual": 'yes' if request.form.get('supervision_type') == 'no' else 'no',
                "ObservedwithClient": request.form.get('observed'),
                "ModeofMeeting": request.form.get('meeting_type'),
                "DateOfService": request.form.get('DateOfService'),
                "Supervisor": int(request.form.get('sup')),
                "Verified": False
            }})

        if not session['user']['role'] in get_admins():
            return redirect('/')
        else:
            rbt = db.users.find_one({"ProviderId": entry['ProviderId']})
            date = datetime_format.get_date(entry['DateOfService'])
            year, month = date.year, date.month,
            return report(id=rbt['_id'], year=year, month=month)
            # return redirect(url_for('report', id=rbt['_id'], curr_year=datetime.datetime.now().year))


@ app.route('/del/<id>', methods=('GET', 'POST'))
@ login_required
def delete(id):
    db.users.delete_one({"_id": ObjectId(id)})
    # if session['user']['role'].lower() in ['admin', 'bcba','bcba (l)']:
    #     try:
    #         if db.users.find_one({"_id": ObjectId(id)}):
    #             try:
    #                 print(id)
    #             except:
    #                 db.users.delete_one({"_id": str(id)})
    #     except:
    #         if db.users.find_one({"_id": str(id)}):
    #             try:
    #                 db.users.delete_one({"_id": ObjectId(id)})
    #             except:
    #                 db.users.delete_one({"_id": str(id)})
    session['messages'] = {'correct': "user deleted successfully"}
    return redirect(url_for('dashboard'))


@ app.route('/user/signup', methods=['POST'])
def signup():
    return User().signup()


@ app.route('/user/login', methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.users.find_one({"email": email})

        if user and pbkdf2_sha256.verify(password, user['password']):
            session['logged_in'] = True
            session['user'] = user
            log(f"User {email} logged in successfully.")
            # return redirect(url_for('dashboard'))
        else:
            log(f"Failed login attempt.")
            flash('Invalid login credentials', 'danger')

    usr = User().login(db)
    return dashboard() 


@ app.route('/user/signout')
def signout():
    return User().signout()


@ app.route('/user/logout')
def logout():
    pass


@ app.route('/procedures/')
def procedures():
    if request.method == 'GET':
        pass

    else:
        pass

def required_columns(data):
    
    columns = [
        "ProviderId",
        "ClientId",
        "ProcedureCodeId",
        "TimeWorkedInHours",
        "DateOfService",
        "DateTimeFrom",
        "DateTimeTo",
    ]
    missing = []
    for i in columns:
        if not i in data:
            missing.append(i) 
    
    return missing
            
            
@ app.route('/upload', methods=['POST', 'GET'])
def upload():
    # if os.path.exists('static/files/data.data.csv'):
    data = pd.read_csv('static/files/data.csv')
    
    missing = required_columns(data)
    
    if len(missing) > 0:
        alert = {"Error": f'File uploaded is not valid, missing: {missing}'}
        session['messages'] = alert
        return redirect(url_for('dashboard'))

    
    status_code = Registry().add_data(db)
    alert = {"correct": 'File uploaded and processed successfully'}
    session['messages'] = alert
    return redirect(url_for('dashboard'))


@ app.route('/upload-providers', methods=['POST', 'GET'])
def upload_provider():
    User().add_data(db)
    return redirect('/')


@ app.route("/filter/", methods=['POST', 'GET'])
def filter_data():
    month = request.form.get('month')
    year = request.form.get('year')

    if not month:
        month = datetime.datetime.now().month-1
    if not year:
        year = datetime.datetime.now().year 
        if month == 12:
            year -= 1
    return redirect(f"/dashboard/{month}/{year}")


@ app.route("/filter/<year>/<month>", methods=['POST', 'GET'])
def filter_data_args(year, month):
    # return redirect(url_for('dashboard', year=year, month=month))
    return redirect(f"/dashboard/{month}/{year}")


@ app.route("/report/<year>/<month>/<id>")
def get_report(year, month, id):
    year = int(year)
    month = int(month)

    try:
        user = db.users.find_one({"_id": ObjectId(id)})
    except:
        user = db.users.find_one({"_id": id})

    if user and "ProviderId" in user:
        user['providerId'] = user['ProviderId']
        entries, total_hours, supervised_time, ids, meetings, min_year, supervisors, observed_with_client, face_to_face = get_entries(
            'basic', year, month, user)

    supervisors = []
    if user and entries:
        month_year = f'{month}/{year}'

        providers = []
        for entry in entries:
            superv = db.users.find_one({"ProviderId": entry["Supervisor"]})
            # log(superv)
            entry["Supervisor"] = superv['name']
            if not entry['Supervisor'] in providers:
                providers.append(entry["Supervisor"])
                supervisors.append(superv)

        # log(supervisors)
        # supervisors = list(set(superviso
        # rs))
        company = user['background_screening_type']
        date = user['background_date']
        exp_date = user['background_exp_date']
        entries_to_print = []
        
        for e in entries:
            e['DateOfService'] = datetime_format.get_date(
                e['DateOfService']).strftime("%m/%d/%Y")
            if e['Verified']:
                entries_to_print.append(e)
            # print(e['DateOfService'])
        # try:
        entries = entries_to_print
        template = render_template(
            'report_rbt.html', rbt_name=user['name'], hired_date=user['hired_date'], signature=get_second_monday(year, month), date=date, exp_date=exp_date, company=company, month_year=month_year, entries=entries, total_hours=total_hours, minimum_supervised=round(total_hours*0.05, 2), supervised_hours=round(supervised_time, 2), supervisors=supervisors, report=True, observed_with_client=observed_with_client, coordinator=get_rbt_coordinator(db))
        options = {
            'page-size': 'A4',
            # 'orientation': ,
            'enable-local-file-access': None,  # to avoid blanks
            'javascript-delay': 1000,
            'no-stop-slow-scripts': None,
            'debug-javascript': None,
            'enable-javascript': None
        }
        # config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
        # except:
        #     # if False:
        #     log("exception")
        #     alert = {
        #         'error': 'Something went Wrong! Check that all the User info is correct'}
        #     if not session['user']['role'].lower() in ['admin', 'bcba', 'bcba (l)']:
        #         return redirect(url_for('dashboard', year=year, month=month, alert=alert, report=False))
        #     else:
        #         return redirect(url_for('report', id=id, alert=alert))
        #         # return  render_template('user_work.html', id=id, year=year, month=month, alert='Something went Wrong! Check that all the User info is correct generating report')
        #     # return dashboard(year, month, alert={'error': 'Error generating report'})
        nm = month
        wkhtmltopdf_path = '/usr/bin/wkhtmltopdf'
        if nm < 10:
            nm = '0'+str(nm)
        filename = f"{nm}{year}-{user['name']}-RBT_Service-Delivery_and_Supervision_Hours_Tracker.pdf"
        pdfkit.from_string(template, './report.pdf', options=options, configuration=pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path))
        sleep(1)

        return send_file('./report.pdf', download_name=filename, as_attachment=True)
        # except:
        #     log("Something went Wrong!")
        #     return dashboard(month, month, alert=None)
    else:
        return dashboard(month, month)


@app.errorhandler(404)
def not_foud(e):
    return render_template('not_found.html')
