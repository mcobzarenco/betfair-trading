#!/usr/bin/python
from __future__ import division, print_function

import datetime
import sched
import time

import pandas as pd
import pymongo
from betfair import api

import settings


dt = datetime.datetime


class MasterTimer(object):
    def __init__(self):
        self._sched = sched.scheduler(time.time, time.sleep)
        self._feeds = []

    def add_feed(self, feed, seconds, priority=1):
        def timed_feed():
            feed.post_to_all()
            self._sched.enter(seconds, priority, timed_feed, ())
        self._feeds.append(timed_feed)

    def run(self):
        map(lambda f: f(), self._feeds)
        self._sched.run()


#####  Feeds  ######

class Feed(object):
    def __init__(self, client, subscribers=[]):
        self._client = client
        self.subscribers = subscribers


    def subscribe(self, subscriber):
        self.subscribers.append(subscriber)


    def unsubscribe(self, subscriber):
        self.subscribers.remove(subscriber)


class QuoteFeed(Feed):
    def __init__(self, client, market_id, subscribers=[]):
        super(QuoteFeed, self).__init__(client, subscribers)
        self._market_id = market_id


    @property
    def market_id(self):
        return self._market_id


    def post_to_all(self):
        client = self._client
        quotes = client.get_market_prices(market_id=self._market_id)
        quotes['timestamp'] = client.API_TIMESTAMP
        for sub in self.subscribers:
            sub(client.API_TIMESTAMP, quotes)


class TradeFeed(Feed):
    def __init__(self, client, market_id, subscribers=[]):
        super(TradeFeed, self).__init__(client, subscribers)
        self._market_id = market_id
        self._last = self.get_traded_volume()


    @property
    def market_id(self):
        return self._market_id


    def get_traded_volume(self):
        tv = self._client.get_market_traded_volume(self._market_id)
        if isinstance(tv, str):
            return None
        return dict(map(lambda x: (x['selection_id'], pd.DataFrame(x['volumes']).set_index('price').amount), tv))


    def post_to_all(self):
        curr = self.get_traded_volume()
        trades = {}
        for sel_id, vol in self._last.items():
            sel_trades = (curr[sel_id] - vol)
            sel_trades = sel_trades[sel_trades >= 2]
            trades[sel_id] = sel_trades
        self._last = curr

        trades = {'timestamp': self._client.API_TIMESTAMP,
                  'runners': trades}

        for sub in self.subscribers:
            sub(self._client.API_TIMESTAMP, trades)




# class VQuoteFeed(Feed):
#     def __init__(self):
#         self.subscribers = []


#     def subscribe(self, subscriber):
#         self.subscribers.append(subscriber)


#     def post_to_all(self):
#         for sub in self.subscribers:
#             sub.post(self._timestamp, self._cur_vquotes)


#     def post(self, timestamp, quotes):
#         quotes['market_id'] = '123456789'
#         self._cur_vquotes = quotes
#         self._timestamp = timestamp
#         self.post_to_all()

class HistoricalFeed(Feed):
    pass


class Subscriber(object):
    def post(self, timestamp, data):
        raise NotImplementedError('Subscriber is an abstract class')


class PrintSubscriber(Subscriber):
    def post(self, timestamp, data):
        print('timestamp=%s; data=%s' % (timestamp, data))





# mt = MasterTimer()

# client = api.API()
# client.login('aristotle137', 'Antiquark_87')


# qt = QuoteFeed(client, '105629371', subscribers=[PrintTimestamp()])

# mt.add_feed(qt, 5)
# mt.run()
