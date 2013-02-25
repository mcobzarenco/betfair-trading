from __future__ import print_function, division

import datetime
from itertools import ifilter
import logging
import time

import dateutil
import numpy as np

from betfair.api import API
from harb.common import extract_horse_name
from harb.strategy import PricingEngine


USERNAME = 'aristotle137'
PASSWORD = 'Antiquark_87'


class Throtle(object):
    def __init__(self, calls_per_min=20):
        self._secs_between_calls = 60.0 / calls_per_min
        self._last_call = 0.0

    def __call__(self, f, args=None, kwargs=None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        diff = time.time() - self._last_call
        logging.debug('Last call %.2f seconds ago' % diff)
        if diff < self._secs_between_calls:
            logging.debug('Sleeping for %.2f seconds' % (self._secs_between_calls - diff))
            time.sleep(self._secs_between_calls - diff)
        self._last_call = time.time()
        return f(*args, **kwargs)


throtle = Throtle()


class MidPricer(PricingEngine):
    def __init__(self, username=USERNAME, password=PASSWORD):
        self.client = API()
        self.client.login(username, password)
        self._id_to_name = {}
        self._last_id = None

    def price_bet(self, event_id, selection, amount):
        return self.symmetric_prices(event_id)[selection]

    def symmetric_prices(self, event_id):
        event_id = str(event_id)
        if event_id == self._last_id:
            return self._last

        if event_id not in self._id_to_name:
            market = throtle(self.client.get_market, [event_id])
            if isinstance(market, str):
                raise RuntimeError(market)
            self._id_to_name[event_id] = dict(map(lambda x: (x['selection_id'], extract_horse_name(x['name'])),
                                                  market['runners']))

        prices = throtle(self.client.get_market_prices, [event_id])
        if isinstance(prices, str):
            raise RuntimeError(prices)

        mid = {}
        n_runners = len(prices['runners'])
        total = 0.0
        for r in prices['runners']:
            name = self._id_to_name[event_id][r['selection_id']]
            best_back = r['back_prices'][0]['price'] if len(r['back_prices']) > 0 else 1.01
            best_lay = r['lay_prices'][0]['price'] if len(r['lay_prices']) > 0 else 999
            mid[name] = {'event_id': int(event_id),
                         'selection': name,
                         'selection_id': r['selection_id'],
                         'volume_matched': r['total_matched'],
                         'odds': (best_back + best_lay) / 2.0,
                         'uniform': 1.0 / n_runners}
            mid[name]['implied'] = 1.0 / mid[name]['odds']
            total += mid[name]['implied']

        for r in mid.values():
            r['implied'] /= total

        self._last_id = event_id
        self._last = mid
        return mid


def future_markets(menu_prefix='\\Horse Racing\\GB', hours=24):
    client = API()
    client.login(USERNAME, PASSWORD)
    now = datetime.datetime.utcnow()
    before_date = now + datetime.timedelta(hours=hours)

    markets = throtle(client.get_all_markets, kwargs={'hours': 24})
    print('fsddddddddddddddddddsfsdfsdfdsjashdkjsahdkhksahdkajshdkjsa')
    if isinstance(markets, str):
        raise RuntimeError(markets)
    markets = ifilter(lambda x: before_date > x['event_date'] > now and x['menu_path'].startswith(menu_prefix),
                      markets)
    for m in markets:
        detailed = throtle(client.get_market, [m['market_id']])
        if isinstance(detailed, str):
            raise RuntimeError(detailed)
        runners, selection_ids = [], []
        for r in detailed['runners']:
            horse_name = extract_horse_name(r['name'])
            if horse_name is None:
                logging.warning('Skipping market with id=%s as selection="%s" is not a horse name.' %
                                (m['market_id'], r['name']))
                continue
            runners.append(horse_name)
            selection_ids.append(r['selection_id'])
        yield {
            'country': detailed['countryISO3'],
            'course': m['menu_path'].split('\\')[-1],
            'event': m['market_name'],
            'event_id': m['market_id'],
            'scheduled_off': dateutil.parser.parse(detailed['marketTime']).replace(tzinfo=None),
            'n_runners': len(runners),
            'selection': runners
        }
