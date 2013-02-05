#!/usr/bin/python
from __future__ import print_function, division

import warnings; warnings.filterwarnings(action='ignore', category=FutureWarning)
import re
import logging

import dateutil
import numpy as np
import pandas as pd

from harb.common import configure_root_logger


def pandas_to_dicts(df, mappers={}):
    def map_it(d):
        for (m, f) in mappers.items():
            if m in d:
                d[m] = f(d[m])
        return d
    if len(mappers) == 0:
        return (df.ix[i].to_dict() for i in df.index)
    else:
        return (map_it(df.ix[i].to_dict()) for i in df.index)


def extract_name(s):
    pos = re.search('[A-Za-z]', s)
    if pos is None:
        return None
    else:
        name = s[pos.start():].strip().lower()
        if any(map(lambda x: x in name, ('yes', 'no'))):
            return None
        return name


def races_from_bars(bars):
    logging.info('Creating races from bars..')
    bars['winners'] = None
    win_ix = bars['win_flag'] == 1
    bars['winners'].ix[win_ix] = bars['selection'].ix[win_ix]

    last = lambda x: x.iget(0)
    agg_dict = {'country': last,
                'event': last,
                'course': last,
                'scheduled_off': last,
                'selection': lambda x: list(set(x.dropna())),
                'winners': lambda x: None if len(x.dropna()) == 0 else list(set(x.dropna()))}
    races = bars.groupby(['event_id']).agg(agg_dict)
    races.sort('scheduled_off', inplace=True)
    return races


def vwao_from_bars(bars):
    logging.info('Calculating VWAO from bars..')
    bars['notional'] = bars.volume_matched * bars.odds

    agg_dict = {'notional': lambda x: float(np.sum(x)),
                'volume_matched': lambda x: float(np.sum(x)),
                'scheduled_off': lambda x: x.iget(0)}
    gb = bars.groupby(['event_id', 'selection']).aggregate(agg_dict)
    gb['vwao'] = gb.notional / gb.volume_matched
    return gb


def training_from_races(races):
    logging.info('Creating training set from races..')
    races = races[races['runners'].map(lambda x: x is not None and len(x) > 0)]
    races = races[races['winners'].map(lambda x: x is not None)]

    races['sel_str'] = races['runners'].map(lambda x: reduce(lambda a, b: a + b, sorted(x)))
    gb = races.groupby('sel_str')

    frames = []
    for (sel_str, events) in gb:
        if len(events) == 1:
            events = events.irow(0).to_dict()
            events['event'] = [events['event']]
            events['event_id'] = int(events['event_id'])
            try:
                events['ranking'] = [int(r not in events['winners']) for r in events['runners']]
            except:
                print(events)
                break
            # del events['sel_str']
            frames.append(events)
        elif len(events) == 2:
            placed = events[events['event'].map(lambda s: s.upper()) == 'TO BE PLACED']
            if len(placed) != 1:
                continue
            placed = placed.irow(0).to_dict()
            placed['ranking'] = [int(r not in placed['winners']) + 1 for r in placed['runners']]
            towin = events[events['event'] != 'TO BE PLACED']
            towin = towin.irow(0).to_dict()

            if len(towin['winners']) > 1:
                continue

            assert(len(towin['winners']) == 1)
            placed['ranking'][placed['runners'].index(towin['winners'][0])] = 0
            placed['event'] = [placed['event'], towin['event']]
            placed['event_id'] = [placed['event_id'], towin['event_id']]
            # del placed['sel_str']
            frames.append(placed)
    return frames


if __name__ == '__main__':
    import zipfile
    from os.path import split, splitext
    import argparse
    from pymongo import MongoClient


    parser = argparse.ArgumentParser(description='Uploads Betfair historical data to a MongoDB database')
    parser.add_argument('files', metavar='FILES', type=str, nargs='+', help='zip/csv/pd files to upload')
    parser.add_argument('--host', type=str, action='store', default='localhost', help='MongoDB host (default=localhost)')
    parser.add_argument('--port', type=int, action='store', default=33000, help='MongoDB port (default=33000)')
    parser.add_argument('--db',type=str, action='store', default='betfair', help='db (default=betfair)')
    parser.add_argument('--races',type=str, action='store', default='races', help='races collection (default=races)')
    parser.add_argument('--train',type=str, action='store', default='train', help='training set collection (default=train)')
    parser.add_argument('--vwao',type=str, action='store', default='vwao', help='volume-weighted-average-odds (vwao) collection (default=vwao)')
    parser.add_argument('--logfile', type=str, help='specifies what log file to use', action='store')
    parser.add_argument('--logtty', help='prints logging info to the terminal', action='store_true')
    args = parser.parse_args()

    configure_root_logger(args.logtty, args.logfile)
    parse = lambda x: dateutil.parser.parse(x, dayfirst=True)

    db = MongoClient(args.host, args.port)[args.db]
    try:
        for path in args.files:
            dir, file_name = split(path)
            file_part, ext = splitext(file_name)
            if ext == '.zip':
                logging.info("Reading zipped csv file '%s' into memory" % file_name)
                input = zipfile.ZipFile(path, 'r').open(file_part + '.csv')
            else:
                logging.info("Reading csv file '%s' into memory" % file_name)
                input = path

            bars = pd.read_csv(input, parse_dates=['SCHEDULED_OFF'], date_parser=parse)
            bars.columns = bars.columns.map(lambda x: x.lower())

            # Insert other filters here:
            bars = bars[bars.in_play == 'PE']
            bars['selection'] = bars['selection'].map(extract_name)

            races = races_from_bars(bars).reset_index()
            db[args.races].insert(pandas_to_dicts(races, {'event_id': int}))

            train = training_from_races(races)
            db[args.train].insert(train)

            vwao = vwao_from_bars(bars).reset_index()
            db[args.vwao].insert(pandas_to_dicts(vwao, {'event_id': int}))

            logging.info('Successfully uploaded to %s' % db)
    except Exception as e:
        logging.critical(e)
        raise
