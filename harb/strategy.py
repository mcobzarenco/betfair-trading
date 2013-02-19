from __future__ import print_function, division

from collections import defaultdict
import logging
import datetime
import time

import numpy as np
import pandas as pd

from common import TO_BE_PLACED, pandas_to_dicts
from analytics import HorseModel, DEFAULT_MU, DEFAULT_SIGMA, DEFAULT_BETA, DEFAULT_TAU, DEFAULT_DRAW
import risk

WARN_LIQUIDITY = 0.2
DEFAULT_COMM = 0.95


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

        bet = {'event_id': event_id,
               'scheduled_off': self._curr['scheduled_off'],
               'selection': selection,
               'amount': amount,
               'odds': odds,
               'pnl': pnl,
               'selection_won': win,
               'winners': self._curr['winners']}
        bet.update(map(lambda x: ('u_' + x[0], x[1]), user_fields.items()))
        self._bets.append(bet)

    def handle_race(self, race):
        raise RuntimeError('Abstract base class: implement the function')

    def run(self, country=None, start_date=None, end_date=None):
        where_clause = defaultdict(lambda: {})
        if start_date is not None:
            where_clause['scheduled_off']['$gte'] = start_date
        if end_date is not None:
            where_clause['scheduled_off']['$lte'] = end_date

        self.vwao = pd.DataFrame(list(self.db[self.vwao_coll].find(where_clause, sort=[('scheduled_off', 1)])))
        self._total_matched = self.vwao.groupby('event_id')['volume_matched'].sum()
        self.vwao = self.vwao.set_index(['event_id', 'selection'])

        # Calculate the probabilities implied by the odds and a uniform distribution
        self.vwao['implied'] = self.vwao.groupby(level=0)['vwao'].transform(lambda x: (1.0 / x) / (1.0 / x).sum())
        self.vwao['uniform'] = self.vwao.groupby(level=0)['vwao'].transform(lambda x: 1.0 / len(x))

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

    def get_total_matched(self, event_id):
        return self._total_matched.get_value(event_id)

    def get_bets(self):
        return self._bets

    @staticmethod
    def _jsonify_scorecard(scorecard):
        for col in ['all', 'backs', 'lays', 'events']:
            scorecard[col] = scorecard[col].to_dict()
        scorecard['daily_pnl'] = list(pandas_to_dicts(scorecard['daily_pnl'].reset_index()))

    def make_scorecard(self, percentile_width=60, comm=DEFAULT_COMM, jsonify=True, llik_frame=False):
        def calculate_collateral(group):
            return np.min(risk.nwin1_bet_returns(group.amount.values, group.odds.values))

        bets_summary = ['amount', 'pnl', 'odds']
        bets = pd.DataFrame.from_dict(self.get_bets())

        user_columns = bets.filter(regex='u_.*').columns.tolist()
        llik = bets.groupby(['event_id', 'selection'])[['selection_won'] + user_columns].last() \
            .join(self.vwao[['implied', 'uniform']])
        llik['llik_implied'] = np.log(llik['implied'][llik['selection_won'] == 1])
        llik['llik_implied'].fillna(0.0, inplace=True)
        llik['llik_uniform'] = np.log(llik['uniform'][llik['selection_won'] == 1])
        llik['llik_uniform'].fillna(0.0, inplace=True)

        events = pd.DataFrame.from_dict([{'event_id': k,
                                          'pnl_gross': v.pnl.sum(),
                                          'coll': calculate_collateral(v),
                                          'scheduled_off': v['scheduled_off'].iget(0)}
                                        for k, v in bets.groupby('event_id')]).set_index('event_id')
        events['pnl_net'] = events.pnl_gross
        events['pnl_net'][events.pnl_net > 0] *= comm

        daily_pnl = events[['scheduled_off', 'pnl_gross', 'pnl_net']]
        daily_pnl['scheduled_off'] = daily_pnl['scheduled_off'].map(lambda t: datetime.datetime(t.year, t.month, t.day))
        daily_pnl = daily_pnl.groupby('scheduled_off').sum().rename(columns={'pnl_gross': 'gross', 'pnl_net': 'net'})
        daily_pnl['gross_cumm'] = daily_pnl['gross'].cumsum()
        daily_pnl['net_cumm'] = daily_pnl['net'].cumsum()

        scorecard = {
            'all': bets[bets_summary].describe(percentile_width),
            'backs': bets[bets['amount'] > 0][bets_summary].describe(percentile_width),
            'lays': bets[bets['amount'] < 0][bets_summary].describe(percentile_width),
            'events': events.describe(percentile_width),
            'daily_pnl': daily_pnl,
            'llik': {
                'implied': llik['llik_implied'].sum(),
                'uniform': llik['llik_uniform'].sum()
            }
        }

        if jsonify:
            Strategy._jsonify_scorecard(scorecard)

        if llik_frame:
            scorecard['_frames'] = {'llik': llik}

        return scorecard


