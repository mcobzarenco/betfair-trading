#!/usr/bin/python
from __future__ import print_function, division

import warnings
warnings.filterwarnings(action='ignore', category=FutureWarning)
warnings.filterwarnings(action='ignore', category=UserWarning)

import re
import logging
import argparse
import datetime

from itertools import islice
from pymongo import MongoClient
from bson import ObjectId

from harb.strategy import Balius, backtest
from harb.common import configure_root_logger
from harb.execution import get_traded_strategies, PaperExecutionService, get_future_markets
from harb.db import BKT_STRATEGIES, PAPER_TRADING, PAPER_BETS


def main(args):
    db = MongoClient(args.host, args.port)[args.db]

    now = datetime.datetime.utcnow()
    markets = list(islice(get_future_markets(hours=args.hours), 0, 1))
    logging.info('Found %d horse races in the next %d hours' % (len(markets), args.hours))
    strats = get_traded_strategies(db[args.paper_trading], True)
    for s in strats:
        strat = Balius.from_dict(db[BKT_STRATEGIES].find_one({'_id': s['strategy_id']}))
        strat.max_expsoure = 1e6
        ex = PaperExecutionService()
        backtest(ex, strat, markets)

        bets = ex.get_mu_bets()[0]
        if len(bets) == 0:
            logging.info('Strategy with id=%s did not place any bets.' % s['strategy_id'])
            continue
        for bet in bets:
            bet['strategy_id'] = s['strategy_id']
            bet['timestamp'] = now
        db[args.paper_bets].insert(bets)
        logging.info('Successfully insert %d bets for strategy with id=%s' % (len(bets), s['strategy_id']))


parser = argparse.ArgumentParser(description='Paper trades horse races')
parser.add_argument('--host', type=str, action='store', default='localhost', help='MongoDB host (default=localhost)')
parser.add_argument('--port', type=int, action='store', default=33000, help='MongoDB port (default=33000)')
parser.add_argument('--db', type=str, action='store', default='betfair', help='db (default=betfair)')
parser.add_argument('--paper-trading', type=str, action='store', default=PAPER_TRADING,
                    help='collection with backtests to paper trade (default=%s)' % PAPER_TRADING)
parser.add_argument('--paper-bets', type=str, action='store', default=PAPER_BETS,
                    help='collection with backtests to paper trade (default=%s)' % PAPER_BETS)
parser.add_argument('--hours', type=int, action='store', default=40,
                    help='for how many hours to look for future races')
parser.add_argument('--logfile', type=str, action='store', default=None, help='specifies what log file to use')
parser.add_argument('--logtty', help='prints logging info to the terminal', action='store_true')
args = parser.parse_args()

configure_root_logger(args.logtty, args.logfile)
main(args)
