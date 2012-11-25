from __future__ import division, print_function

import datetime
import sched
import time

import pymongo

import settings
from feeds import Subscriber


class MarketStore(object):
    def __init__(self, client, quote_feed, trade_feed):
        self._client = client
        self._qfeed = quote_feed
        self._tfreed = trade_feed


class QuotesStore(Subscriber):
    def __init__(self):
        self.conn = pymongo.connection.Connection(settings.MONGODB_HOST, settings.MONGODB_PORT)


    def post(self, timestamp, quotes):
        quotes['timestamp'] = timestamp
        print('Inserting into DB @ %s' % timestamp)
        self.conn['betfair']['quotes'].insert(quotes)
