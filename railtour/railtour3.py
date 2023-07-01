import numpy as np
import pandas as pd
from datetime import date, time, datetime, timedelta
import pickle
from timeit import default_timer as timer
from .consts import *

class Railtour():

    def __init__(self, parameters) -> None:
        self.parameters = parameters
        self.x = 0

    def doIterace(iterace):
        def count_next_hrany(next_iterace):
            next_iterace['next_hrany'] = [{**x[0], x[2] if x[12]!=SPANEK else IDSPANEK:(x[1], x[3], x[4], x[5], x[6], x[7], x[8], x[13], x[9], x[10], x[11])}
                                          for x in zip(next_iterace.hrany, next_iterace.stanice, next_iterace.next_stanice, next_iterace.x_odjezd,
                                                       next_iterace.next_cas, next_iterace.premie_cas, next_iterace.premie_inday,
                                                       next_iterace.premie_kraje, next_iterace.premie_postupka,next_iterace.next_body,
                                                       next_iterace.next_km, next_iterace.id, next_iterace.source, next_iterace.premie_utecha)]
            return next_iterace

        def count_vykon(next_iterace):
            doba = np.where(next_iterace.next_stanice == CIL_ID,
                            (ciltime - starttime).total_seconds(),
                            (next_iterace.next_cas - starttime).dt.total_seconds())
            penale = (next_iterace.next_km - kmsec * doba) * PENALE
            penale = np.where(penale > 0, penale, 0)
            # pomer = (next_iterace.next_cas - stred)/norm
            # docile = (ciltime-next_iterace.timeline).dt.total_seconds()
            # # doba = doba + pomer * docile
            # doba = doba + np.where(pomer>0,pomer,0)*docile
            if USE_VYKON == 2:
                vykon = next_iterace.next_body - penale - (doba / 3600)
            else:
                vykon = (next_iterace.next_body - penale) / doba * 3600

            return vykon

        print(x)
        iterace['u_cas'] = iterace.cas + UNAVA * iterace.conn_time
        iterace['n_cas'] = iterace.u_cas - iterace.u_cas.dt.normalize()
        start = timer()
        next_iterace = iterace.join(active_chp, how='cross')
        end = timer()
        a1 += (end-start)
        start = timer()
        next_iterace = next_iterace.sort_values(['n_cas','stanice','next_stanice'])
        end = timer()
        a2 += (end-start)
        start = timer()
        next_iterace = pd.merge_asof(next_iterace, hrany, left_on='n_cas', right_index=True, left_by=['stanice', 'next_stanice'],
                                     right_by=['point_from_id', 'point_to_id'], direction='forward', suffixes=(None,'_hrana'))
        end = timer()
        a3 += (end-start)
        start = timer()
        next_iterace = next_iterace.dropna(subset=['departure'])
        next_iterace = next_iterace.astype({"point_from_id": int, "point_to_id": int, "id": int, "points": int, "region": int, "source": int})
        next_iterace['x_odjezd'] = next_iterace.u_cas.dt.normalize()+next_iterace.departure-UNAVA * next_iterace.conn_time
        next_iterace['next_cas'] = next_iterace.u_cas.dt.normalize()+next_iterace.arrival+UNAVA*next_iterace.final_transfer
        next_iterace['next_km'] = next_iterace.km+next_iterace.km_hrana
        # next_iterace['source'] = HRANA
        end = timer()
        b+=(end-start)


        # ------------ Presuny ---------------

        # next_pres = pd.merge(iterace, pres_chp, left_on='stanice', right_index=True,
        #                         suffixes=(None, '_pres'))
        # next_pres = next_pres.rename(columns={'do':'next_stanice'})
        # next_pres['next_cas'] = next_pres.cas+(1+UNAVA)*next_pres.cas_pres
        # next_pres['next_km'] = next_pres.km+next_pres.km_pres
        # next_pres['source'] = PRESUN
        #

        # next_iterace = pd.concat([next_iterace, next_pres])
        # next_iterace = pd.merge(next_iterace, aktivni, left_on='next_stanice', right_index=True,
        #                         suffixes=(None, '_stanicedo'))


        next_iterace['next_body'] = next_iterace.body + next_iterace.points
        next_iterace['app_vykon'] = count_vykon(next_iterace)

        # next_iterace.sort_values(['app_vykon','next_body','next_km'], inplace=True, ascending=[False,False,True])


        is_docile = next_iterace.next_stanice.isin(CILS) & (CIL_OD <= next_iterace.next_cas) & (next_iterace.next_cas <= CIL_DO)

        start = timer()
        # aaa = next_iterace.head(4*MAX_V_ITERACI)
        # bbb = next_iterace.loc[is_docile,next_iterace.columns].head(MAX_V_ITERACI)
        aaa = next_iterace.nlargest(LIMIT_POCET*MAX_V_ITERACI,['app_vykon','next_body'],keep='all')
        end = timer()
        c1 += (end-start)
        start = timer()
        bbb = next_iterace.loc[is_docile,next_iterace.columns].nlargest(MAX_V_ITERACI,['app_vykon','next_body'],keep='all')
        end = timer()
        c2 += (end-start)
        start = timer()
        next_iterace = pd.concat([aaa,bbb])
        end = timer()
        c3 += (end-start)

        start=timer()
        # vyhodime jiz navstivene
        next_iterace = next_iterace.loc[[x[0] not in x[1] for x in zip(next_iterace['next_stanice'], next_iterace['hrany'])],
                                         next_iterace.columns]

        # vyhodime ty, odkud se neda dostat vcas do cile
        next_iterace = next_iterace.loc[next_iterace.next_cas <= next_iterace.timeline,next_iterace.columns]

        # vyhodime ty, ktere jsou po cilovem case (kvůli částečným trasám)
        next_iterace = next_iterace.loc[next_iterace.next_cas <= CIL_DO,next_iterace.columns]

        # vyhodime docasne blokovane
        next_iterace = next_iterace.loc[(next_iterace.next_cas > BLOCK_DO) | (~next_iterace.next_stanice.isin(TEMP_BLOCK)),
                                        next_iterace.columns]

        # vyhodit ty, co nemají dostatečný výkon
        next_iterace = next_iterace.loc[next_iterace.app_vykon >= LIMIT_VYKON,
                                        next_iterace.columns]

        end = timer()
        d += (end-start)

        if len(next_iterace)==0:
            return (pd.DataFrame(),pd.DataFrame())

        start = timer()
        druhyden = next_iterace.next_cas.dt.date > next_iterace.cas.dt.date
        next_iterace['next_inday'] = np.where(druhyden,1,next_iterace.inday+1)
        next_iterace.loc[next_iterace.next_stanice == CIL,'next_inday'] = 0
        next_iterace['next_utecha'] = np.where(druhyden,True,next_iterace.utecha)
        next_iterace['next_kraje'] = np.where(druhyden,
                                              ['0' * (x - 2) + '1' + '0' * (14 - x) if 2 <= x <= 14 else '0'*13 for x in next_iterace.region],
                                              [x[0][:x[1] - 2] + '1' + x[0][x[1] - 1:] if 2 <= x[1] <= 14 else x[0] for x in
                                               zip(next_iterace['kraje'], next_iterace['region'])])
        next_iterace['next_postupka'] = np.where(druhyden,
                                                 ['0' * (x - 2) + '1' + '0' * (7 - x) if 2 <= x <= 7 else '0'*6 for x in
                                                  next_iterace['points']],
                                                 [x[0][:x[1] - 2] + '1' + x[0][x[1] - 1:] if 2 <= x[1] <= 7 else x[0] for x in
                                                  zip(next_iterace['postupka'], next_iterace['points'])])
        next_iterace['next_postupka1'] = next_iterace.next_postupka.str.slice(0, 4) == '1111'
        next_iterace['next_postupka2'] = next_iterace.next_postupka.str.slice(1, 5) == '1111'
        next_iterace['premie_cas'] = 0
        if COUNT_PREMIE:
            next_iterace.loc[next_iterace.next_cas < next_iterace.bonus1, 'premie_cas'] = 1
            next_iterace.loc[next_iterace.next_cas < next_iterace.bonus2, 'premie_cas'] = 2
        next_iterace['premie_inday'] = np.where(next_iterace.next_inday.isin([6, 7, 8, 9]), 1, 0)
        next_iterace['premie_kraje'] = np.where((next_iterace.kraje.str.count('1') == 3) &
                                                (next_iterace.next_kraje.str.count('1') == 4), 2, 0)
        next_iterace['premie_postupka'] = np.select(
            [(next_iterace.postupka1 & ~next_iterace.postupka2 & next_iterace.next_postupka2),
             (~next_iterace.postupka2 & next_iterace.next_postupka2),
             (~next_iterace.postupka1 & next_iterace.next_postupka1)],
            [1, 3, 2], default=0)
        next_iterace['premie_utecha'] = np.where(COUNT_PREMIE & (druhyden | next_iterace.next_stanice==CIL) & next_iterace.utecha, 2, 0)

        next_iterace['next_body'] = next_iterace.body + next_iterace.points + next_iterace.premie_cas + \
                                    next_iterace.premie_inday + next_iterace.premie_kraje + next_iterace.premie_postupka + \
                                    next_iterace.premie_utecha
        next_iterace['next_premie'] = next_iterace.premie + next_iterace.premie_cas + \
                                    next_iterace.premie_inday + next_iterace.premie_kraje + next_iterace.premie_postupka + \
                                    next_iterace.premie_utecha
        end = timer()
        e += (end-start)

        # ------------ Spanek ----------------

        start = timer()
        next_spanek = iterace.loc[~iterace.spanek &
                                  (iterace.cas >= SPANEK_OD) & (iterace.cas <= SPANEK_DO) &
                                  ((iterace.cas.dt.time >= time(hour=20)) | (iterace.cas.dt.time <= time(hour=2))),
                                  iterace.columns]
        if not next_spanek.empty:
            next_spanek['next_stanice'] = next_spanek['stanice']
            next_spanek['timeline'] = next_spanek.stanice.map(chp.timeline)
            next_spanek['next_cas'] = next_spanek.cas+pd.Timedelta(6,'h')
            next_spanek['next_km'] = next_spanek.km
            druhyden = next_spanek.next_cas.dt.date > next_spanek.cas.dt.date
            next_spanek['next_inday'] = np.where(druhyden,
                                                  1,
                                                  next_spanek.inday)
            next_spanek['next_utecha'] = np.where(druhyden,True,next_spanek.utecha)
            next_spanek['next_kraje'] = np.where(druhyden,
                                                  ['0' * 13],
                                                  next_spanek.kraje)
            next_spanek['next_postupka'] = np.where(druhyden,
                                                     ['0' * 6],
                                                     next_spanek.postupka)
            next_spanek['next_postupka1'] = next_spanek.next_postupka.str.slice(0, 4) == '1111'
            next_spanek['next_postupka2'] = next_spanek.next_postupka.str.slice(1, 5) == '1111'
            next_spanek['premie_cas'] = 0
            next_spanek['premie_inday'] = 0
            next_spanek['premie_kraje'] = 0
            next_spanek['premie_postupka'] = 0
            next_spanek['premie_utecha'] = np.where(COUNT_PREMIE & druhyden & next_spanek.utecha, 2, 0)
            next_spanek['next_premie'] = next_spanek['premie'] + next_spanek['premie_utecha']
            next_spanek['next_body'] = next_spanek.body + 5 + next_spanek.premie_utecha
            next_spanek['source'] = SPANEK
            next_spanek['x_odjezd'] = next_spanek['cas']
            next_spanek['conn_time_hrana'] = next_spanek['conn_time']

            next_iterace = pd.concat([next_iterace, next_spanek])
        next_iterace['next_spanek'] = np.where(next_iterace.source == SPANEK,
                                               True,
                                               next_iterace.spanek)
        end = timer()
        f += (end-start)
        start = timer()

        # zbavime se stejnych kombinaci s horsim casem
        next_iterace.sort_values(['next_cas','next_body','next_km'], inplace=True, ascending=[True,False,True])
        next_iterace = next_iterace.drop_duplicates(subset=['visited','next_spanek','next_stanice'],keep='first')
        end = timer()
        g += (end-start)
        start = timer()

        next_iterace['next_visited'] = np.where((next_iterace.source == SPANEK) | (next_iterace.next_stanice == CIL),
                                                next_iterace.visited,
                                                [x[0][:x[1] - 3000] + '1' + x[0][x[1] - 2999:]
                                                 for x in zip(next_iterace['visited'], next_iterace['next_stanice'])])
        end = timer()
        h += (end-start)
        start = timer()

        next_iterace['next_vykon'] = count_vykon(next_iterace)
        end = timer()
        i += (end-start)
        start = timer()

        next_vysledky = next_iterace.loc[next_iterace.next_stanice.isin(CILS) &
                                         (CIL_OD <= next_iterace.next_cas) &
                                         (next_iterace.next_cas <= CIL_DO),
                                         next_iterace.columns]
        next_iterace = next_iterace.loc[next_iterace.next_stanice != CIL,next_iterace.columns]
        next_iterace.sort_values(['next_vykon', 'next_km'], ascending=[False, True], inplace=True)
        next_iterace = next_iterace.head(MAX_V_ITERACI)

        next_vysledky.sort_values(['next_vykon', 'next_km'], ascending=[False, True], inplace=True)
        next_vysledky = next_vysledky.head(MAX_VYSLEDKY)
        end = timer()
        j += (end-start)
        start = timer()

        if not next_iterace.empty:
            next_iterace = count_next_hrany(next_iterace)
        if not next_vysledky.empty:
            next_vysledky = count_next_hrany(next_vysledky)
        end = timer()
        k += (end-start)
        start = timer()

        next_iterace = next_iterace.reindex(['next_stanice','next_cas','next_body','next_km','next_kraje','next_visited',
                                             'next_hrany','next_inday','next_postupka','next_postupka1','next_postupka2',
                                             'next_spanek','next_vykon','next_utecha','conn_time_hrana','next_premie'],axis=1)
        next_iterace.columns = ['stanice','cas','body','km','kraje','visited','hrany','inday','postupka',
                                'postupka1','postupka2','spanek','vykon','utecha','conn_time','premie']
        next_vysledky = next_vysledky.reindex(['next_stanice','next_cas','next_body','next_km','next_kraje','next_visited',
                                             'next_hrany','next_inday','next_postupka','next_postupka1','next_postupka2',
                                             'next_spanek','next_vykon','next_utecha','conn_time_hrana','next_premie'],axis=1)
        next_vysledky.columns = ['stanice','cas','body','km','kraje','visited','hrany','inday','postupka',
                                'postupka1','postupka2','spanek','vykon','utecha','conn_time','premie']
        end = timer()
        l += (end-start)

        return next_iterace, next_vysledky

    def vypocet(self, nemazat):
        vysledky = pd.DataFrame(columns=['stanice','cas','body','km','kraje','visited','hrany','inday','postupka',
                                         'postupka1','postupka2','spanek','vykon','utecha','conn_time','premie'])
        vysledky = vysledky.astype({"postupka1":bool,"postupka2":bool,"spanek":bool,"utecha":bool})

        with open('data2\\bhrany1.pickle', 'rb') as handle:
            hrany = pickle.load(handle)
        with open('data2\\checkpointy_alt.pickle', 'rb') as handle:
            chp = pickle.load(handle)
        with open('data2\\stanice_nazvy.pickle', 'rb') as handle:
            nazvy = pickle.load(handle)

        aktivni = chp[chp.active]
        active_chp = pd.Series(list(set(aktivni.index)-BLOCK), name='next_stanice')
        if not CILS:
            CILS = list(aktivni.index)
        nazvy[IDSPANEK] = 'Spánek'
        hrany = hrany.merge(chp,left_on='point_to_id',right_index=True)
        hrany = hrany.loc[hrany.point_from_id.isin(aktivni.index) & hrany.point_to_id.isin(aktivni.index)]
        hrany = hrany.sort_values(['departure','point_from_id','point_to_id']).set_index('departure',drop=False)
        chp['cas_docile'] = ciltime-chp.timeline

        iterace = pd.DataFrame({'stanice': [START_ID],
                                'cas': [pd.to_datetime(starttime)],
                                'body': [0],
                                'km': [0.0],
                                'kraje': ['0'*13],
                                'visited': ['0'*297],
                                'hrany': [{}],
                                'inday': [0],
                                'postupka': ['0'*6],
                                'postupka1': [False],
                                'postupka2': [False],
                                'spanek': [False],
                                'vykon': [0],
                                'utecha': [True],
                                'conn_time': [chp.at[START_ID,'conn_time']],
                                'premie': [0]
        })
        x = 0

        while len(iterace):
            x += 1
            iterace, new_vysledky = self.doIterace(iterace)
            vysledky = pd.concat([vysledky, new_vysledky])
            vysledky.sort_values(['vykon', 'km'], ascending=[False, True], inplace=True)
            vysledky = vysledky.head(MAX_VYSLEDKY)
            print(len(iterace))

        vysledky.to_pickle('data2\\vysledky.pickle')

        best_result = vysledky.iloc[0]
        for stanice,(prev_stanice, cas, next_cas, premie_cas, premie_inday, premie_kraje, premie_postupka, premie_utecha, body, km, trasa) in best_result.hrany.items():
            print(nazvy[stanice], cas, next_cas, premie_cas, premie_inday, premie_kraje, premie_postupka, premie_utecha, body, round(km,1))