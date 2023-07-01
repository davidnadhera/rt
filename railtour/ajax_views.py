from django.http import HttpResponse
from django.shortcuts import render
from django.core import serializers
from datetime import datetime, timedelta
from .consts import *
from .railtour3 import Railtour
import pickle
import pandas as pd
from railtour.models import Status
    
def detail(request, id, koef):
    ec = pd.read_csv(f'data2/ec{id//100000}.csv', parse_dates=['departure','arrival'])
    # ec = pd.read_pickle('data2/edgeconn.pickle')
    # ec.departure = pd.to_datetime(ec.departure)
    # ec.arrival = pd.to_datetime(ec.arrival)
    stan = pd.read_pickle('data2/stanice_nazvy.pickle')
    hrana = ec[ec.edge_id==id]
    modif_spoje = []
    for _,spoj in hrana.iterrows():
        if pd.isna(spoj.train):
            new_spoj = {'odjezd': '',
                            'stanice': stan[spoj.point_from_id],
                            'vlak': 'pěšky',
                            'km': spoj.km,
                            'prijezd': ''}
        else:
            new_spoj = {'odjezd': spoj.departure,
                            'stanice': stan[spoj.point_from_id],
                            'vlak': spoj.train,
                            'km': '',
                            'prijezd': spoj.arrival}
        modif_spoje.append(new_spoj)
    modif_spoje[0]['prijezd'] = modif_spoje[1]['odjezd']
    modif_spoje[0]['odjezd'] = modif_spoje[0]['prijezd'] - (1+koef)*timedelta(seconds=int(hrana.iloc[0]['duration']))
    modif_spoje[-1]['odjezd'] = modif_spoje[-2]['prijezd']
    modif_spoje[-1]['prijezd'] = modif_spoje[-1]['odjezd'] + (1+koef)*timedelta(seconds=int(hrana.iloc[-1]['duration']))

    return render(request, 'railtour/detail.html', {'spoje': modif_spoje, 'cil': stan[int(hrana.iloc[-1]['point_to_id'])]})

def detail_trasy(request, id):
    vysledky = pd.read_pickle("data2/vysledky.pickle")
    chp = pd.read_pickle("data2/checkpointy_alt.pickle")
    param_trasy = request.session.get('_param_trasy', {})
    unava = param_trasy.get('tiredness',0.0)
    vysledek = vysledky.loc[id]
    modif_hrany = []
    for stanice, (prev_stanice, cas, next_cas, premie_cas, premie_inday, premie_kraje, premie_postupka, premie_utecha,
                  body, km, trasa) in vysledek.hrany.items():
        modif_hrany.append({'nazev': chp.at[prev_stanice,'name'],
                            'odjezd': cas,
                            'prijezd': next_cas,
                            'id': trasa,
                            'body': body,
                            'km': km,
                            'body_premie': premie_cas,
                            'body_kraje': premie_kraje,
                            'body_inday': premie_inday,
                            'body_postupka': premie_postupka,
                            'body_utecha': premie_utecha})
    return render(request, 'railtour/detail_trasy.html', {'hrany': modif_hrany, 'id': id,
                                                          'cil': chp.at[vysledek.stanice,'name'],
                                                          'unava': unava })

def change_doba1(request):
    id = int(request.POST['id'])
    new_doba = datetime.fromisoformat(request.POST['doba'])
    chp = pd.read_pickle('data2\\checkpointy_alt.pickle')
    print(chp.at[id,'bonus1'])
    chp.at[id,'bonus1'] = new_doba
    print(chp.at[id, 'bonus1'])
    pd.to_pickle(chp,'data2\\checkpointy_alt.pickle')
    return HttpResponse("")

def change_doba2(request):
    id = int(request.POST['id'])
    new_doba = datetime.fromisoformat(request.POST['doba'])
    chp = pd.read_pickle('data2\\checkpointy_alt.pickle')
    print(chp.at[id,'bonus2'])
    chp.at[id,'bonus2'] = new_doba
    print(chp.at[id, 'bonus2'])
    pd.to_pickle(chp,'data2\\checkpointy_alt.pickle')
    return HttpResponse("")

