import pandas as pd
import numpy as np
from datetime import datetime
import os
from super_roles.super_roles import get_supervisors

risen_supervisors = pd.DataFrame([])

RBTs = []
trainees = []
risen_supervisors = []
supervisors = []
providersErrors = []

# TODO get this from DB in other stuff


def get_trainee_codes():
    return [150582, 194640]


def get_supervisor_codes():
    return [150582, 194640, 150577, 255975]


def get_rbt_codes():
    return [150580, 298632]


def get_indirect_codes():
    return [194642, 150577]


def get_remote_individual_supervision_codes():
    return [150577]


def get_valid_ids():
    return [150582, 194640, 150577, 150580, 194642, 194641, 255975, 298632]


def get_supervisor_ids():
    return [150582, 194640, 150577, 255975]


def get_group_supervisor_ids():
    return [194641]


def get_ind_sup_meeting():
    return [150577]


def get_providers(path):
    return pd.read_csv(path, sep=',')


labels = ['Id', 'DateTimeFrom', 'DateTimeTo', 'TimeWorkedInHours', 'ProviderId',
          'ProviderFirstName', 'ProcedureCodeId', 'DateOfService', 'ClientId']


def get_data(path):
    df = pd.read_csv(path)
    print(df)
    return df.drop(df.columns.difference(labels), 1)


def verify_valid_overlapping(entry, i, providerName, procedureCodeId, providerId):
    procedure = entry[procedureCodeId]
    if entry[providerId] == i[providerId]:
        return False

    # 55 55NB - 55NB
    if procedure in [150582, 194640] and i[procedureCodeId] in [194640]:
        return True
    # 53 - 55 55NB
    if procedure in [150580, 298632] and i[procedureCodeId] in [150582, 194640]:
        return True
    # Ind Sup - Ind Sup
    if procedure in [150577] and i[procedureCodeId] == 150577:
        return True
    return False


def calculate_overlapping(entry, providerName, providerId, depured_data, procedureCodeId, client, DateTimeFrom, timeTo, risen_supervisors):
    overlapping = []

    try:
        entry_start = datetime.strptime(entry[DateTimeFrom], '%m/%d/%Y %H:%M')
        entry_end = datetime.strptime(entry[timeTo], '%m/%d/%Y %H:%M')
    except:
        try:
            entry_start = datetime.strptime(
                entry[DateTimeFrom], '%m/%d/%Y %H:%M:%S')
            entry_end = datetime.strptime(entry[timeTo], '%m/%d/%Y %H:%M:%S')
        except:
            try:
                entry_start = datetime.strptime(
                    entry[DateTimeFrom], '%m/%d/%y %H:%M:%S')
                entry_end = datetime.strptime(
                    entry[timeTo], '%m/%d/%y %H:%M:%S')
            except:
                entry_start = datetime.strptime(
                    entry[DateTimeFrom], '%m/%d/%y %H:%M')
                entry_end = datetime.strptime(entry[timeTo], '%m/%d/%y %H:%M')

    for i in depured_data:
        # print(verify_valid_overlapping(entry,i,providerName,procedureCodeId,providerId, risen_supervisors))
        if verify_valid_overlapping(entry, i, providerName, procedureCodeId, providerId):
            try:
                start = datetime.strptime(
                    i[DateTimeFrom], '%m/%d/%Y %H:%M')
                end = datetime.strptime(i[timeTo], '%m/%d/%Y %H:%M')
            except:
                try:
                    start = datetime.strptime(
                        i[DateTimeFrom], '%m/%d/%Y %H:%M:%S')
                    end = datetime.strptime(i[timeTo], '%m/%d/%Y %H:%M:%S')
                except:
                    try:
                        start = datetime.strptime(
                            i[DateTimeFrom], '%m/%d/%y %H:%M:%S')
                        end = datetime.strptime(
                            i[timeTo], '%m/%d/%y %H:%M:%S')
                    except:
                        start = datetime.strptime(
                            i[DateTimeFrom], '%m/%d/%y %H:%M')
                        end = datetime.strptime(
                            i[timeTo], '%m/%d/%y %H:%M')

            if i[client] != entry[client]:
                continue

            if (entry_start <= end and entry_end >= start) or (start <= entry_end and end >= entry_start):
                time = min(entry_end, end) - max(entry_start, start)
                print(min(entry_end, end), max(entry_start, start))
                print(time, "===", entry[providerName])
                if time != 0:
                    overlapping.append((entry, i, time))

    if len(overlapping) == 0:
        return []
    if len(overlapping) > 1:
        new_overlapping = ''
        for i in overlapping:
            if i[1][providerId] in risen_supervisors:
                overlapping = [i]
                break
            elif i[1][providerId] in supervisors:
                new_overlapping = [i]
            elif i[1][providerId] in trainees:
                new_overlapping = [i]
        if new_overlapping != '':
            overlapping = new_overlapping
    elif overlapping[0][1][procedureCodeId] == 150580:
        providersErrors.append(overlapping[0][1][providerId])

    return overlapping


