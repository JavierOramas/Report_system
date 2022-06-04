import datetime
def format(date):
    return datetime.datetime.strptime(date, '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')

def get_date(date):
    if date[0] == ' ':
        date = date[1:]
    if date[-1] == ' ':
        date = date[:-1]
    try:
        return datetime.datetime.strptime(date, '%d/%m/%y %H:%M')
    except:
        return datetime.datetime.strptime(date, '%d/%m/%y')