from datetime import datetime,time,date,timedelta

MAX_V_ITERACI = 500
IDPESKY = 9999
IDSPANEK = 9998
starttime = datetime(year=2023, month=7, day=31, hour=9, minute=0)
ciltime = datetime(year=2023, month=8, day=4, hour=16, minute=0)
stred = datetime(year=2023, month=8, day=2, hour=12, minute=30)
norm = ciltime-stred
# CIL_OD = datetime(year=2023, month=8, day=1, hour=4, minute=0)
# CIL_DO = datetime(year=2023, month=8, day=1, hour=10, minute=0)
# CILS = list(range(3000,3297))
CIL_OD = ciltime-timedelta(hours=4)
CIL_DO = ciltime
CILS = [3334]

SPANEK_OD = datetime(year=2023, month=8, day=1, hour=20, minute=0)
SPANEK_DO = datetime(year=2023, month=8, day=4, hour=2, minute=0)
TEMP_BLOCK = []
BLOCK_DO = datetime(year=2023, month=8, day=2, hour=0, minute=0)
BLOCK = set() #range(3200,3260)
COUNT_PREMIE = False
TOTAL_KM = 185
PENALE = 0.25
UNAVA = 0
USE_VYKON = 1
HRANA, PRESUN, SPANEK = 0, 1, 2
MAX_VYSLEDKY = 50000
LIMIT_VYKON = 0
LIMIT_POCET = 10

PRAHATIMES = [time(8,23),time(20,23)]
PRAHADATES = [date(2023,7,31),date(2023,8,1),date(2023,8,2),date(2023,8,3),date(2023,8,4)]
SPANEK_ID = 3999
START_ID = 3333
CIL_ID = 3334
PRAHA_ID = 3000
KOEF_VZD = 0.5


celkdoba = CIL_DO - starttime
zlom = (ciltime-starttime)/2
kmsec = TOTAL_KM/celkdoba.total_seconds()

ROWS_PER_PAGE = 10

REGIONS = {
    'Liberecký' : 2,
    'Ústecký' : 3,
    'Karlovarský' : 4,
    'Plzeňský' : 5,
    'Jihočeský' : 6,
    'Středočeský' : 7,
    'Královehradecký' : 8,
    'Pardubický' : 9,
    'Vysočina' : 10,
    'Jihomoravský' : 11,
    'Zlínský' : 12,
    'Olomoucký' : 13,
    'Moravskoslezský' : 14,
    'Horské etapy' : 15,
}