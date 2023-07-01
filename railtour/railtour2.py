from datetime import date, time, datetime, timedelta
import heapdict
from .models import Route,Edge,FootTransfer
from .utils import make_datetime, datetime_to_timedelta
from django.db.models import F, Q, FloatField, ExpressionWrapper, DurationField, IntegerField, Func, Value, Case, When
from django.core.cache import cache
from .consts import *
from time import perf_counter

class Railtour():

    def __init__(self, parameters) -> None:
        self.parameters = parameters

    def doIterace(self,iterace,results,x,a,b,c,d,e,f,g):
        pocet = 0
        print(f'Iterace: {x}')
        new_iterace = heapdict.heapdict()
        self.parameters.curr_iteration = x
        self.parameters.curr_route_number = len(iterace)
        self.parameters.save()
        while len(iterace) and (pocet<self.parameters.steps):
            a-=perf_counter()
            pocet += 1
            pocet_h = 0
            ((idstanice,frozenvisited),trasa) = iterace.popitem()
            visited = list(frozenvisited)
            alt_cas = trasa.curr_time + self.parameters.tiredness * trasa.checkpoint.conn_time
            td_cas = datetime_to_timedelta(alt_cas)
            td_msec = td_cas.total_seconds()*1000000
            a+=perf_counter()
            b-=perf_counter()
            key = f'{idstanice}-{td_cas}'
            hrany = cache.get(key)
            if not hrany:
                hrany = Edge.objects.select_related("point_to").select_related("point_to__point_ptr").filter(point_to__active=True,point_from_id=idstanice,departure__gte=td_cas,prev_departure__lt=td_cas)

                if (trasa.curr_time<=self.parameters.tempblocked_to):
                    hrany = hrany.exclude(point_to_id__in=self.parameters.tempblocked)

                if self.parameters.profit_type == 1:
                    hrany = hrany.annotate(profit=ExpressionWrapper(3600000000.0*F('point_to__points'), output_field=FloatField())/(ExpressionWrapper(F('arrival'), output_field=FloatField())-td_msec))
                else:
                    hrany = hrany.annotate(profit=ExpressionWrapper(F('point_to__points'), output_field=FloatField())-(ExpressionWrapper(F('arrival'), output_field=FloatField())-td_msec)/3600000000.0)

                hrany = hrany.order_by('-profit').values('profit','point_to_id','departure','arrival','final_transfer','km','id',
                                                         'point_to__name','point_to__points','point_to__region','point_to__timeline',
                                                         'point_to__bonus1','point_to__bonus2','point_to__conn_time')
                cache.set(key,list(hrany),None)  
            b+=perf_counter()
                 
            c-=perf_counter()            
            for hrana in hrany:

                if (hrana['point_to_id'] not in trasa.visited) and (((hrana['profit'] >= self.parameters.limitprofit) and (pocet_h<=self.parameters.limit_amount)) or (hrana['point_to_id'] in self.parameters.finish_points) or (pocet <= self.parameters.steps/10) or (x<=2)):
                    pocet_h += 1
                    
                    new_cas = alt_cas.replace(second=0, hour=0, minute=0)
                    

                    new_cas = new_cas + hrana['arrival'] + self.parameters.tiredness*hrana['final_transfer']

                    if (new_cas > hrana['point_to__timeline']) or (new_cas>self.parameters.finish_time_to):
                        continue

                    if ((hrana['profit'] >= self.parameters.limitprofit) and (pocet<=self.parameters.limit_amount)) or ((hrana['point_to_id'] in self.parameters.finish_points) and (new_cas>=self.parameters.finish_time_from)) or (pocet_h <= self.parameters.steps/10) or (x<=2):
                        new_trasa = trasa.add_connection(hrana=hrana, new_cas=new_cas)
                        if hrana['point_to_id'] != CIL_ID:
                            if ((hrana['point_to_id'],frozenset(new_trasa.visited)) not in new_iterace) \
                                    or (new_iterace[(hrana['point_to_id'],frozenset(new_trasa.visited))].profit < new_trasa.profit):
                                new_iterace[(hrana['point_to_id'],frozenset(new_trasa.visited))] = new_trasa
                        if ((hrana['point_to_id'] in self.parameters.finish_points) and (new_cas>=self.parameters.finish_time_from)):
                            results.append(new_trasa)
            c+=perf_counter() 

            d-=perf_counter()

            presuny = FootTransfer.objects\
            .select_related("point_to").select_related("point_to__checkpoint")\
            .filter(~Q(point_to_id__in=visited),point_to__checkpoint__isnull=False,point_to__checkpoint__active=True,point_from_id=idstanice)\
            .all()

            if (trasa.curr_time<=self.parameters.tempblocked_to):
                presuny = presuny.exclude(point_to_id__in=self.parameters.tempblocked)

            d+=perf_counter()
            e-=perf_counter()
            for presun in presuny:

                new_cas = trasa.curr_time+presun.time*(1+self.parameters.tiredness)
                if (new_cas > presun.point_to.checkpoint.timeline) or (new_cas>self.parameters.finish_time_to):
                    continue
                new_trasa = trasa.add_connection(presun=presun, new_cas=new_cas)
                if ((presun.point_to_id,frozenset(new_trasa.visited)) not in new_iterace) \
                        or (new_iterace[(presun.point_to_id,frozenset(new_trasa.visited))].profit < new_trasa.profit):
                    new_iterace[(presun.point_to_id,frozenset(new_trasa.visited))] = new_trasa
                if (presun.point_to_id in self.parameters.finish_points) and (new_cas>=self.parameters.finish_time_from) and (new_cas<=self.parameters.finish_time_to):
                    results.append(new_trasa)
            e+=perf_counter()

            f-=perf_counter()

            if (SPANEK_ID not in visited) and ((trasa.curr_time.time()<=time(hour=2)) or (trasa.curr_time.time()>=time(hour=20))) \
            and (trasa.curr_time<=self.parameters.sleep_to) and (trasa.curr_time>=self.parameters.sleep_from):
                new_cas = trasa.curr_time+timedelta(hours=6)
                new_trasa= trasa.add_connection(spanek=True, new_cas=new_cas)
                if ((idstanice,frozenset(new_trasa.visited)) not in new_iterace) \
                        or (new_iterace[(idstanice,frozenset(new_trasa.visited))].profit < new_trasa.profit):
                    new_iterace[(idstanice,frozenset(new_trasa.visited))] = new_trasa
                if (idstanice in self.parameters.finish_points) and (new_cas <= self.parameters.finish_time_to) and (new_cas >= self.parameters.finish_time_from):
                    results.append(new_trasa)
            f+=perf_counter()

        return new_iterace,a,b,c,d,e,f,g


    def vypocet(self, nemazat):
        iterace = heapdict.heapdict()
        # cache.clear()
        results = []
        x = 1000
        if nemazat:
            vysledky = Route.objects.all()
            for vysledek in vysledky:
                iterace[(vysledek.checkpoint_id,frozenset(vysledek.visited))] = vysledek
                x = len(vysledek.visited) if len(vysledek.visited)<x else x  
        else:
            Route.objects.all().delete()
            start = Route(curr_time = self.parameters.start_time,
                          points = self.parameters.start_points,
                          premium_points = 0,
                          km = self.parameters.start_km,
                          regions = self.parameters.start_regions.copy(),
                          visited = self.parameters.visited.copy(),
                          streak = self.parameters.start_streak.copy(),
                          streak1 = all(elem in self.parameters.start_streak  for elem in range(2,6)),
                          streak2 = all(elem in self.parameters.start_streak  for elem in range(3,7)),
                          inday = self.parameters.start_inday,
                          checkpoint = self.parameters.start_point,
                          parameters = self.parameters,
                          consolation = self.parameters.start_consolation,
                          route_connections={},
                          sleep = self.parameters.sleep)
            iterace[(self.parameters.start_point_id,frozenset([self.parameters.start_point]))] = start
            x = 1
        self.parameters.curr_iteration = x
        a = b = c = d = e = f = g = 0

        while len(iterace) and (self.parameters.curr_iteration >= 0):
            iterace,a,b,c,d,e,f,g = self.doIterace(iterace,results,x,a,b,c,d,e,f,g)
            self.parameters.refresh_from_db()
            x += 1
        print(a,b,c,d,e,f,g)

        self.parameters.curr_iteration = -1
        self.parameters.save()

        Route.objects.bulk_create(results)