#!/usr/bin/python
from __future__ import division, print_function

import logging
import pymongo

from settings import MONGODB_HOST, MONGODB_PORT, OPERATIONS_DB


class MarketStore(object):
    def __init__(self, client, market_id, quote_feed, trade_feed,
                 db=OPERATIONS_DB, host=MONGODB_HOST, port=MONGODB_PORT):
        assert(market_id == quote_feed.market_id)
        assert(market_id == trade_feed.market_id)

        self._conn = pymongo.connection.Connection(host, port)
        self._db = self._conn[db]
        self._market_id = market_id

        if self._db['markets'].find({'marketId': market_id}).count() == 0:
            logging.info('Inserting static market data for market_id=%s' % market_id)
            self._db['markets'].insert(client.get_market(market_id), safe=True)
        else:
            logging.info('Static data already exists for market_id=%s; Skipped inserting' % market_id)
        quote_feed.subscribe(self.store_quote)
        trade_feed.subscribe(self.store_trade)


    @property
    def market_id(self):
        return self._market_id


    def store_quote(self, timestamp, quotes):
        logging.debug('Inserting quotes for market_id=%s' % self._market_id)
        self._db['quotes'].insert(quotes)


    def store_trade(self, timestamp, trades):
        logging.debug('Inserting trades for market_id=%s' % self._market_id)
        trades['runners'] = dict(map(lambda x: (x[0], {'prices': x[1].index.tolist(), 'amount': x[1].values.tolist()}), trades['runners'].items()))
        self._db['trades'].insert(trades)


if __name__ == '__main__':
    from betfair import api
    from harb.feeds import MasterTimer, QuoteFeed, TradeFeed

    import sys

    market_id = '107514860'

    l = logging.getLogger()
    l.setLevel(logging.DEBUG)
    l.handlers.append(logging.StreamHandler(sys.stdout))

    client = api.API()
    client.login('aristotle137', 'Antiquark_87')

    mt = MasterTimer()
    qf = QuoteFeed(client, market_id)
    tf = TradeFeed(client, market_id)
    MarketStore(client, market_id, qf, tf)
    mt.add_feed(qf, 3)
    mt.add_feed(tf, 3)
    mt.run()