def change_active(request):
    id = int(request.POST['id'])
    is_active = int(request.POST['active'])
    chp = pd.read_pickle('data2\\checkpointy_alt.pickle')
    chp.at[id,'active'] = (is_active == 1)
    today = datetime.today().date()
    if today > starttime.date():
        rozdil1 = chp.at[id,'bonus1'] - starttime
        rozdil2 = chp.at[id,'bonus2'] - starttime
        chp.at[id,'bonus1'] = today + rozdil1 + timedelta(hours=4)
        chp.at[id,'bonus2'] = today + rozdil2 + timedelta(hours=4)
    pd.to_pickle(chp,'data2\\checkpointy_alt.pickle')
    return HttpResponse("")

def pocet_tras(request):
    vysledky = pd.read_pickle('data2\\vysledky.pickle')
    return HttpResponse(len(vysledky))

def iterace(request):
    zadani = Status.objects.first()
    return HttpResponse(f"{zadani.curr_iteration};{zadani.curr_route_number}")

def zastavit(request):
    zadani = Status.objects.first()
    zadani.curr_iteration = -1
    zadani.save()
    return HttpResponse('')

def fetch_trasy(request):
    vysledky = pd.read_pickle('data2\\vysledky.pickle')
    chps = pd.read_pickle('data2\\checkpointy_alt.pickle')
    row = int(request.POST.get('row', 0))
    razeni = int(request.POST.get('razeni', 1))
    Praha = (request.POST.get('Praha', False) == '1')
    start = list([int(x) for x in request.POST.getlist('start[]', list())])
    cil = list([int(x) for x in request.POST.getlist('cil[]', list())])
    if razeni == 1:
        vysledky = vysledky.sort_values(['vykon','body','km'],ascending=[False,False,True])
    elif razeni == 2:
        vysledky = vysledky.sort_values(['body','vykon','km'],ascending=[False,False,True])
    elif razeni == 3:
        vysledky = vysledky.sort_values(['premie','vykon','km'],ascending=[False,False,True])
    elif razeni == 4:
        vysledky['body_bez_premii'] = vysledky.body-vysledky.premie
        vysledky = vysledky.sort_values(['body_bez_premii','vykon','km'],ascending=[False,False,True])
    elif razeni == 5:
        vysledky['prvni_klic'] = vysledky['hrany'].apply(
            lambda x: next(iter(x.keys())) if isinstance(x, dict) else None)
        max_indices = vysledky.groupby(['prvni_klic'])['vykon'].transform('max') == vysledky.vykon
        vysledky = vysledky[max_indices]
    elif razeni == 6:
        max_indices = vysledky.groupby(['stanice'])['vykon'].transform('max') == vysledky.vykon
        vysledky = vysledky[max_indices]
    if Praha:
        vysledky = vysledky.loc[[PRAHA_ID in x for x in vysledky['hrany']],vysledky.columns]
    if start:
        vysledky['prvni_klic'] = vysledky['hrany'].apply(lambda x: next(iter(x.keys())) if isinstance(x, dict) else None)
        vysledky = vysledky.loc[vysledky['prvni_klic'].isin(start),vysledky.columns]
    if cil:
        vysledky = vysledky.loc[vysledky['stanice'].isin(cil), vysledky.columns]

    vysledky = vysledky.iloc[row:row+ROWS_PER_PAGE]
    vysledky['prvni_klic'] = vysledky['hrany'].apply(lambda x: next(iter(x.keys())) if isinstance(x, dict) else None)
    vysledky['druhy_klic'] = vysledky['hrany'].apply(lambda x: list(x.keys())[1] if isinstance(x, dict) and len(x.keys()) > 1 else None)

    modif_vysledky = []
    for i,vysledek in vysledky.iterrows():
        modif_vysledky.append({'checkpoint': chps.at[vysledek.stanice,'name'],
                               'prijezd': vysledek.cas,
                               'body': f"{vysledek['body']} ({vysledek['premie']})" if COUNT_PREMIE else vysledek.body,
                               'km': round(vysledek.km,1),
                               'vykon': round(vysledek.vykon,2),
                               'spanek': 'ano' if vysledek.spanek else 'ne',
                               'prvni': chps.at[vysledek.prvni_klic,'name'][:41],
                               'druhy': chps.at[vysledek.druhy_klic,'name'][:41],
                               'id': i})

    return render(request, 'railtour/vypis_tras.html', {'vysledky': modif_vysledky})

