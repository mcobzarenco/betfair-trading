from __future__ import print_function, division

from collections import defaultdict
import logging

import pandas as pd

WARN_LIQUIDITY = 0.2


class Strategy(object):
    def __init__(self, db, vwao='vwao', train='train'):
        self.vwao_coll = vwao
        self.vwao = pd.DataFrame(list(db[vwao].find(sort=[('scheduled_off', 1)]))) \
                        .set_index(['event_id', 'selection'])
        self.train_coll = train
        self.db = db

        self._bets = []


    def bet(self, event_id, selection, amount):
        odds = self.vwao.ix[(event_id, selection)]['vwao']

        self._bets.append({'event_id' : event_id,
                           'selection': selection,
                           'amount': amount,
                           'odds': odds})



    def handle_race(self, race):
        raise RuntimeError('Abstract base class: implement the function')


    def run(self):
        for race in self.db[self.train_coll].find(sort=[('scheduled_off', 1)]):
            self._curr = race
            self.handle_race(race)
