import datetime
def format(date):
    try:
        return datetime.datetime.strptime(date, '%m/%d/%Y %H:%M').strftime('%m/%d/%y %H:%M')
    except:
        return datetime.datetime.strptime(date, '%m/%d/%Y %H:%M').strftime('%d/%m/%y %H:%M')
        
def get_date(date):
    if date[0] == ' ':
        date = date[1:]
    if date[-1] == ' ':
        date = date[:-1]
    try:
        return datetime.datetime.strptime(date, '%m/%d/%y %H:%M')
    except:
        try:
            return datetime.datetime.strptime(date, '%m/%d/%y')
        except:
            try:
                return datetime.datetime.strptime(date, '%d/%m/%y')
            except:
                return datetime.datetime.strptime(date, '%d/%m/%y %H:%M')