from urllib.parse import urlencode
from django.urls import reverse
from railtour.models import Edge, Checkpoint, Region, RouteParameter
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models import F, Q, FloatField, ExpressionWrapper, DurationField, IntegerField, Func, Value, Case, When

from railtour.utils import timedelta_to_time, time_to_timedelta, add_time, time_diff
from datetime import timedelta, time
from .consts import *
from .hrana import Hrana
import pickle

# Create your views here. 

def stanice(request):
    stanice_list = {}
    kraje = Region.choices
    for i,_ in kraje:
        stanice_list[i] = Checkpoint.objects.filter(region=i).order_by('-active','id')
    return render(request, 'railtour/stanice.html', {'stanice_list': stanice_list, 'kraje': kraje})

def spojeni(request):
    if not request.GET:
        request.GET = request.session.get('_spojeni',{})
        redirect_url = reverse('railtour:spojeni')
        parameters = urlencode(request.GET)
        return redirect(f'{redirect_url}?{parameters}')

    chp_list = Checkpoint.objects.filter(active=True).order_by('id')
    od = int(request.GET.get('od',0))
    do = int(request.GET.get('do',0))
    hrany = []
    if od and do:        
        hrany = Edge.objects.filter(~Q(arrival=F('next_arrival')),point_from_id=od,point_to_id=do,departure__lt=timedelta(days=1)).order_by('departure')
        for hrana in hrany:
            hrana.time_departure = timedelta_to_time(hrana.departure)
            hrana.time_arrival = timedelta_to_time(hrana.arrival)
            hrana.profit1 = round(hrana.point_to.points / (hrana.arrival-hrana.departure).total_seconds() * 3600, 2)
            hrana.profit2 = round(hrana.point_to.points - (hrana.arrival-hrana.departure).total_seconds() / 3600, 2)
            hrana.str_duration = str(hrana.arrival-hrana.departure)[:-3]
    request.session['_spojeni'] = request.GET
    return render(request, 'railtour/spojeni.html', {'chp_list': chp_list, 'od': od, 'do': do, 'hrany': hrany})

def odjezdy(request):
    if request.method == "POST":
        request.session['_odjezdy'] = request.POST
        return redirect(request.META['HTTP_REFERER'])
    
    odjezdy_params = request.session.get('_odjezdy',{})
    chp_list = Checkpoint.objects.filter(active=True).order_by('id')  
    od = int(odjezdy_params.get('od',0))
    cas = time.fromisoformat(odjezdy_params.get('cas', '00:00'))
    td_cas = time_to_timedelta(cas)
    td_msec = td_cas.total_seconds()*1000000
    td_day = timedelta(days=1)
    odjezd = int(odjezdy_params.get('odjezd', 1))
    razeni = int(odjezdy_params.get('razeni', 1))
    if odjezdy_params:
        if odjezd == 1:            
            odjezdy = Edge.objects.filter(point_to__active=True,point_from_id=od,departure__gte=td_cas,prev_departure__lt=td_cas)\
            .annotate(profit1=ExpressionWrapper(3600000000.0*F('point_to__points'), output_field=FloatField())/(ExpressionWrapper(F('arrival'), output_field=FloatField())-td_msec))\
            .annotate(profit2=ExpressionWrapper(F('point_to__points'), output_field=FloatField())-(ExpressionWrapper(F('arrival'), output_field=FloatField())-td_msec)/3600000000.0)\
            .all()
            match razeni:
                case 1:
                    odjezdy = odjezdy.order_by('arrival','-departure')
                case 2:
                    odjezdy = odjezdy.order_by('departure','arrival')
                case 3:
                    odjezdy = odjezdy.order_by('-arrival','-departure')
                case 4:
                    odjezdy = odjezdy.order_by('-departure','arrival')
                case 5:
                    odjezdy = odjezdy.order_by('-profit1','arrival')
                case 6:
                    odjezdy = odjezdy.order_by('-profit2','arrival')
        else:
            odjezdy = Edge.objects.filter(Q(arrival__lte=td_cas,next_arrival__gt=td_cas)|Q(arrival__lte=td_cas+td_day,next_arrival__gt=td_cas+td_day,next_day=True),point_from__active=True,point_to_id=od)\
            .annotate(real_arrival=Case(
                                        When(arrival__lte=td_cas,next_arrival__gt=td_cas, then=F('arrival')+td_day),
                                        default=F('arrival'),
                                        output_field=DurationField(),
                                    ))\
            .annotate(modif_time  =Case(
                                        When(arrival__lte=td_cas,next_arrival__gt=td_cas, then=Value(td_cas,output_field=DurationField())),
                                        default=Value(td_cas+td_day,output_field=DurationField()),
                                        output_field=DurationField(),
                                    ))\
            .annotate(profit1=ExpressionWrapper(3600000000.0*F('point_from__points'), output_field=FloatField())/(ExpressionWrapper(F('modif_time')-F('departure'), output_field=FloatField())))\
            .annotate(profit2=ExpressionWrapper(F('point_from__points'), output_field=FloatField())-(ExpressionWrapper(F('modif_time')-F('departure'), output_field=FloatField()))/3600000000.0)\
            .all()
            match razeni:
                case 1:
                    odjezdy = odjezdy.order_by('real_arrival','next_day','-departure')
                case 2:
                    odjezdy = odjezdy.order_by('-next_day','departure','-real_arrival')
                case 3:
                    odjezdy = odjezdy.order_by('-real_arrival','next_day','-departure')
                case 4:
                    odjezdy = odjezdy.order_by('next_day','-departure','-real_arrival')
                case 5:
                    odjezdy = odjezdy.order_by('-profit1')
                case 6:
                    odjezdy = odjezdy.order_by('-profit2')
        for hrana in odjezdy:
            hrana.time_departure = timedelta_to_time(hrana.departure)
            hrana.time_arrival = timedelta_to_time(hrana.arrival) 
            hrana.str_duration = str(hrana.arrival-hrana.departure)[:-3]
    else:
        odjezdy = []
   
    return render(request, 'railtour/odjezdy.html', {'chp_list': chp_list, 'od': od, 'cas': cas,
                                                     'odjezd': odjezd, 'razeni': razeni, 'hrany': odjezdy})

