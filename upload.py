#!/usr/bin/python
from __future__ import print_function, division

import warnings
warnings.filterwarnings(action='ignore', category=FutureWarning)
warnings.filterwarnings(action='ignore', category=UserWarning)

import logging
from itertools import imap

import dateutil
import numpy as np
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError


from harb.common import configure_root_logger, TO_BE_PLACED, convert_types, \
    pandas_to_dicts, SELECTION_BLACK_LIST, extract_horse_name, get_first


def races_from_bars(bars):
    logging.info('Creating races from bars..')
    bars['winners'] = None
    win_ix = bars['win_flag'] == 1
    bars['winners'].ix[win_ix] = bars['selection'].ix[win_ix]

    agg_dict = {'country': get_first,
                'event': get_first,
                'course': get_first,
                'scheduled_off': get_first,
                'selection_id': lambda x: list(set(x.dropna())),
                'selection': lambda x: list(set(x.dropna())),
                'winners': lambda x: None if len(x.dropna()) == 0 else list(set(x.dropna()))}
    races = bars.groupby(['market_id']).agg(agg_dict)
    # races.sort('scheduled_off', inplace=True)
    return races


def vwao_from_bars(bars):
    def format_vwao(d):
        d['back_prices'] = [{'amount': d['total_matched'] / 2.0,
                             'price': d['vwao'],
                             'depth': 1,
                             'type': 'L'}]
        d['lay_prices'] = [{'amount': d['total_matched'] / 2.0,
                            'price': d['vwao'],
                            'depth': 1,
                            'type': 'B'}]
        d['last_price_matched'] = d['vwao']
        del d['vwao']
        return d

    logging.info('Calculating VWAO from bars..')
    bars['notional'] = bars.volume_matched * bars.odds

    agg_dict = {'country': get_first,
                'event': get_first,
                'course': get_first,
                'scheduled_off': get_first,
                'notional': lambda x: float(np.sum(x)),
                'volume_matched': lambda x: float(np.sum(x)),
                'selection': get_first}
    gb = bars.dropna(subset=['selection']).groupby(['market_id', 'selection_id']).aggregate(agg_dict) \
        .rename(columns={'volume_matched': 'total_matched'})
    gb['vwao'] = gb.notional / gb.total_matched
    del gb['notional']

    return imap(format_vwao, pandas_to_dicts(gb.reset_index()))


def training_from_races(races):
    logging.info('Creating training set from races..')
    races = races.dropna(subset=['selection', 'winners'])
    races = races[races['selection'].map(lambda x: len(x) > 0)]

    black_list = races['selection'].map(lambda xs: all([x not in SELECTION_BLACK_LIST for x in xs]))
    logging.info('%d races removed using the selection black list' % (len(black_list) - sum(black_list)))
    races = races[black_list]

    races['n_runners'] = races['selection'].map(len)

    frames = []
    for (_, events) in races.groupby(['course', 'scheduled_off', 'n_runners']):
        # print(len(events))
        if len(events) == 1:
            events = events.irow(0).to_dict()
            events['event'] = events['event']
            events['ranking'] = [int(r not in events['winners']) for r in events['selection']]
            frames.append(events)
        elif len(events) == 2:
            placed = events[events['event'] == TO_BE_PLACED]
            if len(placed) != 1:
                logging.warning('Skipping events with the same (course, time) with no|multiple "to be placed"; '
                                'market_id: %s' % events['market_id'].tolist())
                continue
            placed = placed.irow(0).to_dict()
            placed['ranking'] = [int(r not in placed['winners']) + 1 for r in placed['selection']]
            towin = events[events['event'] != TO_BE_PLACED].irow(0).to_dict()

            if len(towin['winners']) > 1:
                continue

            placed['ranking'][placed['selection'].index(towin['winners'][0])] = 0
            towin['ranking'] = placed['ranking']

            frames.append(placed)
            frames.append(towin)
    return frames


