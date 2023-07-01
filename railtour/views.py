from urllib.parse import urlencode
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core import serializers
from railtour.utils import timedelta_to_time, time_to_timedelta, add_time, time_diff
from datetime import timedelta, time
from .consts import *
import pickle
import pandas as pd
from railtour.models import Status


# Create your views here.

def stanice(request):
    stanice_list = {}
    chp = pd.read_pickle('data2\\checkpointy_alt.pickle')
    for i in REGIONS.values():
        stanice_list[i] = chp[chp.region==i].sort_values(['active','id'],ascending=[False,True]).to_dict('records')
    return render(request, 'railtour/stanice.html', {'stanice_list': stanice_list, 'kraje': REGIONS})


def spojeni(request):
    if not request.GET:
        request.GET = request.session.get('_spojeni', {})
        if request.GET:
            redirect_url = reverse('railtour:spojeni')
            parameters = urlencode(request.GET)
            return redirect(f'{redirect_url}?{parameters}')
    chp = pd.read_pickle('data2\\checkpointy_alt.pickle')
    chp = chp.rename(columns={'id':'point_ptr_id'})
    chp_list = chp[chp.active].to_dict('records')
    od = int(request.GET.get('od', 0))
    do = int(request.GET.get('do', 0))
    if od and do:
        hrany = pd.read_pickle('data2\\bhrany1.pickle')
        hrany = hrany[(hrany.point_from_id==od) & (hrany.point_to_id==do) & (hrany.source==0) & (hrany.departure<timedelta(days=1))]
        hrany[['profit1','profit2']] = hrany[['profit1','profit2']].round(2)
        modif_hrany = hrany.to_dict('records')
        for hrana in modif_hrany:
            hrana['time_departure'] = timedelta_to_time(hrana['departure'])
            hrana['time_arrival'] = timedelta_to_time(hrana['arrival'])
            hrana['str_duration'] = str(hrana['arrival'] - hrana['departure'])[-8:-3]
    request.session['_spojeni'] = request.GET
    return render(request, 'railtour/spojeni.html', {'chp_list': chp_list, 'od': od, 'do': do, 'hrany': modif_hrany})


def odjezdy(request):
    if request.method == "POST":
        request.session['_odjezdy'] = request.POST
        return redirect(request.META['HTTP_REFERER'])

    odjezdy_params = request.session.get('_odjezdy', {})
    chp = pd.read_pickle('data2\\checkpointy_alt.pickle')
    chp = chp.rename(columns={'id':'point_ptr_id'})
    aktivni = chp[chp.active]
    chp_list = aktivni.to_dict('records')
    hrany = pd.read_pickle('data2\\bhrany1.pickle')
    od = int(odjezdy_params.get('od', 0))
    cas = time.fromisoformat(odjezdy_params.get('cas', '00:00'))
    td_cas = time_to_timedelta(cas)
    td_day = timedelta(days=1)
    odjezd = int(odjezdy_params.get('odjezd', 1))
    razeni = int(odjezdy_params.get('razeni', 1))
    if odjezdy_params:
        if odjezd == 1:
            odjezdy = hrany[(hrany['point_from_id']==od) & (hrany['departure']>=td_cas) & (hrany['point_to_id'].isin(aktivni.index))]
            min_indices = odjezdy.groupby(['point_to_id','source'])['departure'].transform('min') == odjezdy.departure
            odjezdy = odjezdy[min_indices]
            odjezdy['body'] = odjezdy.point_to_id.map(chp.points)
            odjezdy['profit1'] = odjezdy.body/(odjezdy.arrival-td_cas).dt.total_seconds()*3600
            odjezdy['profit2'] = odjezdy.body - (odjezdy.arrival - td_cas).dt.total_seconds() / 3600
            odjezdy['point_from'] = odjezdy.point_from_id.map(chp.name)
            odjezdy['point_to'] = odjezdy.point_to_id.map(chp.name)
            if razeni == 1:
                odjezdy = odjezdy.sort_values(['arrival', 'departure'],ascending=[True,False])
            elif razeni == 2:
                odjezdy = odjezdy.sort_values(['departure', 'arrival'],ascending=[True,True])
            elif razeni == 3:
                odjezdy = odjezdy.sort_values(['arrival', 'departure'],ascending=[False, False])
            elif razeni == 4:
                odjezdy = odjezdy.sort_values(['departure', 'arrival'],ascending=[False,True])
            elif razeni == 5:
                odjezdy = odjezdy.sort_values(['profit1', 'arrival'],ascending=[False,True])
            elif razeni == 6:
                odjezdy = odjezdy.sort_values(['profit2', 'arrival'],ascending=[False,True])
        else:
            odjezdy = hrany.loc[(hrany['point_to_id'] == od)  & (hrany['point_from_id'].isin(aktivni.index)),:]
            print(odjezdy[odjezdy.point_from_id==3045])
            odjezdy.loc[odjezdy.arrival>td_cas, 'departure'] -= timedelta(days=1)
            odjezdy.loc[odjezdy.arrival>td_cas, 'arrival'] -= timedelta(days=1)
            # dvakrát proto, že některé příjezdy mohou být o víc jak jeden den dopředu
            odjezdy.loc[odjezdy.arrival>td_cas, 'departure'] -= timedelta(days=1)
            odjezdy.loc[odjezdy.arrival>td_cas, 'arrival'] -= timedelta(days=1)
            print(odjezdy[odjezdy.point_from_id == 3045])
            max_indices = odjezdy.groupby(['point_from_id','source'])['arrival'].transform('max') == odjezdy.arrival
            columns_to_ignore = ['id']
            columns_to_check = odjezdy.columns.difference(columns_to_ignore)
            odjezdy = odjezdy[max_indices].drop_duplicates(subset=columns_to_check)
            print(odjezdy[odjezdy.point_from_id == 3045])
            odjezdy['body'] = odjezdy.point_from_id.map(chp.points)
            odjezdy['profit1'] = odjezdy.body/(td_cas-odjezdy.departure).dt.total_seconds()*3600
            odjezdy['profit2'] = odjezdy.body - (td_cas-odjezdy.departure).dt.total_seconds() / 3600
            odjezdy['point_from'] = odjezdy.point_from_id.map(chp.name)
            odjezdy['point_to'] = odjezdy.point_to_id.map(chp.name)
            if razeni == 1:
                odjezdy = odjezdy.sort_values(['arrival', 'departure'],ascending=[True,False])
            elif razeni == 2:
                odjezdy = odjezdy.sort_values(['departure', 'arrival'],ascending=[True,True])
            elif razeni == 3:
                odjezdy = odjezdy.sort_values(['arrival', 'departure'],ascending=[False, False])
            elif razeni == 4:
                odjezdy = odjezdy.sort_values(['departure', 'arrival'],ascending=[False, True])
            elif razeni == 5:
                odjezdy = odjezdy.sort_values(['profit1','departure'],ascending=[False,False])
            elif razeni == 6:
                odjezdy = odjezdy.sort_values(['profit2','departure'],ascending=[False,False])
        odjezdy = odjezdy.to_dict('records')
        for hrana in odjezdy:
            hrana['time_departure'] = timedelta_to_time(hrana['departure'])
            hrana['time_arrival'] = timedelta_to_time(hrana['arrival'])
            hrana['str_duration'] = str(hrana['arrival'] - hrana['departure'])[-8:-3]
    else:
        odjezdy = []

    return render(request, 'railtour/odjezdy.html', {'chp_list': chp_list, 'od': od, 'cas': cas,
                                                     'odjezd': odjezd, 'razeni': razeni, 'hrany': odjezdy})


