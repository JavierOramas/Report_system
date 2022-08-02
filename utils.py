import math
import calendar 
import datetime

def round_half_up(n, decimals=2):
    multiplier = 10 ** decimals
    return math.floor(int(n)*multiplier + 0.5) / multiplier

def get_rbt_coordinator(db):
    coordinator = db.users.find_one({'ProviderId': 1382528})
    print(coordinator)
    return coordinator['name']

def get_second_monday(year, month):
    c = calendar.Calendar(firstweekday=calendar.SATURDAY)
    monthcal = c.monthdatescalendar(year, month)
    return datetime.datetime.strftime(monthcal[1][-1], "%m/%d/%Y")