def upload(args):
    args, path = args
    parse = lambda x: dateutil.parser.parse(x, dayfirst=True)

    try:
        directory, file_name = split(path)
        file_part, ext = splitext(file_name)

        formatter = logging.Formatter('%(asctime)s - ' + file_name + ' - %(levelname)s: %(message)s')
        configure_root_logger(args.logtty, args.logfile, formatter=formatter)
        db = MongoClient(args.host, args.port)[args.db]

        if ext == '.zip':
            logging.info('Reading zipped csv file into memory')
            fin = zipfile.ZipFile(path, 'r').open(file_part + '.csv')
        else:
            logging.info('Reading csv file into memory')
            fin = path

        bars = pd.read_csv(fin, parse_dates=['SCHEDULED_OFF'], date_parser=parse)
        bars.columns = bars.columns.map(lambda x: x.lower())
        bars = bars.rename(columns={'event_id': 'market_id'})
        for col in ['market_id', 'selection_id']:
            bars[col] = bars[col].map(str)  # Make sure dtype==str

        # Insert other filters here:
        bars = bars[bars.in_play == 'PE']
        bars['selection'] = bars['selection'].map(extract_horse_name)

        races = races_from_bars(bars).reset_index()
        train = training_from_races(races)
        vwao = vwao_from_bars(bars)

        try:
            db[args.races].insert(pandas_to_dicts(races), continue_on_error=True)
        except DuplicateKeyError as e:
            logging.error('Some duplicate keys in %s; If this is a surprise, ABORT! msg=%s' %
                          (db[args.races], e))

        try:
            db[args.train].insert(convert_types(train, {'n_runners': int}), continue_on_error=True)
        except DuplicateKeyError as e:
            logging.error('Some duplicate keys in %s; If this is a surprise, ABORT! msg=%s' %
                          (db[args.train], e))

        try:
            db[args.vwao].insert(vwao, continue_on_error=True)
        except DuplicateKeyError as e:
            logging.error('Some duplicate keys in %s; If this is a surprise, ABORT! msg=%s' %
                          (db[args.vwao], e))

        logging.info('Successfully uploaded to %s' % db)
    except Exception as e:
        logging.critical(e)
        raise


if __name__ == '__main__':
    import zipfile
    from os.path import split, splitext
    import argparse
    from multiprocessing import Pool, cpu_count

    parser = argparse.ArgumentParser(description='Uploads Betfair historical data to a MongoDB database')
    parser.add_argument('files', metavar='FILES', type=str, nargs='+', help='zip/csv/pd files to upload')
    parser.add_argument('--host', type=str, action='store', default='localhost', help='MongoDB host (default=localhost)')
    parser.add_argument('--port', type=int, action='store', default=33000, help='MongoDB port (default=33000)')
    parser.add_argument('--db', type=str, action='store', default='betfair', help='db (default=betfair)')
    parser.add_argument('--jobs', type=int, action='store', default=-1, help='how many jobs to use')
    parser.add_argument('--races', type=str, action='store', default='races', help='races collection (default=races)')
    parser.add_argument('--train', type=str, action='store', default='train',
                        help='training set collection (default=train)')
    parser.add_argument('--vwao', type=str, action='store', default='vwao',
                        help='volume-weighted-average-odds (vwao) collection (default=vwao)')
    parser.add_argument('--logfile', type=str, action='store', default=None, help='specifies what log file to use')
    parser.add_argument('--logtty', help='prints logging info to the terminal', action='store_true')
    args = parser.parse_args()

    configure_root_logger(args.logtty, args.logfile)
    if len(args.files) > 1:
        cpus = min(cpu_count(), len(args.files)) if args.jobs < 0 else args.jobs

        logging.info('Creating a pool with %d worker processes..' % cpus)
        pool = Pool(processes=cpus)
        pool.map(upload, zip([args] * len(args.files), args.files))
    else:
        upload((args, args.files[0]))

