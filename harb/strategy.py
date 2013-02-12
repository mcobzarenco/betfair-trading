from __future__ import print_function, division

from collections import defaultdict
import logging
import time

import numpy as np
import pandas as pd

from common import TO_BE_PLACED
from analytics import HorseModel
import risk

WARN_LIQUIDITY = 0.2


class Strategy(object):
    def __init__(self, db, vwao='vwao', train='train'):
        self.vwao_coll = vwao
        self.train_coll = train
        self.db = db

        self._bets = []

    def bet(self, event_id, selection, amount, user_fields=None):
        assert event_id == self._curr['event_id']
        if user_fields is None:
            user_fields = {}

        odds = self.vwao.get_value((event_id, selection), 'vwao')
        win = int(selection in self._curr['winners'])
        pnl = win * amount * (odds - 1) - (1 - win) * amount

        bet = {'event_id' : event_id,
               'selection': selection,
               'amount': amount,
               'odds': odds,
               'pnl': pnl,
               'win': self._curr['winners']}
        bet.update(map(lambda x: ('user_' + x[0], x[1]), user_fields.items()))
        self._bets.append(bet)

    def handle_race(self, race):
        raise RuntimeError('Abstract base class: implement the function')

    def total_matched(self, event_id):
        return self._total_matched.get_value(event_id)

    def run(self, country=None, start_date=None, end_date=None):
        where_clause = defaultdict(lambda: {})
        if start_date is not None:
            where_clause['scheduled_off']['$gte'] = start_date
        if end_date is not None:
            where_clause['scheduled_off']['$lte'] = end_date

        self.vwao = pd.DataFrame(list(db[self.vwao_coll].find(where_clause, sort=[('scheduled_off', 1)])))
        self._total_matched = self.vwao.groupby('event_id')['volume_matched'].sum()
        self.vwao = self.vwao.set_index(['event_id', 'selection'])

        if country is not None:
            where_clause['country'] = country
        races = self.db[self.train_coll].find(where_clause, sort=[('scheduled_off', 1)])
        logging.info('Running strategy on %d historical races [coll=%s, start_date=%s, end_date=%s].' %
                     (races.count(), self.db[self.train_coll], start_date, end_date))

        start_time = time.clock()
        for i, race in enumerate(races):
            self._curr = race
            self.handle_race(race)
            if i > 0 and i % 100 == 0:
                pnl = sum(map(lambda x: x['pnl'] if np.isfinite(x['pnl']) else 0.0, self._bets))
                logging.info('%s races backtested so far [last 100 took %.2fs; n_bets = %d; pnl = %.2f]'
                             % (i, time.clock() - start_time, len(self._bets), pnl))
                start_time = time.clock()


class Jockey(Strategy):
    def __init__(self, db, vwao='vwao', train='train'):
        super(Jockey, self).__init__(db, vwao, train)

        self.hm = HorseModel()

    def handle_race2(self, race):
        if race['event'] != TO_BE_PLACED:
            return
        #logging.info('To be placed event (event_id = %d)' % race['event_id'])
        try:
            vwao = self.vwao.ix[race['event_id']]['vwao']
            self.bet(race['event_id'], vwao[vwao == vwao.min()].index[0], 2.0)
        except KeyError:
            logging.warn('No VWAO for %d' % race['event_id'])

    def handle_race(self, race):
        if race['event'] == TO_BE_PLACED or race['n_runners'] < 3:
            return

        runners = race['selection']
        # self.total_matched(race['event_id']) > 2e5
        if np.all(self.hm.get_runs(runners) > 2):
            vwao = self.vwao.ix[race['event_id']]['vwao'][runners].values
            q = 1.0 / vwao / np.sum(1.0 / vwao)
            p = self.hm.pwin_trapz(runners)

            rel = p / q - 1.0
            t = 0.1

            p[rel < -t] = q[rel < -t] * 0.9
            p[rel > t] = q[rel > t] * 1.1

            #print(p)
            # ps = (self.hm.get_runs(runners) * p + 4 * q) / (4 + self.hm.get_runs(runners))

            #w = RiskModel2(p, q).optimal_w()
            w = risk.nwin1_l2reg(p, q, 0.2)

            logging.info('Placing some bets: %.2f' % np.sum(np.abs(w)))
            [self.bet(race['event_id'], r, w[i], {'p': p[i]}) for i, r in enumerate(runners)]

        self.hm.fit_race(race)

#        logging.info('To be placed event (event_id = %d)' % race['event_id'])
#        vwao = self.vwao.ix[race['event_id']]['vwao']
#        self.bet(race['event_id'], vwao[vwao == vwao.min()].index[0], 2.0)


if __name__ == '__main__':
    import datetime
    from pymongo import MongoClient
    from common import configure_root_logger

    configure_root_logger(True)

    db = MongoClient(port=30001)['betfair']
    algo = Jockey(db)

    st = time.clock()
    algo.run('GB', datetime.datetime(2012, 1, 1), datetime.datetime(2013, 1, 1))
    en = time.clock()

    df = pd.DataFrame.from_dict(algo._bets)
    print(df.to_string())
    print('Done in %.4f s' % (en - st))

    df.save('/home/marius/playground/btrading/back3.pd')

