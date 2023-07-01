from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Q, F
from railtour.models import Checkpoint,Edge,RouteParameter,Route,FootTransfer 
from railtour.utils import timedelta_to_time, add_time
from datetime import datetime, timedelta
from .consts import *
from .railtour import Railtour

def filtered_checkpoints(request):
    query = request.GET.get('searchData','')
    if query:
        if query.isnumeric():
            aktivni = Checkpoint.objects.filter(active=True,id=int(query)).order_by('id').all()
        else:
            aktivni = Checkpoint.objects.filter(active=True,name__contains=query).order_by('id').all()

        return render(request, 'railtour/checkpointy.html', {'chps': aktivni}) 
    else:
        return None
    
def detail(request, id):
    hrana = Edge.objects.get(id=id)
    spoje = hrana.connections.all()
    modif_spoje = []
    curr_time = timedelta_to_time(hrana.departure)
    for spoj in spoje:
        if spoj.transfer:
            new_spoj = {'odjezd': curr_time,
                            'stanice': spoj.transfer.point_from.name,
                            'vlak': 'pěšky',
                            'km': spoj.transfer.km,
                            'prijezd': add_time(curr_time,spoj.transfer.time)}         
        else:
            new_spoj = {'odjezd': spoj.connection.departure,
                            'stanice': spoj.connection.point_from.name,
                            'vlak': spoj.connection.train,
                            'km': '',
                            'prijezd': spoj.connection.arrival}
        curr_time = new_spoj['prijezd']
        modif_spoje.append(new_spoj)

    return render(request, 'railtour/detail.html', {'spoje': modif_spoje, 'cil': hrana.point_to.name})

def detail_trasy(request, id):
    route = Route.objects.get(id=id)
    cas = route.parameters.start_time
    chp = route.parameters.start_point
    modif_hrany = []
    for _,hrana in route.route_connections.items():
        if 'sleep' in hrana:
            new_cas = cas+timedelta(hours=6)
            modif_hrany.append({'nazev': chp.name,
                                'odjezd': cas,
                                'prijezd': new_cas,
                                'id': -1,
                                'body': 5,
                                'km': 0,
                                'body_premie': hrana['premie_c'],
                                'body_kraje': hrana['premie_k'],
                                'body_inday': hrana['premie_d'],
                                'body_postupka': hrana['premie_p'],
                                'body_utecha': hrana['premie_u']})
            cas = new_cas
        elif 'transfer' in hrana:
            transfer = FootTransfer.objects.get(id=hrana['transfer'])
            new_cas = cas+transfer.time
            modif_hrany.append({'nazev': transfer.point_to.name,
                                'odjezd': cas,
                                'prijezd': new_cas,
                                'id': -2,
                                'body': transfer.point_to.checkpoint.points,
                                'km': transfer.km,
                                'body_premie': hrana['premie_c'],
                                'body_kraje': hrana['premie_k'],
                                'body_inday': hrana['premie_d'],
                                'body_postupka': hrana['premie_p'],
                                'body_utecha': hrana['premie_u']})
            cas = new_cas
            chp = transfer.point_to 
        else:
            edge = Edge.objects.get(id=hrana['edge']) 
            new_cas = cas + route.parameters.tiredness * chp.checkpoint.conn_time                  
            new_cas = new_cas.replace(second=0, hour=0, minute=0) + edge.arrival + route.parameters.tiredness*edge.final_transfer
            odjezd = new_cas.replace(second=0, hour=0, minute=0) + edge.departure
            modif_hrany.append({'nazev': edge.point_to.name,
                                'odjezd': odjezd,
                                'prijezd': new_cas,
                                'id': edge.id,
                                'body': edge.point_to.points,
                                'km': edge.km,
                                'body_premie': hrana['premie_c'],
                                'body_kraje': hrana['premie_k'],
                                'body_inday': hrana['premie_d'],
                                'body_postupka': hrana['premie_p'],
                                'body_utecha': hrana['premie_u']}) 
            cas = new_cas
            chp = edge.point_to 
    return render(request, 'railtour/detail_trasy.html', {'hrany': modif_hrany, 'id': id})

def change_doba1(request):
    id = request.POST['id']
    new_doba = datetime.fromisoformat(request.POST['doba'])
    checkpoint = Checkpoint.objects.get(id=id)
    checkpoint.bonus1 = new_doba
    checkpoint.save()
    return HttpResponse("")

def change_doba2(request):
    id = request.POST['id']
    new_doba = datetime.fromisoformat(request.POST['doba'])
    checkpoint = Checkpoint.objects.get(id=id)
    checkpoint.bonus2 = new_doba
    checkpoint.save()
    return HttpResponse("")

def change_active(request):
    id = request.POST['id']
    is_active = int(request.POST['active'])
    checkpoint = Checkpoint.objects.get(id=id)
    checkpoint.active = (is_active == 1)
    today = datetime.today().date()
    if today > STARTTIME.date():
        rozdil1 = checkpoint.bonus1 - STARTTIME
        rozdil2 = checkpoint.bonus2 - STARTTIME
        checkpoint.bonus1 = today + rozdil1 + timedelta(hours=4)
        checkpoint.bonus2 = today + rozdil2 + timedelta(hours=4)
    checkpoint.save()
    return HttpResponse("")

def pocet_tras(request):
    vysledky = Route.get_results_by_params(request)
    return HttpResponse(len(vysledky))

