from registry.models import Registry
from user import routes
from user.models import User
from flask import Flask, render_template, redirect, session, request, url_for, jsonify, send_file
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
            if session['user']['role'] in ['admin', 'bcba']:
                return f(*args, **kwargs)
        else:
            return redirect('/')
    return wrap


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(int(n)*multiplier + 0.5) / multiplier


def get_entries(role, year, month, user):
    entries = db.Registry.find()
    entries = [entry for entry in entries]

    temp = []
    clients = []
    dates = []
    supervisors = []

    for entry in entries:
        if datetime_format.get_date(entry["DateOfService"]).year == year and datetime_format.get_date(entry["DateOfService"]).month == month:
            entry['ProviderId'] = int(entry['ProviderId'])
            if 'providerId' in user and int(entry['ProviderId']) == int(user['providerId']) and "ClientId" in entry:
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
        # print(i)
        min_year = min(min_year, int(
            datetime_format.get_date(i["DateOfService"]).year))

        i['MeetingDuration'] = round_half_up(i['MeetingDuration'], 1)
        supervised_time += int(i['MeetingDuration'])
        # TODO get this condition from other table that gives clinical meeting info
        condition = True
        if i['ProcedureCodeId'] == 194641 and condition == True:
            meetings += 1

        if 'ProviderId' in i:
            ids += list(set([i['ProviderId'] for i in entries]))
    if role == 'basic':
        # , 'Year': datetime.datetime.now().year, 'Month': datetime.datetime.now().month})
        total_hours = db.TotalHours.find_one({'ProviderId': int(
            user['providerId']), 'Month': month, 'Year': year})
        if total_hours == None:
            total_hours = 0
        else:
            # print(total_hours, year ,month)
            total_hours = total_hours['TotalTime']
    else:
        total_hours = 0

    print(supervised_time)

    return entries, total_hours, supervised_time, ids, meetings, min_year, set(supervisors)


def get_pending(role, user):

    if role in ['admin', 'bcba']:
        entries = list(db.Registry.find({'Verified': False}))
    elif role != 'basic' or role != 'rbt':
        try:
            entries = list(db.Registry.find(
                {'Verified': False, 'ProviderId': int(user['providerId'])}))
        except:
            entries = list(db.Registry.find(
                {'Verified': False, 'ProviderId': int(user['ProviderId'])}))
    else:
        entries = []

    return entries

# routes.

# Home Page

# Home Route with login form


@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect('/dashboard')
    return render_template('home.html', register=False)
# Home Route With Regiter form


@app.route('/register')
def register():
    types = ['None'] + [i['type'] for i in db.providerType.find()]
    return render_template('home.html', register=True, types=types)


# Dashboard

# Post endpoint to upoad file
@app.route("/dashboard", methods=['POST'])
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


@app.route("/dashboard/providers", methods=['POST'])
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
    return redirect(url_for('upload_provider'))


@app.route('/providers')
@login_required
@admin_required
def providers():
    entries = db.user.find()
    return render_template('dashboard.html', roles=get_roles(entries), role='admin', entries=entries, providerIds=ids, session=session)


@app.route('/user_report/<id>', methods=["POST", "GET"])
@login_required
def report(id):
    year = int(request.form.get("year")) if request.form.get(
        "year") else datetime.datetime.now().year
    month = int(request.form.get("month")) if request.form.get(
        "month") else datetime.datetime.now().month

    try:
        user = db.users.find_one({"_id": ObjectId(id)})
    except:
        user = db.users.find_one({"_id": id})

    if user and "ProviderId" in user:
        user['providerId'] = user['ProviderId']
        entries, total_hours, supervised_time, ids, meetings, min_year, supervisors = get_entries(
            'basic', year, month, user)

        for entry in entries:
            name = db.users.find_one({"ProviderId": int(entry['Supervisor'])})
            if name:
                entry['Supervisor'] = name['name']

        # 10th percento fo total hours
        minimum_supervised = round_half_up(total_hours * 0.05)
        return render_template("user_work.html", id=id, session=session, year=year, month=month, entries=entries, total_hours=total_hours, supervised_time=supervised_time, minimum_supervised=minimum_supervised, ids=ids, meetings=meetings, min_year=min_year, supervisors=supervisors, report=True)

    return redirect("/")

# Dashoard for client (login Needed)


def get_roles(users):
    roles = ['all']
    for u in users:
        roles.append(u['role'])
    return set(roles)


