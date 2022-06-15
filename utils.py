import math

def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(int(n)*multiplier + 0.5) / multiplier

def get_rbt_coordinator(db):
    coordinator = db.users.find_one({'ProviderId': 1382528})
    print(coordinator)
    return coordinator['name']