def get_supervisors():
    return [i.lower() for i in  ['BCBA', 'BCBA (L)', 'BCaBA']]

def get_admins():
    return [i.lower() for i in  ['BCBA', 'BCBA (L)', 'BCaBA', 'admin']]