def trasy(request):
    chp_list = Checkpoint.objects.filter(active=True).order_by('id')
    kraje = Region.choices[:-1]
    zadani = RouteParameter.objects.last()
    param_trasy = request.session.get('_param_trasy',{})
    if not zadani:
        zadani = RouteParameter.objects.create(start_point_from=Checkpoint.objects.get(id=START_ID),
                                               finish_points=[CIL_ID])
    return render(request, 'railtour/trasy.html', {'chp_list': chp_list, 'kraje': kraje,
                                                   'zadani': zadani, 'start_id': START_ID,
                                                   'praha_id': PRAHA_ID, 'cil_id': CIL_ID,
                                                   'cil_od': CIL_OD,
                                                   'cil_do': CIL_DO,
                                                   'starttime': STARTTIME,
                                                   'prahadates': PRAHADATES, 'prahatimes': PRAHATIMES,
                                                   'razeni': int(param_trasy.get('razeni',1)),
                                                   'Praha': int(param_trasy.get('Praha',0)),
                                                   'start': param_trasy.get('start',[]),
                                                   'cil': param_trasy.get('cil',[])})

def test(request):
    q_chp = Checkpoint.objects.all()
    chps = dict((obj.id, obj) for obj in q_chp)

    q_edge = Edge.objects.order_by('point_from_id','point_to_id','departure').all()
    pfi = None
    pti = None
    graph = {}
    for edge in q_edge:

        if pfi != edge.point_from_id:
            graph[edge.point_from_id] = {}
            print(edge.point_from_id)
        if pti != edge.point_to_id:
            graph[edge.point_from_id][edge.point_to_id] = {}
        graph[edge.point_from_id][edge.point_to_id][edge.departure] = Hrana(edge)

        pfi = edge.point_from_id
        pti = edge.point_to_id

    with open("pickle_data/graph.pickle", "wb+") as file:
        pickle.dump(graph, file)

    return HttpResponse()


def test2(request):
    with open("pickle_data/graph.pickle", "rb") as file:
        graph = pickle.load(file)
    active = list(Checkpoint.objects.filter(active=True).values_list('id',flat=True))
    active_graph = {}
    for start in active:
        print(start)
        x_dict = {}
        if start in graph:
            for cil in active:
                y_dict = {}
                if cil in graph[start]:
                    y_dict = graph[start][cil]
                x_dict[cil] = y_dict
        active_graph[start] = x_dict

    with open("pickle_data/active_graph.pickle", "wb+") as file:
        pickle.dump(active_graph, file)







    return HttpResponse()