def vypocet_tras(request):
    od = int(request.POST.get('od',3333))
    cas1 = request.POST.get('cas1',starttime.strftime('%Y-%m-%d'))
    cas2 = request.POST.get('cas2',starttime.strftime('%H:%M'))
    cas = datetime.combine(datetime.strptime(cas1,'%Y-%m-%d').date(),datetime.strptime(cas2,'%H:%M').time())
    visited = list([int(x) for x in request.POST.getlist('visited[]',list())])
    tempvisited = [int(x) for x in request.POST.getlist('tempvisited[]', list())]
    do = [int(x) for x in request.POST.getlist('cil[]',[CIL_ID])]
    body = int(request.POST.get('body',0))
    km = float(request.POST.get('km',0))
    spanek = (request.POST.get('spanek',False) == '1')
    mintime1 = request.POST.get('mintime1',CIL_OD.strftime('%Y-%m-%d'))
    mintime2 = request.POST.get('mintime2',CIL_OD.strftime('%H:%M'))
    mintime = datetime.combine(datetime.strptime(mintime1,'%Y-%m-%d').date(),datetime.strptime(mintime2,'%H:%M').time())
    maxtime1 = request.POST.get('maxtime1',CIL_DO.strftime('%Y-%m-%d'))
    maxtime2 = request.POST.get('maxtime2',CIL_DO.strftime('%H:%M'))
    maxtime = datetime.combine(datetime.strptime(maxtime1,'%Y-%m-%d').date(),datetime.strptime(maxtime2,'%H:%M').time())
    kroku = int(request.POST.get('kroku', 1000))
    koef_unavy = float(request.POST.get('koef_unavy', 0))
    uroven = int(request.POST.get('uroven', 0))
    kmcelk = float(request.POST.get('kmcelk', 185))
    C = float(request.POST.get('C', 0.25))
    temptime = datetime.fromisoformat(request.POST['temptime'])
    metoda = int(request.POST.get('metoda', 1))
    limitpocet = int(request.POST.get('limitpocet', 20))
    limitvykon = float(request.POST.get('limitvykon', 0))
    usepremie = (request.POST.get('usepremie',False) == '1')
    nemazat = (int(request.POST.get('nemazat',0)) > 0)
    spanekod = datetime.fromisoformat(request.POST['spanekod'])
    spanekdo = datetime.fromisoformat(request.POST['spanekdo'])
    kraje = [int(x) for x in request.POST.getlist('kraje[]', list())]
    postupka = [int(x) for x in request.POST.getlist('postupka[]', list())]
    utecha = (request.POST.get('consolation',False) == '1')

    zadani = {}
    zadani['start_point_id'] = od
    zadani['start_time'] = cas
    zadani['visited'] = visited
    zadani['tempblocked'] = tempvisited
    zadani['finish_points'] = do
    zadani['start_points'] = body
    zadani['start_km'] = km
    zadani['sleep'] = spanek
    zadani['finish_time_from'] = mintime
    zadani['finish_time_to'] = maxtime
    zadani['steps'] = kroku
    zadani['tiredness'] = koef_unavy
    zadani['start_inday'] = uroven
    zadani['max_km'] = kmcelk
    zadani['km_penalty'] = C
    zadani['tempblocked_to'] = temptime
    zadani['profit_type'] = metoda
    zadani['limit_amount'] = limitpocet
    zadani['limitprofit'] = limitvykon
    zadani['use_time_bonus'] = usepremie
    zadani['sleep_from'] = spanekod
    zadani['sleep_to'] = spanekdo
    zadani['start_regions'] = kraje
    zadani['start_streak'] = postupka
    zadani['start_consolation'] = utecha
    status = Status.objects.first()
    if not nemazat:
        status.curr_iteration = 0
        status.curr_route_number = 0
        status.save()

    param_trasy = zadani.copy()
    param_trasy['start_time'] = param_trasy['start_time'].isoformat()
    param_trasy['finish_time_from'] = param_trasy['finish_time_from'].isoformat()
    param_trasy['finish_time_to'] = param_trasy['finish_time_to'].isoformat()
    param_trasy['tempblocked_to'] = param_trasy['tempblocked_to'].isoformat()
    param_trasy['sleep_from'] = param_trasy['sleep_from'].isoformat()
    param_trasy['sleep_to'] = param_trasy['sleep_to'].isoformat()

    request.session['_param_trasy'] = param_trasy

    # rt = Railtour(zadani)
    # rt.vypocet(nemazat)
    return HttpResponse('')