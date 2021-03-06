from cmath import nan
from inspect import signature
from time import sleep
from logger import log
from colorama import Cursor
from registry.models import Registry
from super_roles.super_roles import get_admins
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
from utils import get_rbt_coordinator, get_second_monday, round_half_up

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
            if session['user']['role'].lower() in ['admin', 'bcba','bcba (l)']:
                return f(*args, **kwargs)
        else:
            return redirect('/')
    return wrap

def get_entries(role, year, month, user):

    if not 'providerId' in user:
        if 'ProviderId' in user and user['ProviderId'] != '' and user['ProviderId'] != None:
            user['providerId'] = user['ProviderId']
        else:
            return [],0,0,[],0,0,[], 0
        
    entries = db.Registry.find({'ProviderId':int(str(user['providerId'])), 'Verified': True})
    entries = [entry for entry in entries]

    temp = []
    clients = []
    dates = []
    supervisors = []

    for entry in entries:
        
        if (datetime_format.get_date(entry["DateOfService"]).year == year or datetime_format.get_date(entry["DateOfService"]).year + 2000 == year) and datetime_format.get_date(entry["DateOfService"]).month == month:
            entry['ProviderId'] = int(entry['ProviderId'])
            if 'providerId' in user:
                if "ClientId" in entry:
                    clients.append(entry['ClientId'])
                supervisors.append(entry['Supervisor'])
                dates.append(entry['DateOfService'])
                temp.append(entry)
    entries = temp
    entries = sorted(entries, key=lambda d: d['DateOfService'])

    ids = []
    supervised_time = 0
    observed_with_client = 0
    meetings = 0
    min_year = int(datetime.datetime.now().year)
    for i in entries:
        # log(i)
        if i['ObservedwithClient'] == True or i['ObservedwithClient'] == 'yes':
            observed_with_client += 1

        min_year = min(min_year, int(
            datetime_format.get_date(i["DateOfService"]).year))

        i['MeetingDuration'] = i['MeetingDuration']
        # print(i['MeetingDuration'])
        if i['Verified'] == True:
            supervised_time += i['MeetingDuration']

        # TODO get this condition from other table that gives clinical meeting info
        condition = True
        if int(i['ProcedureCodeId']) == 194641 and condition == True:
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
            # log(total_hours, year ,month)
            total_hours = total_hours['TotalTime']
    else:
        total_hours = 0
    return entries, total_hours, supervised_time, ids, meetings, min_year, set(supervisors), observed_with_client


def get_pending(role, user):
    if role.lower() in ['admin', 'bcba', 'bcba (l)']:
        entries = list(db.Registry.find({'Verified': False}))
    elif role.lower() in ['basic','rbt','rbt/trainee']:
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
    return render_template('dashboard.html', roles=get_roles(entries), role='admin', entries=entries, providerIds=ids, session=session, report=False)

@app.route('/manage_procedure_codes', methods=['GET', 'POST'])
# @app.route('/manage_procedure_codes', methods=['GET', 'POST'])
@login_required
@admin_required
def procedure_codes():
    if request.method == 'POST':
        print(request.form)
        db.procedure_codes.insert_one({'code': request.form['code'], 'name': request.form['name']})
        return redirect(url_for('procedure_codes'))
    if request.method == 'GET':
        codes = db.procedure_codes.find()
        return render_template('procedure_codes.html', codes=list(codes))

@app.route('/del/procedure/<id>')
@login_required
@admin_required
def del_procedure_code(id):
    db.procedure_codes.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('procedure_codes'))

@app.route('/user_report/<id>/<alert>', methods=["POST", "GET"])
@app.route('/user_report/<id>', methods=["POST", "GET"])
@login_required
def report(id, alert=None):

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
        entries, total_hours, supervised_time, ids, meetings, min_year, supervisors, observed_with_client = get_entries(
            'basic', year, month, user)

        for entry in entries:
            name = db.users.find_one({"ProviderId": int(entry['Supervisor'])})
            if name:
                entry['Supervisor'] = name['name']
        # log("observed:",observed_with_client)
        # 5th percent of total hours
        minimum_supervised = round_half_up(total_hours * 0.05, 3)
        log("user:", user)

        missing = []

        for i in ["ProviderId","name","email","first_name","last_name","credential","background_date","hired_date","background_screening_type","background_exp_date"]:

            if i in user and user[i] != None and user[i] != "" and user[i] != "None" and user[i] != nan:
                continue
            missing.append(i)

        log("missing:", missing)
        return render_template("user_work.html", id=id,session=session, year=year, month=month, entries=entries, total_hours=total_hours, supervised_time=supervised_time, minimum_supervised=minimum_supervised, ids=ids, meetings=meetings, min_year=min_year, supervisors=supervisors, report=True, user=user, observed_with_client=observed_with_client, alert=alert, pending=get_pending('basic', user), missing=missing, codes=list(db.procedure_codes.find()), code_id=[int(i['code']) for i in db.procedure_codes.find()])


    return redirect("/")

# Dashoard for client (login Needed)