class Balius(Strategy):
    def __init__(self, db, vwao='vwao', train='train',
                 mu=DEFAULT_MU, sigma=DEFAULT_SIGMA, beta=DEFAULT_BETA, tau=DEFAULT_TAU, draw_probability=DEFAULT_DRAW,
                 risk_aversion=0.1, min_races=3, max_exposure=50):
        super(Balius, self).__init__(db, vwao, train)
        self.hm = HorseModel(mu=mu, sigma=sigma, beta=beta, tau=tau, draw_probability=draw_probability)
        self.risk_aversion = risk_aversion
        self.min_races = min_races
        self.max_expsoure = max_exposure

    def make_scorecard(self, percentile_width=60, comm=DEFAULT_COMM, jsonify=True, llik_frame=False):
        scorecard = super(Balius, self).make_scorecard(percentile_width, comm, jsonify, True)
        llik = scorecard['_frames']['llik']

        llik['llik_model'] = np.log(llik['u_p'][llik['selection_won'] == 1])
        llik['llik_model'].fillna(0.0, inplace=True)
        scorecard['llik']['model'] = llik['llik_model'].sum()
        scorecard['params'] = {
            'ts': self.hm.get_params(),
            'risk': {
                'risk_aversion': self.risk_aversion,
                'min_races': self.min_races,
                'max_exposure': self.max_expsoure
            }
        }

        if not llik_frame:
            del scorecard['_frames']
        return scorecard

    def handle_race(self, race):
        if race['event'] == TO_BE_PLACED or race['n_runners'] < 3:
            return

        runners = race['selection']
        # self.total_matched(race['event_id']) > 2e5
        if np.all(self.hm.get_runs(runners) >= self.min_races):
            vwao = self.vwao.ix[race['event_id']]['vwao'][runners].values
            implied = self.vwao.ix[race['event_id']]['implied'][runners].values
            p = self.hm.pwin_trapz(runners)

            rel = p / implied - 1.0
            t = 0.1

            p[rel < -t] = implied[rel < -t] * 0.9
            p[rel > t] = implied[rel > t] * 1.1

            #print(p)
            # ps = (self.hm.get_runs(runners) * p + 4 * q) / (4 + self.hm.get_runs(runners))

            #w = RiskModel2(p, q).optimal_w()
            w = risk.nwin1_l2reg(p, vwao, self.risk_aversion)

            returns = risk.nwin1_bet_returns(w, vwao)
            #ix = np.where(returns < -self.max_expsoure)[0]
            if np.any(returns <= -self.max_expsoure):
                logging.warning('Maximum exposure limit of %.2f reached!' % self.max_expsoure)
                logging.warning('Ignoring bets w=%s runners=%s with potential returns=%s'
                                % (w.tolist(), runners, returns.tolist()))
            else:
                logging.info('Betting on event_id=%d: |exposure|=%.2f collateral=%.2f' %
                             (race['event_id'], np.sum(np.abs(w)), np.min(returns)))
                for i, r in enumerate(runners):
                    if np.abs(w[i]) > 0.01:
                        self.bet(race['event_id'], r, w[i], {'p': p[i], 'odds': 1.0 / p[i]})

        self.hm.fit_race(race)