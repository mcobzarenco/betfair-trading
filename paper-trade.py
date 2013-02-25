#!/usr/bin/python
from __future__ import print_function, division

import warnings
warnings.filterwarnings(action='ignore', category=FutureWarning)
warnings.filterwarnings(action='ignore', category=UserWarning)

import re
import logging
import argparse

import dateutil
import numpy as np
import pandas as pd
from pymongo import MongoClient
from bson import ObjectId


from harb.paper import future_markets, MidPricer
from harb.strategy import Balius
from harb.common import configure_root_logger
from backtest import STRATEGIES_COLL


def main(args):
    db = MongoClient(args.host, args.port)[args.db]

    markets = list(future_markets(hours=args.hours))
    logging.info('Found %d horse races in the next %d hours' % (len(markets), args.hours))
    paper_strats = db[args.paper].find()
    for s in paper_strats:
        strat = Balius.from_dict(MidPricer(), db[STRATEGIES_COLL].find_one({'_id': s['strategy_id']}))
        strat.max_expsoure = 1e6
        strat.run(markets)


parser = argparse.ArgumentParser(description='Paper trades horse races')
parser.add_argument('--host', type=str, action='store', default='localhost', help='MongoDB host (default=localhost)')
parser.add_argument('--port', type=int, action='store', default=33000, help='MongoDB port (default=33000)')
parser.add_argument('--db', type=str, action='store', default='betfair', help='db (default=betfair)')
parser.add_argument('--paper', type=str, action='store', default='races',
                    help='collection with backtests to paper trade (default=paper)')
parser.add_argument('--hours', type=int, action='store', default=18,
                    help='for how many hours to look for future races')
parser.add_argument('--logfile', type=str, action='store', default=None, help='specifies what log file to use')
parser.add_argument('--logtty', help='prints logging info to the terminal', action='store_true')
args = parser.parse_args()

configure_root_logger(args.logtty, args.logfile)

main(args)