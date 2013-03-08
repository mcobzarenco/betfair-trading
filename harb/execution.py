from __future__ import print_function, division

import logging
import datetime
import time
from collections import defaultdict
from itertools import chain, imap, product

import numpy as np
import pandas as pd


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


class ExecutionEngine(object):
    def place_exchange_bets(self, market_id, bets):
        raise RuntimeError('Method not implemented - abstract class')

    def get_mu_bets(self, market_id=None, consolidate=True):
        raise RuntimeError('Method not implemented - abstract class')

    def cancel_unmatched(self, market_id, selection_id=None):
        raise RuntimeError('Method not implemented - abstract class')


class HistoricalExecutionEngine(ExecutionEngine):
    def __init__(self, historical_data_provider):
        super(HistoricalExecutionEngine, self).__init__()
        self._provider = historical_data_provider
        self._matched = []
        self._unmatched = []

    def place_exchange_bets(self, market_id, bets):
        prices = self._provider.get_market_prices(market_id)
        prices = dict(map(lambda x: (x['selection_id'], x), prices))
        for bet in bets:
            price = prices[bet['selection_id']]
            self._matched.append({
                'market_id': market_id,
                'country': price['country'],
                'event': price['event'],
                'course': price['course'],
                'n_runners': price['n_runners'],
                'scheduled_off': price['scheduled_off'],
                'selection': price['selection_id'],
                'selection_id': price['selection_id'],
                'amount': bet['amount'],
                'odds': price['last_price_matched'],
                'total_matched': price['total_matched']
            })

    def get_mu_bets(self, market_id=None, consolidate=True):
        return self._matched, self._unmatched

    def cancel_unmatched(self, market_id, selection_id=None):
        self._unmatched = []


class PaperExecutionEngine(object):
    pass


class BetfairExecutionEngine(object):
    pass


class MarketDataProvider(object):
    def get_market_prices(self, market_id):
        raise RuntimeError('Method not implemented - abstract class')


class HistoricalDataProvider(MarketDataProvider):
    def __init__(self, db, vwao_coll='vwao'):
        super(HistoricalDataProvider, self).__init__()
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



class BetfairDataProvider(MarketDataProvider):
    pass