def trasy(request):
    chp = pd.read_pickle('data2\\checkpointy_alt.pickle')
    chp = chp.rename(columns={'id':'point_ptr_id'})
    chp_list = chp[chp.active].to_dict('records')
    kraje = {key: value for key, value in REGIONS.items() if value != 15}
    param_trasy =  request.session.get('_param_trasy', '[]')
    zadani = Status.objects.all()
    if not zadani:
        zadani = Status(curr_iteration=-1,curr_route_number = 0)
        zadani.save()
    if not param_trasy:
        param_trasy = {'start_point_id':START_ID,
                            'finish_points':[CIL_ID],
                            'start_time': starttime,
                            'start_points': 0,
                            'start_km': 0.0,
                            'finish_time_from': CIL_OD,
                            'finish_time_to':CIL_DO,
                            'visited': [],
                            'sleep': False,
                            'use_time_bonus': False,
                            'tempblocked': [],
                            'tempblocked_to': BLOCK_DO,
                            'steps':  MAX_V_ITERACI,
                            'tiredness': UNAVA,
                            'limit_amount': LIMIT_POCET,
                            'limitprofit':  LIMIT_VYKON,
                            'max_km': TOTAL_KM,
                            'km_penalty': PENALE,
                            'profit_type': USE_VYKON,
                            'sleep_from': SPANEK_OD,
                            'sleep_to': SPANEK_DO,
                            'start_regions': [],
                            'start_streak':  [],
                            'start_inday': 0,
                            'start_consolation': True,
                            'distance_coef': KOEF_VZD,
                            'curr_iteration': -1,
                            'curr_route_number': 0}
    else:
        param_trasy['start_time'] = datetime.fromisoformat(param_trasy['start_time'])
        param_trasy['finish_time_from'] = datetime.fromisoformat(param_trasy['finish_time_from'])
        param_trasy['finish_time_to'] = datetime.fromisoformat(param_trasy['finish_time_to'])
        param_trasy['tempblocked_to'] = datetime.fromisoformat(param_trasy['tempblocked_to'])
        param_trasy['sleep_from'] = datetime.fromisoformat(param_trasy['sleep_from'])
        param_trasy['sleep_to'] = datetime.fromisoformat(param_trasy['sleep_to'])
    return render(request, 'railtour/trasy.html', {'chp_list': chp_list, 'kraje': kraje,
                                                   'zadani': param_trasy, 'start_id': START_ID,
                                                   'praha_id': PRAHA_ID, 'cil_id': CIL_ID,
                                                   'cil_od': CIL_OD,
                                                   'cil_do': CIL_DO,
                                                   'starttime': starttime,
                                                   'prahadates': PRAHADATES, 'prahatimes': PRAHATIMES,
                                                   'razeni': int(param_trasy.get('razeni', 1)),
                                                   'Praha': int(param_trasy.get('Praha', 0)),
                                                   'start': param_trasy.get('start', []),
                                                   'cil': param_trasy.get('cil', [])})