@app.route('/dashboard')
@login_required
def dashboard(month=datetime.datetime.now().month, year=datetime.datetime.now().year, alert=None):
    if 'providerId' in session['user']:
        session['user']['providerId'] = int(session['user']['providerId'])

    # Detect the role of the loged user to determine the permissions
    if 'role' in session['user'] and session['user']['role'] != None:
        role = session['user']['role']
    else:
        role = 'basic'

    # If user is not admin, remove the entries that dont belong to him/her
    # if role == 'basic':
    users = db.users.find()
    entries, total_hours, supervised_time, ids, meetings, min_year, supervisors = get_entries(
        role, year, month, session['user'])
    pending = get_pending(role, session['user'])

    for entry in entries:
        name = db.users.find_one({"ProviderId": int(entry['Supervisor'])})
        if name:
            entry['Supervisor'] = name['first_name']

    for entry in pending:
        name = db.users.find_one({"ProviderId": int(entry['Supervisor'])})
        print(name)
        if name:
            entry['Supervisor'] = name['first_name']

    return render_template('dashboard.html', role=role, entries=entries, providerIds=ids, session=session, total_hours=round_half_up(total_hours), minimum_supervised=round_half_up(5/100*total_hours, 1), supervised_hours=round_half_up(supervised_time, 1), meeting_group=meetings, year=year, min_year=min_year, month=month, users=users, pending=pending, id=str(session['user']['_id']), alert=alert, report=True)

# Only admins will see this page and it will let edit users and provider ids


