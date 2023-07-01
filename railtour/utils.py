from datetime import datetime,timedelta,date

DEF_DATE = date(2021, 6, 1)
DEF_DATETIME = datetime(2021,6,1)

def make_datetime(t):
    return datetime.combine(DEF_DATE, t)

def handle_timedelta(s):
    s = s.strip(' "')
    word_list = s.split(" ")
    s = word_list[-1]
    t = datetime.strptime(s, "%H:%M:%S")
    return timedelta(hours=t.hour, minutes=t.minute)

def add_time(cas, doba):
    den = make_datetime(cas)
    posun_den = den + doba
    return posun_den.time()

def timedelta_to_time(td):
    posun_den = DEF_DATETIME + td
    return posun_den.time()

def time_to_timedelta(t):
    den = make_datetime(t)
    return den - DEF_DATETIME

def datetime_to_timedelta(t):
    return t-t.replace(second=0, hour=0, minute=0)

def time_diff(cas2, cas1):
    den1 = make_datetime(cas1)
    den2 = make_datetime(cas2)
    if cas2 < cas1:
        den2 = den2 + timedelta(days=1)
    return den2 - den1

def make_time(x):
    return x.time()