def get_roles(users):
    roles = ['all']
    for u in users:
        roles.append(u['role'])
    return set(roles)


@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard(month=datetime.datetime.now().month, year=datetime.datetime.now().year, alert=None):
    
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

    # If user is not admin, remove the entries that dont belong to him/her
    # if role == 'basic':
    users = db.users.find()
    entries, total_hours, supervised_time, ids, meetings, min_year, supervisors, observed_with_client = get_entries(
        role, year, month, session['user'])
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
    if not (role in get_admins()):
        user = session['user']
        for i in ["ProviderId","name","email","first_name","last_name","BACB_id","credential","role","background_screening_type"]:
            if i in user and user[i] != None and user[i] != "" and user[i] != "None" and user[i] != nan:
                continue
            missing.append(i)
    return render_template('dashboard.html', role=role, entries=entries, providerIds=ids, supervisors=supervisors, session=session, total_hours=round_half_up(total_hours,3), minimum_supervised=round_half_up(5/100*total_hours, 3), supervised_hours=round_half_up(supervised_time, 3), meeting_group=meetings, year=year, min_year=min_year, month=month, users=users, pending=pending, id=str(session['user']['_id']), alert=alert, report=not (role in get_admins()), observed_with_client=observed_with_client, missing=missing)

# Only admins will see this page and it will let edit users and provider ids


