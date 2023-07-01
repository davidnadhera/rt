from railtour.consts import *
import pickle
from collections import defaultdict
from time import perf_counter

class Trasa():
    next_id = 0

    def __init__(self,parameters):
        self.id = Trasa.next_id
        Trasa.next_id += 1
        self.parameters = parameters


    def set_start(self):
        self.checkpoint = self.parameters.start_point_id
        self.curr_time = self.parameters.start_time
        self.points = self.parameters.start_points
        self.premium_points = 0
        self.km = self.parameters.start_km
        self.regions = self.parameters.start_regions.copy()
        self.visited = self.parameters.visited.copy()+[self.checkpoint]
        self.streak = self.parameters.start_streak.copy()
        self.streak1 = all(elem in self.streak  for elem in range(2,6))
        self.streak2 = all(elem in self.streak  for elem in range(3,7))
        self.inday = self.parameters.start_inday
        self.consolation = self.parameters.start_consolation
        self.route_connections = []
        self.sleep = self.parameters.sleep



    @property
    def profit1(self):
        if self.checkpoint == CIL_ID:
            doba = CILTIME - self.parameters.start_time
        else:
            doba = self.curr_time - self.parameters.start_time
        doba = doba - KOEF_VZD * (1 - (self.curr_time-STARTTIME) / zlom) * (CILTIME-self.timeline)
        doba = doba.total_seconds()
        penale = max(0, (self.km - kmsec * doba) * self.parameters.km_penalty)
        if doba:
            return (self.points - penale) / doba * 60.0 * 60.0
        else:
            return 0.0

    @property
    def profit2(self):
        if self.checkpoint == CIL_ID:
            doba = CILTIME - self.parameters.start_time
        else:
            doba = self.curr_time - self.parameters.start_time
        doba = doba - KOEF_VZD * (1 - (self.curr_time-STARTTIME) / zlom) * (CILTIME-self.timeline)
        doba = doba.total_seconds()
        penale = max(0, (self.km - kmsec * doba) * self.parameters.km_penalty)
        if doba:
            return self.points - penale - doba / 60.0 / 60.0
        else:
            return 0.0

    def count_profit(self):
        if self.parameters.profit_type == 1:
            self.profit = self.profit1
        else:
            self.profit = self.profit2

    def __lt__(self, other):
        return self.profit > other.profit

    @staticmethod
    def get_results_by_params(request,zadani):
        with open("pickle_data/vysledky.pickle", "rb") as file:
            vysledky = pickle.load(file)
        vysledky = list(vysledky.values())
        praha = (request.POST.get('Praha',False) == '1')
        od = [int(x) for x in request.POST.getlist('start[]',[])]
        do = [int(x) for x in request.POST.getlist('cil[]',[])]
        if praha:
            vysledky = [x for x in vysledky if PRAHA_ID in x.visited]
        if od:
            vysledky = [x for x in vysledky if x.visited[0]==od]
        if do:
            vysledky = [x for x in vysledky if x.checkpoint==do]
        return vysledky

    def add_connection(self, new_cas, presun=None, hrana=None, spanek=None, perf=None):
        if not perf:
            perf = defaultdict(float)
        perf['d1'] -= perf_counter()
        if presun:
            cil_id = presun.point_to_id
            region = presun.point_to.checkpoint.region
            points = presun.point_to.checkpoint.points
            bonus1 = presun.point_to.checkpoint.bonus1
            bonus2 = presun.point_to.checkpoint.bonus2
        elif hrana:
            cil_id = hrana.point_to_id
            region = hrana.region
            points = hrana.points
            bonus1 = hrana.bonus1
            bonus2 = hrana.bonus2
        elif spanek:
            cil_id = self.checkpoint
        perf['d1'] += perf_counter()
        perf['d2'] -= perf_counter()
        result = Trasa(parameters=self.parameters)
        perf['d2'] += perf_counter()
        perf['d3'] -= perf_counter()
        result.checkpoint = cil_id
        if cil_id == CIL_ID:
            new_cas = CILTIME
        result.curr_time = new_cas
        druhyden = new_cas.date() > self.curr_time.date()
        if druhyden:
            result.inday = 0
            result.regions = []
            result.streak = []
        else:
            result.inday = self.inday
            result.regions = self.regions.copy()
            result.streak = self.streak.copy()
        if druhyden or (cil_id == CIL_ID):
            result.consolation = True
            if self.parameters.use_time_bonus and self.consolation:
                new_premie_u = 2
            else:
                new_premie_u = 0
        else:
            new_premie_u = 0
            result.consolation = self.consolation
        perf['d3'] += perf_counter()
        perf['d4'] -= perf_counter()
        if (presun or hrana):
            result.inday += 1
            if region in range(1, 14):
                result.regions.append(region)
                result.regions = list(set(result.regions))
            result.streak.append(points)
            result.streak1 = all(elem in result.streak for elem in range(2, 6))
            result.streak2 = all(elem in result.streak for elem in range(3, 7))
            if (result.inday in [6, 7, 8, 9]) and (cil_id != CIL_ID):
                new_premie_d = 1
            else:
                new_premie_d = 0
            if (len(self.regions) == 3) and (len(result.regions) == 4):
                new_premie_k = 2
            else:
                new_premie_k = 0
            if self.parameters.use_time_bonus and (new_cas <= bonus1):
                new_premie_c = 2
                result.consolation = False
            elif self.parameters.use_time_bonus and (new_cas <= bonus2):
                new_premie_c = 1
                result.consolation = False
            else:
                new_premie_c = 0
            if result.streak2 and self.streak1 and not self.streak2:
                new_premie_p = 1
            elif result.streak2 and not self.streak2:
                new_premie_p = 3
            elif result.streak1 and not self.streak1:
                new_premie_p = 2
            else:
                new_premie_p = 0
            result.points = self.points + points + new_premie_p + new_premie_k + new_premie_c + new_premie_d + new_premie_u
            result.premium_points = self.premium_points + new_premie_p + new_premie_k + new_premie_c + new_premie_d + new_premie_u
            result.sleep = self.sleep
        else:
            result.streak1 = False
            result.streak2 = False
            new_premie_c = 0
            new_premie_d = 0
            new_premie_k = 0
            new_premie_p = 0
            result.points = self.points + 5
            result.premium_points = self.premium_points
            result.sleep = True
        perf['d4'] += perf_counter()
        perf['d5'] -= perf_counter()
        result.visited = self.visited.copy()
        if spanek:
            result.visited.append(SPANEK_ID)
            result.km = self.km
            result.timeline = self.timeline
        elif presun:
            result.visited.append(cil_id)
            result.km = self.km + presun.km
            result.timeline = presun.point_to.checkpoint.timeline
        else:
            result.visited.append(cil_id)
            result.km = self.km + hrana.km
            result.timeline = hrana.timeline
        perf['d5'] += perf_counter()
        perf['d6'] -= perf_counter()

        result.count_profit()
        perf['d6'] += perf_counter()
        perf['d7'] -= perf_counter()

        new_hrana = {'premie_c': new_premie_c,
                     'premie_d': new_premie_d,
                     'premie_k': new_premie_k,
                     'premie_p': new_premie_p,
                     'premie_u': new_premie_u}
        if spanek:
            new_hrana['sleep'] = True
        elif presun:
            new_hrana['transfer'] = presun.id
        elif hrana:
            new_hrana['edge'] = hrana.id
        perf['d7'] += perf_counter()
        perf['d8'] -= perf_counter()

        result.route_connections = self.route_connections.copy()
        result.route_connections.append(new_hrana)
        perf['d8'] += perf_counter()

        return result