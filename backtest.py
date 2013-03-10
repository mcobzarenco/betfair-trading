#!/usr/bin/python
from __future__ import print_function, division

import datetime
import logging
import time
import argparse
from collections import defaultdict
from itertools import product
from multiprocessing import Pool, cpu_count
import warnings
warnings.filterwarnings(action='ignore', category=FutureWarning)
warnings.filterwarnings(action='ignore', category=UserWarning)

import dateutil
import numpy as np
import pandas as pd
from pymongo import MongoClient

from harb import strategy
from harb.execution import HistoricalExecutionService
from harb.scorecard import market_breakdown, make_scorecard, price_historical_bets
from harb.analytics import DEFAULT_MU, DEFAULT_SIGMA, DEFAULT_BETA, DEFAULT_TAU, DEFAULT_DRAW
from harb.common import configure_root_logger,  pandas_to_dicts


DEFAULT_NUM = 10


def parse_date(d):
    return dateutil.parser.parse(d, dayfirst=True) if d is not None else None


def add_scorecard_id_to_dicts(scorecard_id, dicts):
    for d in dicts:
        d['scorecard_id'] = scorecard_id
        yield d


def run_backtest(context):
    n_bkt, args, mparams = context

    formatter = logging.Formatter('%(asctime)s - n_bkt=' + str(n_bkt) + ' - %(levelname)s: %(message)s')
    configure_root_logger(args.logtty, args.logfile,
                          MongoClient(args.host, args.port)[args.db][args.logmongo] if args.logmongo is not None
                          else None, formatter=formatter)

    db = MongoClient(args.host, args.port)[args.db]

    where_clause = defaultdict(lambda: {})
    country, start_date, end_date = 'GB', parse_date(args.start), parse_date(args.end)
    if start_date is not None:
        where_clause['scheduled_off']['$gte'] = start_date
    if end_date is not None:
        where_clause['scheduled_off']['$lte'] = end_date
    if country is not None:
        where_clause['country'] = country
    sorted_races = db[args.train].find(where_clause, sort=[('scheduled_off', 1)], timeout=False)

    exec_services = HistoricalExecutionService(db)
    strat = strategy.Balius(mu=mparams['mu'], sigma=mparams['sigma'], beta=mparams['beta'], tau=mparams['tau'],
                            draw_probability=mparams['draw_prob'], risk_aversion=mparams['risk_aversion'],
                            min_races=mparams['min_races'], max_exposure=mparams['max_exposure'])
    st = time.clock()
    strategy.backtest(exec_services, strat, sorted_races)
    en = time.clock()
    logging.info('Backtest finished in %.2f seconds' % (en - st))

    strat_dict = strat.to_dict()
    strat_id = db[STRATEGIES_COLL].insert(strat_dict)
    logging.info('Strategy serialised to %s with id=%s' % (db[STRATEGIES_COLL], strat_id))

    bets = price_historical_bets(db, exec_services.get_mu_bets()[0])
    scorecard = make_scorecard(bets)
    now = datetime.datetime.utcnow()
    scorecard.update({'params': {'ts': strat_dict['hm']['ts'], 'risk': strat_dict['risk']},
                      'timestamp': now,
                      'run_seconds': en - st,
                      'strategy_id': strat_id})
    scorecard_id = db[SCORECARDS_COLL].insert(scorecard)
    logging.info('Scorecard inserted in %s with id=%s' % (db[SCORECARDS_COLL], scorecard_id))

    db[BETS_COLL].insert(add_scorecard_id_to_dicts(scorecard_id, bets))
    logging.info('Associated bets inserted in %s' % db[BETS_COLL])

    markets = market_breakdown(bets).reset_index()
    markets = pandas_to_dicts(markets, {'n_runners': int})
    db[MARKETS_COLL].insert(add_scorecard_id_to_dicts(scorecard_id, markets))
    logging.info('Associated market breakdown inserted in %s' % db[MARKETS_COLL])


def arg_linspace(s):
    groups = s.split(':')
    if len(groups) == 1:
        return [float(groups[0])]
    elif len(groups) == 2:
        return np.linspace(float(groups[0]), float(groups[1]), DEFAULT_NUM).tolist()
    elif len(groups) == 3:
        return np.linspace(float(groups[0]), float(groups[1]), float(groups[2])).tolist()
    else:
        raise argparse.ArgumentTypeError('"%s" is not a valid parameter or range')


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
    parser.add_argument('--mu', type=arg_linspace, action='store', default=[DEFAULT_MU], help='mu (default=%.2f)' % DEFAULT_MU)
    parser.add_argument('--sigma', type=arg_linspace, action='store', default=[DEFAULT_SIGMA],
                        help='sigma (default=%.2f)' % DEFAULT_SIGMA)
    parser.add_argument('--beta', type=arg_linspace, action='store', default=[DEFAULT_BETA],
                        help='distance of beta = probability 80p of winning (default=%.2f)' % DEFAULT_BETA)
    parser.add_argument('--tau', type=arg_linspace, action='store', default=[DEFAULT_TAU],
                        help='dynamic factor tau (default=%.2f)' % DEFAULT_TAU)
    parser.add_argument('--draw-prob', type=arg_linspace, action='store', default=[DEFAULT_DRAW], metavar='PROB',
                        help='draw probability (default=%.2f)' % DEFAULT_DRAW)
    parser.add_argument('--risk-aversion', type=arg_linspace, action='store', default=[0.1], metavar='RA',
                        help='risk aversion')
    parser.add_argument('--min-races', type=arg_linspace, action='store', default=[3], metavar='N',
                        help='minimum no. of races required per horse before betting')
    parser.add_argument('--max-exposure', type=arg_linspace, action='store', default=[50], metavar='EXP',
                        help='maximum exposure')
    parser.add_argument('--logfile', type=str, action='store', default=None, help='specifies what log file to use')
    parser.add_argument('--logmongo', type=str, action='store', default=None,
                        help='specifies what collection to use for logging to MongoDB')
    parser.add_argument('--logtty', help='prints logging info to the terminal', action='store_true')
    parser.add_argument('train', type=str, action='store', help='training set collection')
    args = parser.parse_args()

    configure_root_logger(args.logtty, args.logfile,
                          MongoClient(args.host, args.port)[args.db][args.logmongo] if args.logmongo is not None
                          else None)

    keys = ['mu', 'sigma', 'beta', 'tau', 'draw_prob', 'risk_aversion', 'min_races', 'max_exposure']
    mparams = [args.mu, args.sigma, args.beta, args.tau, args.draw_prob,
               args.risk_aversion, args.min_races, args.max_exposure]
    n_backtests = reduce(lambda x, y: x * y, map(len, mparams))
    logging.info('The specified ranges of parameters yield %d different backtests.' % n_backtests)

    packed_args = ((n_bkt, args, dict(zip(keys, values))) for n_bkt, values in enumerate(product(*mparams)))
    if n_backtests > 1:
        n_processes = min(cpu_count(), n_backtests) if args.jobs < 0 else args.jobs
        logging.info('Creating a pool with %d worker processes..' % n_processes)
        pool = Pool(processes=n_processes)

        pool.map(run_backtest, packed_args)
        pool.close()
        pool.join()
    else:
        run_backtest(packed_args.next())