@app.route('/user/edit/<id>', methods=('GET', 'POST'))
@login_required
def config(id):
    log(id)
    log(session['user'])
    try:
        flag = (session['user']['_id'] == str(id))
    except:
        flag = (session['user']['_id'] ==  ObjectId(str(id)))
    log(flag)
    is_admin = ('role' in session['user'] and session['user']['role'] in get_admins())
    log(is_admin)
    if (flag) or  is_admin:
        if request.method == 'POST':
            log('edit')
            try:
                prov_id = int(request.form.get('provider_id'))
            except:
                prov_id = ''
            try:
                if is_admin:
                    log('user is admin')
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
                log(pwd)
                if pwd != '':
                    data['password'] = pbkdf2_sha256.encrypt(pwd)
                log(data)
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
                    '$set': {"password": data}})
            return redirect("/")

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
            "provider_id": '',
            "credential": '',
            "role": '',
            "hired_date": '',
            "fingerprint_background": '',
            "background_date": '',
            "background_exp_date": '',
        }
        return render_template('edit_user.html', user=user, admin=True)

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
        log(user)
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

    if request.method == 'GET':
        entry = {
            # "entryId": entry["Id"],
            "ProviderId": user['ProviderId'],
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
        
        supervisor_roles = ["BCBA (L)","BCBA","BCaBA"]
        supervisors = []
        for role in supervisor_roles:
            temp = db.users.find({"role": role})
            supervisors += list(temp)
            
        return render_template('edit.html', entry=entry, supervisors=supervisors, codes=list(db.procedure_codes.find()))
        # return redirect(url_for('/', message={'error':'you cant edit that entry'}))
    else:
        group= individual = 'no'
        if request.form.get("supervision_type") == 'yes':
            group = 'yes'
        if request.form.get("supervision_type") == 'no':
            individual = 'yes'
            
        db.Registry.insert_one({
            "ProviderId": user['ProviderId'],
            "ProcedureCodeId": int(request.form.get('ProcedureCodeId')),
            "MeetingDuration": float(request.form.get("MeetingDuration")),
            "ModeofMeeting": request.form.get("meeting_type"),
            "ObservedwithClient": request.form.get("observed"),
            "Group": group,
            "Individual": individual,
            "DateOfService": request.form.get('DateOfService'),
            "Supervisor": int(request.form.get('sup')),
            "Verified": False
        })

        if not session['user']['role'] in get_admins():
            return redirect('/')
        else:
            print("here")
            return redirect(url_for('report', id=user['_id']))


@ app.route('/verify/<id>', methods=('GET', 'POST'))
@ login_required
def verify(id):
    # log('verifying')
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    if session['user']['role'].lower() in ['admin', 'bcba','bcba (l)'] or session['user']['providerId'] == entry['Supervisor']:
        # log('here')
        db.Registry.update_one({"_id": ObjectId(id)}, {"$set": {
            "Verified": True,
        }})
    # log(db.Registry.find_one({"_id": ObjectId(id)}))
    if not session['user']['role'] in get_admins():
            return redirect('/')
    else:
        rbt = db.users.find_one({"ProviderId": entry['ProviderId']})
        # print(rbt)
        return redirect(url_for('report', id=rbt['_id']))


@ app.route('/del/entry/<id>', methods=('GET', 'POST'))
@ login_required
def delete_entry(id):
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    rbt = db.users.find_one({"ProviderId": entry['ProviderId']})
    
    db.Registry.delete_one({"_id": ObjectId(id)})
    
    if not session['user']['role'] in get_admins():
            return redirect('/')
    else:
        return redirect(url_for('report', id=rbt['_id']))

@ app.route('/edit/<id>', methods=('GET', 'POST'))
@ login_required
def edit(id):
    entry = db.Registry.find_one({"_id": ObjectId(id)})
    # log(entry)
    if request.method == 'GET':
        
        supervisor_roles = ["BCBA (L)","BCBA","BCaBA"]
        supervisors = []
        for role in supervisor_roles:
            temp = db.users.find({"role": role})
            supervisors += list(temp)
        
        user = db.users.find_one({"ProviderId":entry['ProviderId']})
        
        return render_template('edit.html', entry=entry, supervisors=supervisors, id = user['_id'],codes=list(db.procedure_codes.find()))

    elif request.method == "POST":
        if entry["ProcedureCodeId"] != request.form.get('ProcedureCodeId') or entry["DateOfService"] != request.form.get('DateOfService') or entry["MeetingDuration"] != request.form.get('MeetingDuration'):
            db.Registry.update_one({"_id": ObjectId(id)}, {"$set": {
                "ProcedureCodeId": int(request.form.get('ProcedureCodeId')),
                "MeetingDuration": float(request.form.get("MeetingDuration")),
                "Group": 'yes' if request.form.get('supervision_type_group') == 'on' else 'no',
                "Individual": 'yes' if request.form.get('supervision_type_individual') else 'no',
                "ObservedwithClient": request.form.get('observed'),
                "ModeofMeeting": request.form.get('meeting_type'),
                "DateOfService": request.form.get('DateOfService'),
                "Verified": False
            }})
      
        if not session['user']['role'] in get_admins():
            return redirect('/')
        else:
            rbt = db.users.find_one({"ProviderId": entry['ProviderId']})
            return redirect(url_for('report', id=rbt['_id']))


@ app.route('/del/<id>', methods=('GET', 'POST'))
@ login_required
def delete(id):
    # print(id)
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
    return User().login(db)


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


@ app.route('/upload', methods=['POST', 'GET'])
def upload():
    Registry().add_data(db)
    alert = {"correct":'File uploaded and processed successfully'}
    print(alert)
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

    # log(year)
    # log(month)

    if not month:
        month = datetime.datetime.now().month-1
    if not year:
        year = datetime.datetime.now().year

    return dashboard(int(month), int(year))


@ app.route("/filter/<year>/<month>", methods=['POST', 'GET'])
def filter_data_args(year, month):
    # return redirect(url_for('dashboard', year=year, month=month))
    return dashboard(int(month), int(year))


@ app.route("/report/<year>/<month>/<id>")
def get_report(year, month, id):
    # try:
    #     user = db.users.find_one({"_id": str(id)})
    #     if user is None:
    #         user = db.users.find_one({"_id": ObjectId(str(id))})
    # except:
    #     user = db.users.find_one({"_id": ObjectId(str(id))})
    # # Detect the role of the loged user to determine the permissions
    # if 'role' in user and user['role'] != None:
    #     role = session['user']['role']
    # else:
    #     role = 'basic'

    year = int(year)
    month = int(month)
    
    try:
        user = db.users.find_one({"_id": ObjectId(id)})
    except:
        user = db.users.find_one({"_id": id})

    if user and "ProviderId" in user:
        user['providerId'] = user['ProviderId']
        entries, total_hours, supervised_time, ids, meetings, min_year, supervisors, observed_with_client = get_entries(
            'basic', year, month, user)
    
    supervisors = []
    if user and entries:
        month_year = f'{month} {year}'

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
        try:
            template = render_template(
                'report_rbt.html', rbt_name=user['name'], hired_date=user['hired_date'],signature=get_second_monday(year, month), date=date, exp_date=exp_date, company=company, month_year=month_year, entries=entries, total_hours=round_half_up(total_hours, 2), minimum_supervised=round(total_hours*0.05), supervised_hours=round_half_up(supervised_time, 3), supervisors=supervisors, report=True, observed_with_client=observed_with_client, coordinator=get_rbt_coordinator(db))
            options = {
                'page-size': 'A4',
                # 'orientation': ,
                'enable-local-file-access': None,  # to avoid blanks
                'javascript-delay': 1000,
                'no-stop-slow-scripts': None,
                'debug-javascript': None,
                'enable-javascript': None
            }
        except:
        # if False:
            log("exception")
            alert = {'error': 'Something went Wrong! Check that all the User info is correct'}
            if not session['user']['role'].lower() in ['admin', 'bcba','bcba (l)']:
                return redirect(url_for('dashboard', year=year, month=month, alert=alert, report=False))
            else:
                return redirect(url_for('report', id=id, alert=alert))
                # return  render_template('user_work.html', id=id, year=year, month=month, alert='Something went Wrong! Check that all the User info is correct generating report')
            # return dashboard(year, month, alert={'error': 'Error generating report'})
        
        pdfkit.from_string(template, 'report.pdf', options=options)
        log("pdf generated")
        sleep(1)
        return send_file('report.pdf', as_attachment=True)
    else:
        log("Something went Wrong!")
        return dashboard( month, month, alert=alert)


@app.errorhandler(404)
def not_foud(e):
    return render_template('not_found.html')
