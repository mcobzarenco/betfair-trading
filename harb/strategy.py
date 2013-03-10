from __future__ import print_function, division

import logging
import datetime
import time
from collections import defaultdict
from itertools import chain, imap, product

import numpy as np
import pandas as pd

from common import TO_BE_PLACED, pandas_to_dicts
from analytics import HorseModel, DEFAULT_MU, DEFAULT_SIGMA, DEFAULT_BETA, DEFAULT_TAU, DEFAULT_DRAW, \
    get_implied_from_odds
import risk


WARN_LIQUIDITY = 0.2
DEFAULT_COMM = 0.95
LOGGING_NRACES = 500


def backtest(exec_services, strategy, sorted_races):
    start_time = time.clock()
    for i, race in enumerate(sorted_races):
        strategy.handle_race(exec_services, race)
        if i > 0 and i % LOGGING_NRACES == 0:
            #pnl = sum(map(lambda x: x['pnl'] if np.isfinite(x['pnl']) else 0.0, self._bets))
            #logging.info('%d races backtested so far [last %d took %.2fs; n_bets = %d; pnl = %.2f]'
            #             % (i, LOGGING_NRACES, time.clock() - start_time, len(self._bets), pnl))
            logging.info('%d races backtested so far [last %d took %.2fs]' %
                         (i, LOGGING_NRACES, time.clock() - start_time))
            start_time = time.clock()


class Balius(object):
    def __init__(self, horse_model=None, mu=DEFAULT_MU, sigma=DEFAULT_SIGMA, beta=DEFAULT_BETA,
                 tau=DEFAULT_TAU, draw_probability=DEFAULT_DRAW, risk_aversion=0.1, min_races=3, max_exposure=50):
        if horse_model is None:
            logging.debug('Balius created from scratch: mu=%.2f sigma=%.2f beta=%.2f tau=%.2f draw_prob=%.2f '
                          'risk_aversion=%.2f min_races=%d max_exposure=%.2f' %
                          (mu, sigma, beta, tau, draw_probability, risk_aversion, min_races, max_exposure))
            self.hm = HorseModel(mu=mu, sigma=sigma, beta=beta, tau=tau, draw_probability=draw_probability)
        else:
            logging.debug('Balius created from horse model: ts=%s risk_aversion=%.2f min_races=%d max_exposure=%.2f' %
                          (str(horse_model._ts), risk_aversion, min_races, max_exposure))
            self.hm = horse_model
        self.risk_aversion = risk_aversion
        self.min_races = min_races
        self.max_expsoure = max_exposure

    def handle_race(self, ex, race):
        if race['event'] == TO_BE_PLACED or race['n_runners'] < 3:
            return

        runners = race['selection']
        if np.all(self.hm.get_runs(runners) >= self.min_races):
            prices = ex.get_market_prices(race['market_id'])
            prices = dict(map(lambda x: (x['selection'], x), prices))
            odds = np.array(map(lambda r: prices[r]['back_prices'][0]['price'], runners))
            implied = get_implied_from_odds(odds)
            p = self.hm.pwin_trapz(runners)

            rel = p / implied - 1.0
            t = 0.05

            p[rel < -t] = implied[rel < -t] * 0.95
            p[rel > t] = implied[rel > t] * 1.05

            w = risk.nwin1_l2reg(p, odds, self.risk_aversion)

            returns = risk.nwin1_bet_returns(w, odds)
            if np.any(returns <= -self.max_expsoure):
                logging.warning('Maximum exposure limit of %.2f reached!' % self.max_expsoure)
                logging.warning('Ignoring bets w=%s runners=%s with potential returns=%s'
                                % (w.tolist(), runners, returns.tolist()))
            else:
                logging.info('Betting on market_id=%s: |exposure|=%.2f collateral=%.2f' %
                             (race['market_id'], np.sum(np.abs(w)), np.min(returns)))
                bets = ({'selection_id': prices[r]['selection_id'],
                         'amount': w[i],
                         'data': {
                             'p': p[i],
                             'implied': implied[i]
                         }
                        } for i, r in enumerate(runners))
                ex.place_exchange_bets(race['market_id'], bets)

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
    def from_dict(cls, strat):
        hm = HorseModel.from_dict(strat['hm'])
        return cls(horse_model=hm, **strat['risk'])
