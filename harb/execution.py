from __future__ import print_function, division

import logging
import datetime
import time
from collections import defaultdict
from itertools import chain, imap, product

import numpy as np
import pandas as pd


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


class HistoricalExecutionService(ExecutionService):
    def __init__(self, db, vwao_coll='vwao'):
        self.db = db
        self.vwao_coll = vwao_coll
        self._cache = {}
        self._matched = []
        self._unmatched = []

    def get_market_prices(self, market_id):
        if market_id in self._cache:
            prices = self._cache[market_id]
        else:
            prices = list(self.db[self.vwao_coll].find({'market_id': market_id}))
            self._cache[market_id] = prices
        return prices

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
#                'n_runners': price['n_runners'],
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


class PaperExecutionService(ExecutionService):
    pass


class BetfairExecutionEngine(ExecutionService):
    pass
