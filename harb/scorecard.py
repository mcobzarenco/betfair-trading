from __future__ import print_function, division

import logging
import datetime
import time
from collections import defaultdict
from itertools import chain, imap, product

import numpy as np
import pandas as pd

from common import pandas_to_dicts
import risk

WARN_LIQUIDITY = 0.2
DEFAULT_COMM = 0.95
LOGGING_NRACES = 500


def get_bet_pnl(amount, odds, selection_won):
    return selection_won * amount * (odds - 1) - (1 - selection_won) * amount


def price_historical_bets(db, bets, train_coll='train'):
    cache = {}
    for bet in bets:
        if 'selection_won' in bet:
            continue
        market_id = bet['market_id']
        if market_id not in cache:
            curr = db[train_coll].find({'market_id': bet['market_id']})
            assert curr.count() == 1
            race = curr.next()
            cache[market_id] = race
        else:
            race = cache[market_id]
        bet['winners'] = race['winners']
        bet['n_runners'] = race['n_runners']
        bet['selection_won'] = int(bet['selection'] in race['winners'])
        bet['pnl'] = get_bet_pnl(bet['amount'], bet['odds'], bet['selection_won'])
    return bets


def flatten_user_data(bets, user_field='data'):
    flattened = []
    for bet in bets:
        bet = bet.copy()
        bet.update(map(lambda x: ('data_' + x[0], x[1]), bet[user_field].iteritems()))
        flattened.append(bet)
    return flattened


def make_scorecard(bets, percentile_width=60, comm=DEFAULT_COMM, jsonify=True, llik_frame=False):
    bets_summary = ['amount', 'pnl', 'odds']
    bets = pd.DataFrame.from_dict(flatten_user_data(bets))
    assert 'pnl' in bets.columns

    user_columns = bets.filter(regex='data_.*').columns.tolist()
    llik = bets.groupby(['market_id', 'selection'])[['selection_won', 'n_runners'] + user_columns].last()
    llik['llik_implied'] = np.log(llik['data_implied'][llik['selection_won'] == 1])
    llik['llik_uniform'] = np.log(1.0 / llik['n_runners'][llik['selection_won'] == 1])
    llik['llik_model'] = np.log(llik['data_p'][llik['selection_won'] == 1])
    llik.fillna(0.0, inplace=True)

    markets = market_breakdown(bets, comm)

    daily_pnl = markets[['scheduled_off', 'pnl_gross', 'pnl_net']]
    daily_pnl['scheduled_off'] = daily_pnl['scheduled_off'].map(lambda t: datetime.datetime(t.year, t.month, t.day))
    daily_pnl = daily_pnl.groupby('scheduled_off').sum().rename(columns={'pnl_gross': 'gross', 'pnl_net': 'net'})
    daily_pnl['gross_cumm'] = daily_pnl['gross'].cumsum()
    daily_pnl['net_cumm'] = daily_pnl['net'].cumsum()

    scorecard = {
        'all': bets[bets_summary].describe(percentile_width),
        'backs': bets[bets['amount'] > 0][bets_summary].describe(percentile_width),
        'lays': bets[bets['amount'] < 0][bets_summary].describe(percentile_width),
        'events': markets.describe(percentile_width),
        'daily_pnl': daily_pnl,
        'llik': {
            'implied': llik['llik_implied'].sum(),
            'uniform': llik['llik_uniform'].sum(),
            'model': llik['llik_model'].sum()
        }
    }

    if jsonify:
        _jsonify_scorecard(scorecard)

    if llik_frame:
        scorecard['_frames'] = {'llik': llik}

    return scorecard


def _jsonify_scorecard(scorecard):
    for col in ['all', 'backs', 'lays', 'events']:
        scorecard[col] = scorecard[col].to_dict()
    scorecard['daily_pnl'] = list(pandas_to_dicts(scorecard['daily_pnl'].reset_index()))


def market_breakdown(bets, comm=DEFAULT_COMM):
    def calculate_collateral(group):
        return np.min(risk.nwin1_bet_returns(group.amount.values, group.odds.values))
    if isinstance(bets, list):
        bets = pd.DataFrame.from_dict(bets)
    events = pd.DataFrame.from_dict([{'market_id': k,
                                      'event': v['event'].iget(0),
                                      'course': v['course'].iget(0),
                                      'country': v['country'].iget(0),
                                      'n_runners': v['n_runners'].iget(0),
                                      'pnl_gross': v.pnl.sum(),
                                      'coll': calculate_collateral(v),
                                      'scheduled_off': v['scheduled_off'].iget(0)}
                                     for k, v in bets.groupby('market_id')]).set_index('market_id')
    events['pnl_net'] = events.pnl_gross
    events['pnl_net'][events.pnl_net > 0] *= comm
    return events



#### OLD STUFF ####


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


