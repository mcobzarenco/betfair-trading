from __future__ import print_function, division

from collections import defaultdict
import logging
import time

import pandas as pd

from common import TO_BE_PLACED
from analytics import HorseModel

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
        assert event_id == self._curr['event_id']

        odds = self.vwao.get_value((event_id, selection), 'vwao')
        win = int(selection in self._curr['winners'])
        pnl = win * amount * (odds - 1) - (1 - win) * amount

        self._bets.append({'event_id' : event_id,
                           'selection': selection,
                           'amount': amount,
                           'odds': odds,
                           'pnl': pnl,
                           'win': self._curr['winners']})


    def handle_race(self, race):
        raise RuntimeError('Abstract base class: implement the function')


    def run(self):
        for race in self.db[self.train_coll].find(sort=[('scheduled_off', 1)]):
            self._curr = race
            self.handle_race(race)


class Jockey(Strategy):
    def __init__(self, db, vwao='vwao', train='train'):
        super(Jockey, self).__init__(db, vwao, train)

        self.hm = HorseModel()


    def handle_race(self, race):
        if race['event'] != TO_BE_PLACED:
            return
        #logging.info('To be placed event (event_id = %d)' % race['event_id'])
        try:
            vwao = self.vwao.ix[race['event_id']]['vwao']
            self.bet(race['event_id'], vwao[vwao == vwao.min()].index[0], 2.0)
        except KeyError:
            logging.warn('No VWAO for %d' % race['event_id'])



    def handle_race2(self, race):
        if race['event'] != TO_BE_PLACED:
            return
        runners = race['selection']
        self.hm.fit_race(race)

#        logging.info('To be placed event (event_id = %d)' % race['event_id'])
#        vwao = self.vwao.ix[race['event_id']]['vwao']
#        self.bet(race['event_id'], vwao[vwao == vwao.min()].index[0], 2.0)


if __name__ == '__main__':
    from pymongo import MongoClient

    db = MongoClient(port=30001)['betfair']
    algo = Jockey(db)

    st = time.clock()
    algo.run()
    en = time.clock()

    print(pd.DataFrame.from_dict(algo._bets).to_string())

    print('Done in %.4f s' % (en - st))