def iterace(request):
    zadani = RouteParameter.objects.last()
    return HttpResponse(f'{zadani.curr_iteration};{zadani.curr_route_number}')

def zastavit(request):
    zadani = RouteParameter.objects.last()
    zadani.curr_iteration = -1
    zadani.save()
    return HttpResponse('')

def fetch_trasy(request):
    request.session['_param_trasy'] = request.POST
    vysledky = Route.get_results_by_params(request).annotate(points_without_bonus=F('points')-F('premium_points'))
    row = int(request.POST.get('row', 0))
    razeni = int(request.POST.get('razeni', 1))
    if razeni == 1:
        vysledky = vysledky.order_by('-profit','-points','km')
    elif razeni == 2:
        vysledky = vysledky.order_by('-points','-profit','km')
    elif razeni == 3:
        vysledky = vysledky.order_by('-premium_points','-profit','km')
    elif razeni == 4:
        vysledky = vysledky.order_by('-points_without_bonus','-profit','km')
    elif razeni == 5:
        vysledky = list(vysledky)
        vysledky.sort(key=lambda x: (-x.profit,-x.points,x.km))
        vysledky2 = {}
        vysledky3 = []
        for vysledek in vysledky:
            curr_id = vysledek.visited[0]
            if curr_id not in vysledky2:
                vysledky2[curr_id] = vysledek.profit
                vysledky3.append(vysledek)
            else:
                if vysledky2[curr_id] <= vysledek.profit+0.01:
                    vysledky3.append(vysledek)
        vysledky = vysledky3
    elif razeni == 6:
        vysledky = list(vysledky)
        vysledky.sort(key=lambda x: (-x.profit,-x.points,x.km))
        vysledky2 = {}
        vysledky3 = []
        for vysledek in vysledky:
            curr_id = vysledek.checkpoint.id
            if curr_id not in vysledky2:
                vysledky2[curr_id] = vysledek.profit
                vysledky3.append(vysledek)
            else:
                if vysledky2[curr_id] <= vysledek.profit+0.01:
                    vysledky3.append(vysledek)
        vysledky = vysledky3

    vysledky = vysledky[row:row+ROWS_PER_PAGE]

    modif_vysledky = []
    for vysledek in vysledky:
        modif_vysledky.append({'checkpoint': vysledek.checkpoint.name,
                               'prijezd': vysledek.curr_time,
                               'body': vysledek.points,
                               'km': round(vysledek.km,1),
                               'vykon1': round(vysledek.profit1,2),
                               'vykon2': round(vysledek.profit2,2),
                               'spanek': 'ano' if vysledek.sleep else 'ne',
                               'prvni': Checkpoint.objects.get(id=vysledek.visited[0]).name[:41],
                               'druhy': Checkpoint.objects.get(id=vysledek.visited[1]).name[:41],
                               'id': vysledek.id})

    return render(request, 'railtour/vypis_tras.html', {'vysledky': modif_vysledky})

def vypocet_tras(request):
    od = int(request.POST.get('od',3333))
    cas1 = request.POST.get('cas1',STARTTIME.strftime('%Y-%m-%d'))
    cas2 = request.POST.get('cas2',STARTTIME.strftime('%H:%M'))
    cas = datetime.combine(datetime.strptime(cas1,'%Y-%m-%d').date(),datetime.strptime(cas2,'%H:%M').time())
    visited = [int(x) for x in request.POST.getlist('visited[]',list())]
    tempvisited = [int(x) for x in request.POST.getlist('tempvisited[]', list())]
    do = [int(x) for x in request.POST.getlist('cil[]',[3334])]
    body = int(request.POST.get('body',0))
    km = float(request.POST.get('km',0))
    spanek = (request.POST.get('spanek',False) == '1')
    mintime1 = request.POST.get('mintime1',STARTTIME.strftime('%Y-%m-%d'))
    mintime2 = request.POST.get('mintime2',STARTTIME.strftime('%H:%M'))
    mintime = datetime.combine(datetime.strptime(mintime1,'%Y-%m-%d').date(),datetime.strptime(mintime2,'%H:%M').time())
    maxtime1 = request.POST.get('maxtime1',STARTTIME.strftime('%Y-%m-%d'))
    maxtime2 = request.POST.get('maxtime2',STARTTIME.strftime('%H:%M'))
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

    zadani = RouteParameter.objects.last()
    zadani.start_point_id = od
    zadani.start_time = cas
    zadani.visited = visited
    zadani.tempblocked = tempvisited
    zadani.finish_points = do
    zadani.start_points = body
    zadani.start_km = km
    zadani.sleep = spanek
    zadani.finish_time_from = mintime
    zadani.finish_time_to = maxtime
    zadani.steps = kroku
    zadani.tiredness = koef_unavy
    zadani.start_inday = uroven
    zadani.max_km = kmcelk
    zadani.km_penalty = C
    zadani.tempblocked_to = temptime
    zadani.profit_type = metoda
    zadani.limit_amount = limitpocet
    zadani.limitprofit = limitvykon
    zadani.use_time_bonus = usepremie
    zadani.sleep_from = spanekod
    zadani.sleep_to = spanekdo
    zadani.start_regions = kraje
    zadani.start_streak = postupka
    zadani.start_consolation = utecha
    if not nemazat:
        zadani.curr_iteration = 0
        zadani.curr_route_number = 0

    zadani.save()
    rt = Railtour(zadani)
    rt.vypocet(nemazat)
    return HttpResponse('')