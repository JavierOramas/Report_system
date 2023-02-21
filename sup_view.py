import datetime_format


def inspect_supervisor(pid, db, year, month):

    p_list = list(db.Users.find())

    ovl = list(db.Registry.find(
        {'Supervisor': int(pid)}))
    users = []
    for item in ovl:
        if datetime_format.get_date(item["DateOfService"]).year == year:
            if datetime_format.get_date(item["DateOfService"]).month == month:
                users.append(item["ProviderId"])

    return set(users)
