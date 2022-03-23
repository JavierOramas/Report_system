import datetime
def format(date):
    return datetime.datetime.strptime(date, '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')

def get_date(date):
    try:
        return datetime.datetime.strptime(date, '%d/%m/%y %H:%M')
    except:
        return datetime.datetime.strptime(date, '%d/%m/%y')