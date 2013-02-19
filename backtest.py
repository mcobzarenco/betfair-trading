#!/usr/bin/python
from __future__ import print_function, division

import datetime
import logging
import time
import argparse
import warnings
warnings.filterwarnings(action='ignore', category=FutureWarning)
warnings.filterwarnings(action='ignore', category=UserWarning)

import dateutil
import numpy as np
import pandas as pd
from pymongo import MongoClient

from harb.analytics import DEFAULT_MU, DEFAULT_SIGMA, DEFAULT_BETA, DEFAULT_TAU, DEFAULT_DRAW
from harb.strategy import Balius
from harb.common import configure_root_logger, convert_types, pandas_to_dicts


def parse_date(d):
    return dateutil.parser.parse(d, dayfirst=True) if d is not None else None


def run_backtest(args):
    db = MongoClient(args.host, args.port)[args.db]
    strat = Balius(db, args.vwao, args.train,
                   mu=args.mu, sigma=args.sigma, beta=args.beta, tau=args.tau, draw_probability=args.draw_prob,
                   risk_aversion=args.risk_aversion, min_races=args.min_races, max_exposure=args.max_exposure)
    st = time.clock()
    strat.run('GB', parse_date(args.start), parse_date(args.end))
    en = time.clock()
    logging.info('Backtest finished in %.2f seconds' % (en - st))

    scorecard = strat.make_scorecard()
    now = datetime.datetime.utcnow()
    scorecard['timestamp'] = now
    scorecard['run_seconds'] = en - st
    scorecard_id = db['scorecards'].insert(scorecard)
    logging.info('Scorecard inserted in the database with id=%s' % scorecard_id)

    db['bets'].insert({'bets': strat.get_bets(),
                       'timestamp': now,
                       'scorecard_id': scorecard_id})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Runs a backtest against Betfair historical data')
    parser.add_argument('--host', type=str, action='store', default='localhost', help='MongoDB host (default=localhost)')
    parser.add_argument('--port', type=int, action='store', default=33000, help='MongoDB port (default=33000)')
    parser.add_argument('--db', type=str, action='store', default='betfair', help='db (default=betfair)')
    parser.add_argument('--jobs', type=int, action='store', default=-1, help='how many jobs to use')
    parser.add_argument('--vwao', type=str, action='store', default='vwao',
                        help='volume-weighted-average-odds (vwao) collection (default=vwao)')
    parser.add_argument('--start', type=str, action='store', default=None, help='start date')
    parser.add_argument('--end', type=str, action='store', default=None, help='end date')
    parser.add_argument('--mu', type=float, action='store', default=DEFAULT_MU, help='mu (default=%.2f)' % DEFAULT_MU)
    parser.add_argument('--sigma', type=float, action='store', default=DEFAULT_SIGMA,
                        help='sigma (default=%.2f)' % DEFAULT_SIGMA)
    parser.add_argument('--beta', type=float, action='store', default=DEFAULT_BETA,
                        help='distance of beta = probability 80%% of winning')
    parser.add_argument('--tau', type=float, action='store', default=DEFAULT_TAU, help='dynamic factor tau')
    parser.add_argument('--draw-prob', type=float, action='store', default=DEFAULT_DRAW, metavar='PROB',
                        help='draw probability')
    parser.add_argument('--risk-aversion', type=float, action='store', default=0.1, metavar='RA',
                        help='risk aversion')
    parser.add_argument('--min-races', type=int, action='store', default=3, metavar='N',
                        help='minimum no. of races required per horse before betting')
    parser.add_argument('--max-exposure', type=float, action='store', default=50, metavar='EXP',
                        help='maximum exposure')
    parser.add_argument('--logfile', type=str, action='store', default=None, help='specifies what log file to use')
    parser.add_argument('--logtty', help='prints logging info to the terminal', action='store_true')
    parser.add_argument('train', type=str, action='store', help='training set collection')
    args = parser.parse_args()

    configure_root_logger(args.logtty, args.logfile)
    run_backtest(args)
