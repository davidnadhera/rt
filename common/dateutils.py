from datetime import date,time,datetime,timedelta

def make_date(t):
    return datetime.combine(date(2000,1,1),t)

def timedelta_to_time(td):
    totsec = td.total_seconds()
    if td>=timedelta(days=1):
        d,z = divmod(totsec,3600*24)
        h = z//3600
        m = (z%3600)//60
        return f'{int(h):02}:{int(m):02} +{int(d)} den'
    else:
        h = totsec//3600
        m = (totsec%3600)//60
        return f'{int(h):02}:{int(m):02}'

def timedelta_to_time2(td):
    totsec = td.total_seconds()
    d, z = divmod(totsec, 3600 * 24)
    h = int(z // 3600)
    m = int((z % 3600) // 60)
    return time(hour=h, minute=m)

def time_to_timedelta(t):
    return timedelta(hours=t.hour,minutes=t.minute)