@app.route('/user/edit/<id>', methods=('GET', 'POST'))
@login_required
def config(id):
    
    try:
        flag = (session['user']['_id'] == str(id))
    except:
        flag = (session['user']['_id'] ==  ObjectId(str(id)))
    
    if (flag) or ('role' in session['user'] and session['user']['role'] in ['admin', 'bcba']) :
        if request.method == 'POST':

            try:
                db.users.update_one({"_id": ObjectId(str(id))}, {'$set': {
                    "name": request.form.get('name'),
                    "email": request.form.get('email'),
                    "first_name": request.form.get('first_name'),
                    "last_name": request.form.get('last_name'),
                    "BACB_id": request.form.get('BACB_id'),
                    "credential": request.form.get('credential'),
                    "role": request.form.get('role'),
                    "hired_date": request.form.get('hired_date'),
                    "fingerprint_background": request.form.get('fingerprint'),
                    "background_date": request.form.get('background_date'),
                    "background_exp_date": request.form.get('background_exp_date'),
                }})
                pwd = request.form.get("password")
                if pwd != '':
                    db.users.update_one({"_id": ObjectId(str(id))}, {
                                        '$set': {"password": pbkdf2_sha256.encrypt(pwd)}})
            except:
                db.users.update_one({"_id": str(id)}, {'$set': {
                    "name": request.form.get('name'),
                    "first_name": request.form.get('first_name'),
                    "last_name": request.form.get('last_name'),
                    "BACB_id": request.form.get('BACB_id'),
                    "credential": request.form.get('credential'),
                    "role": request.form.get('role'),
                    "hired_date": request.form.get('hired_date'),
                    "fingerprint_background": request.form.get('fingerprint'),
                    "background_date": request.form.get('background_date'),
                    "background_exp_date": request.form.get('background_exp_date'),
                }})
                pwd = request.form.get("password")
                if pwd != '':
                    db.users.update_one({"_id": str(id)}, {
                                        '$set': {"password": pbkdf2_sha256.encrypt(pwd)}})
            return redirect("/")

        is_admin = session['user']['role'] in ['admin', 'bcba']
        if request.method == 'GET':
            try:
                user = db.users.find_one({'_id': str(id)})
                if user:
                    return render_template('edit_user.html', user=user, admin=is_admin)
                else:
                    user = db.users.find_one({'_id': ObjectId(str(id))})
                    return render_template('edit_user.html', user=user, admin=is_admin)
    
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
            "credential": '',
            "role": '',
            "hired_date": '',
            "fingerprint_background": '',
            "background_date": '',
            "background_exp_date": '',
        }
        return render_template('edit_user.html', user=user)

    if request.method == 'POST':
        print(request.form.get('first_name'))

        db.users.insert_one({
            "name": request.form.get('name'),
            "first_name": request.form.get('first_name'),
            "last_name": request.form.get('last_name'),
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
        print(user)
        if user:
            return render_template('edit_user.html', user=user)


@ app.route('/edit/new', methods=('GET', 'POST'))
@ login_required
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
            "Verified": True
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


@ app.route('/verify/<id>', methods=('GET', 'POST'))
@ login_required
def verify(id):
    print('verifying')
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    if session['user']['role'] in ['admin', 'bcba'] or session['user']['providerId'] == entry['Supervisor']:
        print('here')
        db.Registry.update_one({"_id": ObjectId(id)}, {"$set": {
            "Verified": True,
        }})
    print(db.Registry.find_one({"_id": ObjectId(id)}))
    return redirect('/')


@ app.route('/edit/<id>', methods=('GET', 'POST'))
@ login_required
def edit(id):
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    if request.method == 'GET':
        if entry and 'providerId' in session['user'] and int(entry["ProviderId"]) == int(session['user']['providerId']):
            supervisors = [entry['Supervisor']]
            return render_template('edit.html', entry=entry, supervisors=supervisors)
        else:
            return redirect(url_for('/dashboard', message={'error': 'you cant edit that entry'}))
    else:
        if entry["ProcedureCodeId"] != request.form.get('ProcedureCodeId') or entry["DateOfService"] != request.form.get('DateOfService') or entry["MeetingDuration"] != request.form.get('MeetingDuration'):

            db.Registry.update_one({"_id": ObjectId(id)}, {"$set": {
                "ProcedureCodeId": int(request.form.get('ProcedureCodeId')),
                "MeetingDuration": int(request.form.get("MeetingDuration")),
                "DateOfService": request.form.get('DateOfService'),
                "Verified": False
            }})

        return


@ app.route('/del/<id>', methods=('GET', 'POST'))
@ login_required
def delete(id):
    if session['user']['role'] in ['admin', 'bcba'] and db.users.find_one({"_id": ObjectId(id)}):
        try:
            db.users.delete_one({"_id": ObjectId(str(id))})
        except:
            db.users.delete_one({"_id": str(id)})

    return redirect('/')


@ app.route('/user/signup', methods=['POST'])
def signup():
    return User().signup()


@ app.route('/user/login', methods=['POST'])
def login():
    return User().login(db)


@ app.route('/user/signout')
def signout():
    return User().signout()


@ app.route('/user/logout')
def logout():
    pass


@ app.route('/upload', methods=['POST', 'GET'])
def upload():
    Registry().add_data(db)
    return redirect('/')


@ app.route('/upload-providers', methods=['POST', 'GET'])
def upload_provider():
    User().add_data(db)
    return redirect('/')


@ app.route("/filter", methods=['POST', 'GET'])
def filter_data():
    month = request.form.get('month')
    year = request.form.get('year')

    if not month:
        month = datetime.datetime.now().month
    if not year:
        year = datetime.datetime.now().year

    return dashboard(int(month), int(year))


@ app.route("/filter/<year>/<month>", methods=['POST', 'GET'])
def filter_data_args(year, month):
    # return redirect(url_for('dashboard', year=year, month=month))
    return dashboard(int(month), int(year))


@ app.route("/report/<year>/<month>/<id>")
def get_report(year, month, id):
    try:
        user = db.users.find_one({"_id": str(id)})
        if user is None:
            user = db.users.find_one({"_id": ObjectId(str(id))})
    except:
        user = db.users.find_one({"_id": ObjectId(str(id))})
    # Detect the role of the loged user to determine the permissions
    if 'role' in user and user['role'] != None:
        role = session['user']['role']
    else:
        role = 'basic'

    year = int(year)
    month = int(month)

    user['providerId'] = user['ProviderId']

    entries, total_hours, supervised_time, ids, meetings, min_year, supervisors = get_entries(
        role, year, month, user)
    # print(entries)
    supervisors = []
    if user and entries:
        month_year = f'{month} {year}'

        for entry in entries:
            superv = db.users.find_one({"ProviderId": entry["Supervisor"]})
            print(superv)
            entry["Supervisor"] = superv['name']
            if not superv in supervisors:
                supervisors.append(superv)

        # print(supervisors)
        # supervisors = list(set(supervisors))
        try:
            template = render_template(
                'report_rbt.html', rbt_name=user['name'], hired_date=user['hired_date'], month_year=month_year, entries=entries, total_hours=round_half_up(total_hours, 2), minimum_supervision_hours=round(total_hours*0.05, 1), supervised_hours=round_half_up(supervised_time), supervisors=supervisors, report=True)
            options = {
                'page-size': 'A4',
                # 'orientation': ,
                'enable-local-file-access': None,  # to avoid blanks
                'javascript-delay': 1000,
                'no-stop-slow-scripts': None,
                'debug-javascript': None,
                'enable-javascript': None
            }

            pdfkit.from_string(template, 'report.pdf')
            return send_file('report.pdf', as_attachment=True)
        except:
            # return redirect(url_for('dashboard', year=year, month=month, alert={'error': 'Error generating report'}))
            # return dashboard(year, month, alert={'error': 'Error generating report'})
            pass
    else:
        print("Something went Wrong!")
        return dashboard(year, month, alert='Something went Wrong!')


@app.errorhandler(404)
def not_foud(e):
    return render_template('not_found.html')
