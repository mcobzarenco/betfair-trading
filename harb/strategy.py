from __future__ import print_function, division

import logging
import datetime
import time
from collections import defaultdict
from itertools import chain, imap, product

import numpy as np
import pandas as pd

from common import TO_BE_PLACED, pandas_to_dicts
from analytics import HorseModel, DEFAULT_MU, DEFAULT_SIGMA, DEFAULT_BETA, DEFAULT_TAU, DEFAULT_DRAW
import risk

WARN_LIQUIDITY = 0.2
DEFAULT_COMM = 0.95
LOGGING_NRACES = 500


class Strategy(object):
    def __init__(self, px_engine):
        self.px_engine = px_engine
        self._bets = []

    def bet(self, event_id, selection, amount, user_fields=None):
        assert event_id == self._curr['event_id']
        if user_fields is None:
            user_fields = {}

        price = self.px_engine.price_bet(event_id, selection, amount)
        matched_odds = price['odds']
        if 'winners' in self._curr:
            win = int(selection in self._curr['winners'])
            pnl = win * amount * (matched_odds - 1) - (1 - win) * amount
        else:
            win = -1
            pnl = 0

        bet = {'event_id': event_id,
               'country': self._curr['country'],
               'event': self._curr['event'],
               'course': self._curr['course'],
               'n_runners': self._curr['n_runners'],
               'scheduled_off': self._curr['scheduled_off'],
               'selection': selection,
               'amount': amount,
               'odds': matched_odds,
               'volume_matched': price['volume_matched'],
               'pnl': pnl,
               'selection_won': win,
               'winners': self._curr['winners'] if 'winners' in self._curr else []}
        bet.update(map(lambda x: ('u_' + x[0], x[1]), user_fields.items()))
        self._bets.append(bet)

    def get_bets(self):
        return self._bets

    def run(self, sorted_races):
        start_time = time.clock()
        for i, race in enumerate(sorted_races):
            self._curr = race
            self.handle_race(race)
            if i > 0 and i % LOGGING_NRACES == 0:
                pnl = sum(map(lambda x: x['pnl'] if np.isfinite(x['pnl']) else 0.0, self._bets))
                logging.info('%s races backtested so far [last %d took %.2fs; n_bets = %d; pnl = %.2f]'
                             % (i, LOGGING_NRACES, time.clock() - start_time, len(self._bets), pnl))
                start_time = time.clock()

    @staticmethod
    def _jsonify_scorecard(scorecard):
        for col in ['all', 'backs', 'lays', 'events']:
            scorecard[col] = scorecard[col].to_dict()
        scorecard['daily_pnl'] = list(pandas_to_dicts(scorecard['daily_pnl'].reset_index()))

    def event_breakdown(self, comm=DEFAULT_COMM, bets_dataframe=None):
        def calculate_collateral(group):
            return np.min(risk.nwin1_bet_returns(group.amount.values, group.vwao.values))
        bets = pd.DataFrame.from_dict(self.get_bets()) if bets_dataframe is None else bets_dataframe
        events = pd.DataFrame.from_dict([{'event_id': k,
                                          'event': v['event'].iget(0),
                                          'course': v['course'].iget(0),
                                          'country': v['country'].iget(0),
                                          'n_runners': v['n_runners'].iget(0),
                                          'pnl_gross': v.pnl.sum(),
                                          'coll': calculate_collateral(v),
                                          'scheduled_off': v['scheduled_off'].iget(0)}
                                         for k, v in bets.groupby('event_id')]).set_index('event_id')
        events['pnl_net'] = events.pnl_gross
        events['pnl_net'][events.pnl_net > 0] *= comm
        return events

    def make_scorecard(self, percentile_width=60, comm=DEFAULT_COMM, jsonify=True, llik_frame=False):
        bets_summary = ['amount', 'pnl', 'odds']
        bets = pd.DataFrame.from_dict(self.get_bets())

        user_columns = bets.filter(regex='u_.*').columns.tolist()
        llik = bets.groupby(['event_id', 'selection'])[['selection_won'] + user_columns].last() \
            .join(self.px_engine.vwao_as_dataframe()[['implied', 'uniform']])
        llik['llik_implied'] = np.log(llik['implied'][llik['selection_won'] == 1])
        llik['llik_implied'].fillna(0.0, inplace=True)
        llik['llik_uniform'] = np.log(llik['uniform'][llik['selection_won'] == 1])
        llik['llik_uniform'].fillna(0.0, inplace=True)

        events = self.event_breakdown(comm, bets)

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

    def handle_race(self, race):
        raise RuntimeError('Abstract base class: implement the function')


