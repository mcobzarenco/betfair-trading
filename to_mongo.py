#!/usr/bin/python
from __future__ import print_function, division

import warnings; warnings.filterwarnings(action='ignore')
import re

import dateutil
import numpy as np
import pandas as pd



def pandas_to_dict(df):
    return [df.ix[i].to_dict() for i in df.index]


def extract_name(s):
    pos = re.search('[A-Za-z]', s)
    if pos is None:
        return None
    else:
        name = s[pos.start():].strip().lower()
        if any(map(lambda x: x in name, ('yes', 'no'))):
            return None
        return name


def as_games(bars):
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
    games = bars.groupby(['event_id']).agg(agg_dict).sort('scheduled_off', inplace=True)
    games = pandas_to_dict(games.reset_index())
    for g in games:
        g['event_id'] = int(g['event_id'])

    return games


def calc_vwao(bars):
    bars['notional'] = bars.volume_matched * bars.odds

    agg_dict = {'notional': lambda x: float(np.sum(x)),
                'volume_matched': lambda x: float(np.sum(x)),
                'scheduled_off': lambda x: x.iget(0)}
    gb = bars.groupby(['event_id', 'selection']).aggregate(agg_dict)
    gb['vwao'] = gb.notional / gb.volume_matched

    gb = pandas_to_dict(gb.reset_index())
    for g in gb:
        g['event_id'] = int(g['event_id'])
    return gb


if __name__ == '__main__':
    import pymongo
    import sys
    import zipfile
    from os.path import split, splitext
    import argparse

    parser = argparse.ArgumentParser(description='Uploads Betfair historical data to a MongoDB database')
    parser.add_argument('files', metavar='FILES', type=str, nargs='+', help='zip/csv/pd files to upload')
    parser.add_argument('--host', type=str, action='store', default='localhost', help="MongoDB host (default=localhost)")
    parser.add_argument('--port', type=int, action='store', default=33000, help="MongoDB port (default=33000)")
    parser.add_argument('--db',type=str, action='store', default='db', help="db (default=betfair)")
    parser.add_argument('--save', type=str, metavar='DIR', action='store', default=None, help="save files as Pandas' binary format to DIR")
    args = parser.parse_args()

    parse = lambda x: dateutil.parser.parse(x, dayfirst=True)

    db = pymongo.connection.Connection(args.host, args.port)[args.db]
    for path in args.files:
        dir, file_name = split(path)
        file_part, ext = splitext(file_name)
        if ext == '.pd':
            print('Uploading file %s (Pandas binary format) to %s' % (file_name, db))
            # Pandas' binary format
            # fname should contain the result pd.read_csv(csv_file, parse_dates=['SCHEDULED_OFF'], date_parser=parse)
            train = pd.load(path)
        elif ext == '.zip':
            print('Uploading file %s (zipped csv file) to %s' % (file_name, db))
            z = zipfile.ZipFile(path, 'r').open(file_part + '.csv')
            train = pd.read_csv(z, parse_dates=['SCHEDULED_OFF'], date_parser=parse)
        else:
            print('Uploading file %s (csv file) to %s' % (file_name, db))
            train = pd.read_csv(path, parse_dates=['SCHEDULED_OFF'], date_parser=parse)
        train.columns = train.columns.map(lambda x: x.lower())

        # Insert other filters here:
        train = train[train.in_play == 'PE']

        train['selection'] = train['selection'].map(extract_name)

        db['races'].insert(as_games(train), safe=True)
        db['vwao'].insert(calc_vwao(train), safe=True)