def process(incoming_data, db_providers, db=None):

    final_ol = pd.DataFrame()
    try:
        supervisors = []
        risen_supervisors = []
        trainees = []
        RBTs = []
        providers_data = db.users.find()

        for i in providers_data:
            if i.role in get_supervisors():
                supervisors.append(i)
            else: 
                trainee.appennd(i)
    except:
        providers_data = get_providers(db_providers)
        supervisors = providers_data[providers_data['Type'] == 'Supervisor']
        risen_supervisors = providers_data[providers_data['Type']
                                       == 'Risen Supervisor']

        trainees = providers_data[providers_data['Status'] == 'Trainee']
        RBTs = providers_data[providers_data['Status'] == 'RBT']
    # print(risen_supervisors)
    data = get_data(incoming_data)
    supervisors_id = get_supervisor_codes()
    print(data)
    # eliminar datos no deseados
    # data = data.drop(data[data['ProcedureCodeId'].isin(get_valid_ids()).index, index=True)
    data.loc[data['ProcedureCodeId'].isin(get_valid_ids())]
    # data['data_filter1'] = data_filter
    # data = data.drop('data_filter1', 1)
    # st.dataframe(data)
    print(data)

    errors = []
    notifications = []
    depured_data = []
    non_supervisors = []
    names = {}

    cols = data.columns

    providerId = list(cols).index('ProviderId')
    providerName = list(cols).index('ProviderFirstName')
    procedureCodeId = list(cols).index('ProcedureCodeId')
    # print(procedureCodeId)
    DateTimeFrom = list(cols).index('DateTimeFrom')
    timeTo = list(cols).index('DateTimeTo')
    client = list(cols).index('ClientId')
    # clientName = list(cols).index('ClientFirstName')
    filter_supervisors = [i in supervisors_id for i in data.ProcedureCodeId]

    supervisors_data = data[filter_supervisors]

    supervisors_data = np.array(supervisors_data)

    # print(len(supervisors_data))

    for k in range(len(supervisors_data)):

        i = supervisors_data[k]
        if i[procedureCodeId] == 150577 and (i[providerId] in list(trainees['ProviderId']) or i[providerId] in list(RBTs['ProviderId'])):
            notifications.append(i)
            i[procedureCodeId] = 194642
            non_supervisors.append(i)
            continue

        if i[procedureCodeId] == 150582:
            if i[providerId] in list(risen_supervisors['ProviderId']+supervisors['ProviderId']):
                notifications.append(i)
                i[procedureCodeId] = 194640
                depured_data.append(i)
                continue

            if i[providerId] in list(RBTs['ProviderId']):
                errors.append(i)
                providersErrors.append(i[providerId])
                continue

            # if i[providerId] in list(trainees['ProviderId']):
                # errors.append(i)
                # providersErrors.append(i[providerId])
                # continue

        if i[procedureCodeId] == 194640 and i[providerId] in list(RBTs['ProviderId']):
            errors.append(i)
            providersErrors.append(i[providerId])
            continue
        # print(i)

        depured_data.append(i)


