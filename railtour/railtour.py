from datetime import date, time, datetime, timedelta
import heapdict
from .utils import make_datetime, datetime_to_timedelta
from .consts import *
from time import perf_counter
import pickle
from collections import defaultdict
from .trasa import Trasa
from .models import Checkpoint,FootTransfer
import bisect
import itertools

class Railtour():

    def __init__(self, parameters) -> None:
        self.parameters = parameters
        q_chp = Checkpoint.objects.filter(active=True).all()
        self.chps = dict((obj.id, obj) for obj in q_chp)
        self.trans = {}
        for chp in q_chp:
            q_trans = FootTransfer.objects.filter(point_from=chp,point_to__checkpoint__active=True).all()
            self.trans[chp.id] = list(q_trans)
        self.cache = {}
        self.vysledky = {}
        Trasa.next_id = 0
        self.temp_vysledky = defaultdict(list)
        self.iterace = heapdict.heapdict()
        self.x = 0
        self.perf_time = defaultdict(int)
        self.graph = {}

    def doIterace(self):
        def bisect_graph(graph,od,do):
            return bisect.bisect_left(graph[od][do],td_cas,key=lambda x:x.departure)

        pocet = 0
        print(f'Iterace: {self.x}')
        new_iterace = heapdict.heapdict()
        if self.temp_vysledky[self.x]:
            for vysledek in self.temp_vysledky[self.x]:
                if ((vysledek.checkpoint, frozenset(vysledek.visited)) not in self.iterace) or \
                    (self.iterace[(vysledek.checkpoint, frozenset(vysledek.visited))].profit < vysledek.profit):
                    self.iterace[(vysledek.checkpoint, frozenset(vysledek.visited))] = vysledek
        self.parameters.curr_iteration = self.x
        self.parameters.curr_route_number = len(self.iterace)
        self.parameters.save()
        while len(self.iterace) and (pocet<self.parameters.steps):
            self.perf_time['a']-=perf_counter()
            pocet += 1
            ((idstanice,frozenvisited),trasa) = self.iterace.popitem()
            visited = list(frozenvisited)
            alt_cas = trasa.curr_time + self.parameters.tiredness * self.chps[trasa.checkpoint].conn_time
            td_cas = datetime_to_timedelta(alt_cas)
            self.perf_time['a']+=perf_counter()
            self.perf_time['b']-=perf_counter()
            key = (idstanice,td_cas)
            if key in self.cache:
                hrany = self.cache[key]
            else:
                hrany = [self.graph[idstanice][i][bisect_graph(self.graph,idstanice,i)] for i in self.graph[idstanice] if self.graph[idstanice][i]]
                hrany.sort(key=lambda x: -x.profit)
                self.cache[key] = hrany
            self.perf_time['b']+=perf_counter()
                 
            self.perf_time['c']-=perf_counter()
            potenc_hrany = [x for x in hrany if x.point_to_id not in trasa.visited]
            if (trasa.curr_time<=self.parameters.tempblocked_to):
                potenc_hrany = [x for x in potenc_hrany if x.point_to_id not in self.parameters.tempblocked]

            hrany_do_cile = [x for x in potenc_hrany if x.point_to_id in self.parameters.finish_points]

            if (pocet > self.parameters.steps/10) and (self.x > 2):
                potenc_hrany = [x for x in potenc_hrany if x.profit >= self.parameters.limitprofit]
                potenc_hrany = potenc_hrany[:self.parameters.limit_amount]

            potenc_hrany = set(potenc_hrany)|set(hrany_do_cile)

            self.perf_time['c'] += perf_counter()

            for hrana in potenc_hrany:
                self.perf_time['h'] -= perf_counter()
                new_cas = alt_cas.replace(second=0, hour=0, minute=0)

                new_cas = new_cas + hrana.arrival + self.parameters.tiredness*hrana.final_transfer

                if (new_cas > hrana.timeline) or (new_cas>self.parameters.finish_time_to):
                    self.perf_time['h'] += perf_counter()
                    continue
                self.perf_time['h'] += perf_counter()
                self.perf_time['d'] -= perf_counter()
                new_trasa = trasa.add_connection(hrana=hrana, new_cas=new_cas, perf=self.perf_time)
                self.perf_time['d'] += perf_counter()
                self.perf_time['g'] -= perf_counter()
                if hrana.point_to_id != CIL_ID:
                    fs = frozenset(new_trasa.visited)
                    if ((hrana.point_to_id,fs) not in new_iterace) \
                            or (new_iterace[(hrana.point_to_id,fs)].profit < new_trasa.profit):
                        new_iterace[(hrana.point_to_id,fs)] = new_trasa
                if ((hrana.point_to_id in self.parameters.finish_points) and (new_cas>=self.parameters.finish_time_from)):
                    self.vysledky[new_trasa.id]=new_trasa
                self.perf_time['g']+=perf_counter()

            self.perf_time['e']-=perf_counter()
            if idstanice in self.trans:
                for presun in self.trans[idstanice]:

                    if (presun.point_to_id in trasa.visited):
                        continue

                    if (trasa.curr_time <= self.parameters.tempblocked_to) and (
                            presun.point_to_id in self.parameters.tempblocked):
                        continue

                    new_cas = trasa.curr_time+presun.time*(1+self.parameters.tiredness)
                    if (new_cas > self.chps[presun.point_to_id].timeline) or (new_cas>self.parameters.finish_time_to):
                        continue
                    new_trasa = trasa.add_connection(presun=presun, new_cas=new_cas, perf=self.perf_time)
                    fs = frozenset(new_trasa.visited)
                    if ((presun.point_to_id,fs) not in new_iterace) \
                            or (new_iterace[(presun.point_to_id,fs)].profit < new_trasa.profit):
                        new_iterace[(presun.point_to_id,fs)] = new_trasa
                    if (presun.point_to_id in self.parameters.finish_points) and (new_cas>=self.parameters.finish_time_from) and (new_cas<=self.parameters.finish_time_to):
                        self.vysledky[new_trasa.id]=new_trasa
            self.perf_time['e']+=perf_counter()

            self.perf_time['f']-=perf_counter()

            if (SPANEK_ID not in visited) and ((trasa.curr_time.time()<=time(hour=2)) or (trasa.curr_time.time()>=time(hour=20))) \
            and (trasa.curr_time<=self.parameters.sleep_to) and (trasa.curr_time>=self.parameters.sleep_from):
                new_cas = trasa.curr_time+timedelta(hours=6)
                new_trasa= trasa.add_connection(spanek=True, new_cas=new_cas, perf=self.perf_time)
                fs = frozenset(new_trasa.visited)
                if ((idstanice,fs) not in new_iterace) \
                        or (new_iterace[(idstanice,fs)].profit < new_trasa.profit):
                    new_iterace[(idstanice,fs)] = new_trasa
                if (idstanice in self.parameters.finish_points) and (new_cas <= self.parameters.finish_time_to) and (new_cas >= self.parameters.finish_time_from):
                    self.vysledky[new_trasa.id]=new_trasa
            self.perf_time['f']+=perf_counter()

        self.iterace = new_iterace


    def vypocet(self, nemazat):
        with open("pickle_data/active_graph.pickle", "rb") as file:
            self.graph = pickle.load(file)
        with open("pickle_data/cache.pickle", "rb") as file:
            self.cache = pickle.load(file)
        if nemazat:
            with open("pickle_data/vysledky.pickle", "rb") as file:
                self.vysledky = pickle.load(file)
            for vysledek in self.vysledky.values():
                self.temp_vysledky[len(vysledek.visited)].append(vysledek)
            self.x = min(self.temp_vysledky.keys())
        else:
            start = Trasa(self.parameters)
            start.set_start()
            start.timeline = self.chps[self.parameters.start_point_id].timeline
            start.count_profit()
            self.iterace[(start.checkpoint,frozenset(start.visited))] = start
            self.x = 0
        self.parameters.curr_iteration = self.x

        while len(self.iterace) and (self.parameters.curr_iteration >= 0):
            self.doIterace()
            self.parameters.refresh_from_db()
            self.x += 1
        print(self.perf_time)

        self.parameters.curr_iteration = -1
        self.parameters.save()

        self.vysledky = {k: v for k, v in sorted(self.vysledky.items(), key=lambda item: (-item[1].profit,-item[1].points,-item[1].km))}
        self.vysledky = dict(itertools.islice(self.vysledky.items(), 50000))


        with open("pickle_data/vysledky.pickle", "wb+") as file:
            pickle.dump(self.vysledky, file)

        with open("pickle_data/cache.pickle", "wb+") as file:
            pickle.dump(self.cache, file)
