import math
import calendar
import datetime

def round_half_up(n, decimals=2):
    multiplier = 10 ** decimals
    return math.floor(int(n)*multiplier + 0.5) / multiplier

def get_rbt_coordinator(db):
    coordinator = db.users.find_one({'ProviderId': 1382528})
    # print(coordinator)
    if coordinator:
        return coordinator['name']
    else:
        return "1382528"
def get_second_monday(year, month):
    c = calendar.Calendar(firstweekday=calendar.MONDAY)
    if month < 12:
        monthcal = c.monthdatescalendar(year, month+1)
    else:
        monthcal = c.monthdatescalendar(year+1, 1)
    d = monthcal[1][0].day
    if d > 7:
        return datetime.datetime.strftime(monthcal[1][0], "%m/%d/%Y")
    else:
        return datetime.datetime.strftime(monthcal[2][0], "%m/%d/%Y")