class PricingEngine(object):
    def price_bet(self, event_id, selection, amount):
        raise NotImplementedError()

    def symmetric_prices(self, event_id):
        raise NotImplementedError()


class VWAOPricer(PricingEngine):
    def __init__(self, db, vwao_coll):
        self.db = db
        self.vwao_coll = vwao_coll
        self._vwao = defaultdict(lambda: {})

    def price_bet(self, event_id, selection, amount):
        vwao = self.symmetric_prices(event_id)[selection]
        vwao['odds'] = vwao['vwao']
        return vwao

    def symmetric_prices(self, event_id):
        if event_id not in self._vwao:
            vwao = self._vwao[event_id]
            cursor = self.db[self.vwao_coll].find({'event_id': event_id})
            n_runners = cursor.count()
            implied_sum = 0.0
            for sel in cursor:
                sel['odds'] = sel['vwao']
                sel['uniform'] = 1.0 / n_runners
                sel['implied'] = 1.0 / sel['vwao']
                implied_sum += sel['implied']
                vwao[sel['selection']] = sel
            for sel in vwao.values():
                sel['implied'] /= implied_sum
        else:
            vwao = self._vwao[event_id]

        return vwao

    def vwao_as_dataframe(self):
        index = list(chain(*imap(lambda x: product([x[0]], x[1].keys()), self._vwao.iteritems())))
        values = list(chain(*imap(lambda x: x[1].values(), self._vwao.iteritems())))
        vwao = pd.DataFrame.from_dict(values)
        vwao.index = pd.MultiIndex.from_tuples(index)
        return vwao


class Balius(Strategy):
    def __init__(self, px_engine, horse_model=None, mu=DEFAULT_MU, sigma=DEFAULT_SIGMA, beta=DEFAULT_BETA,
                 tau=DEFAULT_TAU, draw_probability=DEFAULT_DRAW, risk_aversion=0.1, min_races=3, max_exposure=50):
        super(Balius, self).__init__(px_engine)
        logging.debug('Balius params: mu=%.2f sigma=%.2f beta=%.2f tau=%.2f draw_prob=%.2f '
                      'risk_aversion=%.2f min_races=%d max_exposure=%.2f' %
                      (mu, sigma, beta, tau, draw_probability, risk_aversion, min_races, max_exposure))
        if horse_model is None:
            self.hm = HorseModel(mu=mu, sigma=sigma, beta=beta, tau=tau, draw_probability=draw_probability)
        else:
            self.hm = horse_model
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
            vwao_dict = self.px_engine.symmetric_prices(race['event_id'])
            vwao = np.array(map(lambda r: vwao_dict[r]['odds'], runners))
            implied = np.array(map(lambda r: vwao_dict[r]['implied'], runners))
            p = self.hm.pwin_trapz(runners)

            rel = p / implied - 1.0
            t = 0.1

            p[rel < -t] = implied[rel < -t] * 0.8
            p[rel > t] = implied[rel > t] * 1.2

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
                logging.info('Betting on event_id=%s: |exposure|=%.2f collateral=%.2f' %
                             (str(race['event_id']), np.sum(np.abs(w)), np.min(returns)))
                for i, r in enumerate(runners):
                    #if np.abs(w[i]) > 0.01 and vwao[i] < 50.0:
                    self.bet(race['event_id'], r, w[i], {'p': p[i], 'odds': 1.0 / p[i]})

        if 'ranking' in race:
            self.hm.fit_race(race)

    def to_dict(self):
        return {
            'hm': self.hm.to_dict(),
            'risk': {
                'risk_aversion': self.risk_aversion,
                'min_races': self.min_races,
                'max_exposure': self.max_expsoure
            }
        }

    @classmethod
    def from_dict(cls, px_engine, strat):
        hm = HorseModel.from_dict(strat['hm'])
        return cls(px_engine=px_engine, horse_model=hm, **strat['risk'])