# Using procedure code id because its faster and better than procedure code
    print(data[data['ProviderFirstName'] == 'Gabriella'])
    code53 = np.array(data[[i in get_rbt_codes()
                      for i in data['ProcedureCodeId']]])
    code_doc = np.array(data[[i in get_indirect_codes()
                        for i in data['ProcedureCodeId']]])
    code55 = np.array(data[[i in get_supervisor_codes()
                      for i in data['ProcedureCodeId']]])
    code_meeting = np.array(
        data[[i in get_group_supervisor_ids() for i in data['ProcedureCodeId']]])
    code_ind_sup = np.array(
        data[[i in get_ind_sup_meeting() for i in data['ProcedureCodeId']]])

    # print(f"code55: {code55}")

    for i in code_doc:
        if i[procedureCodeId] == 194642 and (i[providerId] in list(supervisors['ProviderId']) or i[providerId] in list(risen_supervisors['ProviderId'])):
            notifications.append(i)
            i[procedureCodeId] = 150577
            depured_data.append(i)
            continue

        non_supervisors.append(i)

    for i in code_ind_sup:
        if i[providerId] in list(supervisors['ProviderId']) or i[providerId] in list(risen_supervisors['ProviderId']):
            depured_data.append(i)
        else:
            non_supervisors.append(i)

    for i in code55:
        if i[providerId] in list(risen_supervisors['ProviderId']):
            depured_data.append(i)
            continue
        non_supervisors.append(i)

    for i in code53:
        if i[providerId] in list(supervisors['ProviderId']) or i[providerId] in list(risen_supervisors['ProviderId']):
            errors.append(i)
            providersErrors.append(i[providerId])
            continue

        non_supervisors.append(i)

    # print(non_supervisors)
    if len(non_supervisors) > 0:
        non_supervisors = np.stack(non_supervisors, axis=0)
    if len(depured_data) > 0:
        depured_data = np.stack(depured_data, axis=0)
    if len(errors) > 0:
        errors = np.stack(errors, axis=0)

    overlappings = {}
    providers_data_with_errors = {}

    supervisors_meeting = []
    non_supervisors_meeting = []

    for i in code_meeting:
        if not i[providerId] in overlappings:
            overlappings[i[providerId]] = []

        if i[providerId] in supervisors['ProviderId'].tolist() or i[providerId] in risen_supervisors['ProviderId'].tolist():
            supervisors_meeting.append(i)
        else:
            non_supervisors_meeting.append(i)

    for i in non_supervisors_meeting:
        names[i[providerId]] = i[providerName]

        flag = False
        for j in supervisors_meeting:
            if i[DateTimeFrom] == j[DateTimeFrom]:
                overlappings[i[providerId]].append((i, j, datetime.strptime(
                    i[timeTo], '%m/%d/%Y %H:%M')-datetime.strptime(i[DateTimeFrom], '%m/%d/%Y %H:%M')))
                flag = True
                break
        if not flag:
            temp = i
            temp[providerName] = ''
            overlappings[i[providerId]].append(('', i, datetime.strptime(
                i[timeTo], '%m/%d/%Y %H:%M')-datetime.strptime(i[DateTimeFrom], '%m/%d/%Y %H:%M')))

    for i in non_supervisors:

        names[i[providerId]] = i[providerName]

        new_ol = calculate_overlapping(i, providerName=providerName, providerId=providerId, depured_data=depured_data, procedureCodeId=procedureCodeId,
                                       client=client, DateTimeFrom=DateTimeFrom, timeTo=timeTo, risen_supervisors=risen_supervisors)

        if not i[providerId] in overlappings:
            overlappings[i[providerId]] = []

        if len(new_ol) != 0:
            print(new_ol)
            overlappings[i[providerId]].append(new_ol)

    # if len(errors) > 0:
    #     pd.DataFrame(errors).to_csv('errors.csv')
    #     pd.DataFrame(supervisors_data).to_csv('supervisors_data.csv')
    # if len(notifications) > 0:
    #     notifications = pd.DataFrame(np.stack(notifications, axis=0), columns=cols)
    #     notifications.to_csv('auto_fixed.csv')

    lab = list(cols)
    lab.append('MeetingDuration')
    # print(overlappings)

    if not os.path.exists('done'):
        os.mkdir('done')

    for i in overlappings:
        ovl = []
        final_labels = labels+['MeetingDuration']
        for j in overlappings[i]:
            try:
                _, i_ol, time = j[0]
                if time.seconds == 0:
                    continue
                i_ol = np.append(i_ol, time.seconds/3600)
                ovl.append(i_ol)
            except:
                _, i_ol, time = j
                i_ol = np.append(i_ol, time.seconds/3600)
                ovl.append(i_ol)

        if len(ovl) > 0:
            ovl = pd.DataFrame(np.stack(ovl, axis=0), columns=lab)
            ovl = ovl[final_labels]
            # ovl = ol.drop(['ClientId'], axis=1)
            ovl["ProvId"] = i
            final_ol = final_ol.append(ovl)
            # ol.to_csv(path.join('done',names[i]+' '+str(i)+'.csv'))

    # print(final_ol)
    return final_ol
