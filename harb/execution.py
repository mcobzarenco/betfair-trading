from __future__ import print_function, division

import logging
import datetime
import time
from collections import defaultdict
from itertools import chain, imap, product

import dateutil
from pymongo import ASCENDING, DESCENDING
from betfair import API_T

from common import extract_horse_name


USERNAME = 'aristotle137'
PASSWORD = 'Antiquark_87'


class ExecutionService(object):
    def place_exchange_bets(self, market_id, bets):
        raise RuntimeError('Method not implemented - abstract class')

    def get_mu_bets(self, market_id=None, consolidate=True):
        raise RuntimeError('Method not implemented - abstract class')

    def cancel_unmatched(self, market_id, selection_id=None):
        raise RuntimeError('Method not implemented - abstract class')

    def get_market_prices(self, market_id):
        raise RuntimeError('Method not implemented - abstract class')


class VirtualExecutionService(ExecutionService):
    def __init__(self):
        self._matched = []
        self._unmatched = []

    def place_exchange_bets(self, market_id, bets):
        prices = self.get_market_prices(market_id)
        prices = dict(map(lambda x: (x['selection_id'], x), prices))
        for bet in bets:
            price = prices[bet['selection_id']]
            self._matched.append({
                'market_id': market_id,
                'country': price['country'],
                'event': price['event'],
                'course': price['course'],
#               'n_runners': price['n_runners'],
                'scheduled_off': price['scheduled_off'],
                'selection': price['selection'],
                'selection_id': price['selection_id'],
                'amount': bet['amount'],
                'odds': price['last_price_matched'],
                'total_matched': price['total_matched'],
                'data': bet['data'] if 'data' in bet else None
            })

    def get_mu_bets(self, market_id=None, consolidate=True):
        return self._matched, self._unmatched

    def cancel_unmatched(self, market_id, selection_id=None):
        self._unmatched = []

    def get_market_prices(self, market_id):
        raise RuntimeError('Method not implemented - abstract class')


class HistoricalExecutionService(VirtualExecutionService):
    def __init__(self, db, vwao_coll='vwao'):
        super(HistoricalExecutionService, self).__init__()
        self.db = db
        self.vwao_coll = vwao_coll
        self._cache = {}

    def get_market_prices(self, market_id):
        if market_id in self._cache:
            prices = self._cache[market_id]
        else:
            prices = list(self.db[self.vwao_coll].find({'market_id': market_id}))
            self._cache[market_id] = prices
        return prices


class PaperExecutionService(VirtualExecutionService):
    def __init__(self, username=USERNAME, password=PASSWORD):
        super(PaperExecutionService, self).__init__()
        self.c = API_T()
        self.c.login(username, password)
        self._static = {}

    def get_market_prices(self, market_id):
        if market_id not in self._static:
            static = self.c.get_market(market_id)
            self._static[market_id] = static
        else:
            static = self._static[market_id]
        id_to_name = dict(map(lambda x: (x['selection_id'], extract_horse_name(x['name'])), static['runners']))

        raw = self.c.get_market_prices(market_id)
        prices = raw['runners']
        scheduled_off = dateutil.parser.parse(static['marketTime']).replace(tzinfo=None)
        for px in prices:
            px['market_id'] = market_id
            px['country'] = static['countryISO3']
            px['event'] = static['name']
            px['course'] = ''
            px['scheduled_off'] = scheduled_off
            px['selection'] = id_to_name[px['selection_id']]
        return prices


class BetfairExecutionService(ExecutionService):
    pass


def trade_strategy(coll, strategy_id, trade_switch):
    curr = coll.find({'strategy_id': strategy_id}).sort([('timestamp', -1)])
    count = curr.count()
    last_trade_switch = curr.next()['trade_switch'] if count > 0 else (not trade_switch)
    if trade_switch == last_trade_switch or (not trade_switch and count == 0):
        if trade_switch:
            msg = 'Strategy id="%s" is already being traded (coll=%s). Ignoring start signal' % (str(strategy_id), coll)
            logging.error(msg)
        else:
            msg = 'Strategy id="%s" is not currently being traded (coll=%s). Ignoring stop signal' % (str(strategy_id), coll)
            logging.error(msg)
        return {'success': False, 'msg': msg}
    else:
        logging.info('Setting trade switch to %s for strategy with id="%s" (coll=%s)' %
                     (trade_switch, str(strategy_id), coll))
        coll.insert({
            'strategy_id': strategy_id,
            'timestamp': datetime.datetime.utcnow(),
            'trade_switch': trade_switch
        })
        return {'success': True}


def get_traded_strategies(coll, currently_trading=False):
    strats = coll.distinct('strategy_id')
    summary = []
    for strat in strats:
        start = coll.find_one({'strategy_id': strat}, sort=[('timestamp', ASCENDING)])
        end = coll.find_one({'strategy_id': strat}, sort=[('timestamp', DESCENDING)])
        last_traded = end['timestamp'] if not end['trade_switch'] else None
        assert start['trade_switch']
        if not currently_trading or last_traded is None:
            summary.append({'strategy_id': strat,
                            'first_traded': start['timestamp'],
                            'last_traded': last_traded})
    return summary
