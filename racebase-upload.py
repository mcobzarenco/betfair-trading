#!/usr/bin/python
from __future__ import print_function, division

import warnings
warnings.filterwarnings(action='ignore', category=FutureWarning)
warnings.filterwarnings(action='ignore', category=UserWarning)

import re
import logging

import dateutil
import numpy as np
import pandas as pd

from harb.common import configure_root_logger, TO_BE_PLACED, convert_types, pandas_to_dicts


def parse_horse_name(h):
    country_ix = h.find('(')
    if country_ix != -1:
        h = h[:country_ix]
    return h.strip().lower()


def parse_place(p):
    if isinstance(p, float):
        return -1
    digits = filter(lambda c: c.isdigit(), p)
    if len(digits) == 0:
        return -1
    return int(digits)


def upload(args):
    first = lambda x: x.iget(0)
    args, path = args


    try:
        _, file_name = split(path)

        formatter = logging.Formatter('%(asctime)s - ' + file_name + ' - %(levelname)s: %(message)s')
        configure_root_logger(formatter=formatter)
        db = MongoClient(args.host, args.port)[args.db]

        logging.info('Reading csv file into memory')
        races = pd.read_csv(path, sep='\t', parse_dates=[[0, 1]], dayfirst=True)
        if len(races) <=2 :
            logging.warning('No races in file. Skipping')
            return

        races.rename(columns={'race_date_race_time': 'scheduled_off',
                              'horse_name': 'selection',
                              'place': 'ranking'}, inplace=True)

        races['selection'] = races['selection'].map(parse_horse_name)
        races['ranking'] = races['ranking'].map(parse_place)

        races = pd.DataFrame.from_dict([{'course': k[0],
                                         'scheduled_off': k[1],
                                         'selection': v['selection'][v.ranking >= 0].tolist(),
                                         'ranking': (v['ranking'][v.ranking >= 0] - 1).tolist()}
                                        for k, v in races.groupby(['track', 'scheduled_off'])])

        #print(races)

        dtypes = list(races.dtypes[races.dtypes == np.int64].index)
        type_mappers = dict(zip(dtypes, [int] * len(dtypes)))
        db[args.races].insert(pandas_to_dicts(races))

        logging.info('Successfully uploaded to %s' % db)
    except Exception as e:
        logging.critical(e)
        raise


if __name__ == '__main__':
    import zipfile
    from os.path import split, splitext
    import argparse
    from multiprocessing import Pool, cpu_count
    from pymongo import MongoClient

    parser = argparse.ArgumentParser(description='Uploads horseracebase.com historical data to a MongoDB database')
    parser.add_argument('files', metavar='FILES', type=str, nargs='+', help='zip/csv/pd files to upload')
    parser.add_argument('--host', type=str, action='store', default='localhost', help='MongoDB host (default=localhost)')
    parser.add_argument('--port', type=int, action='store', default=33000, help='MongoDB port (default=33000)')
    parser.add_argument('--db', type=str, action='store', default='betfair', help='db (default=betfair)')
    parser.add_argument('--jobs', type=int, action='store', default=-1, help='how many jobs to use')
    parser.add_argument('--races', type=str, action='store', default='horseracebase',
                        help='races collection (default=horseracebase)')
    args = parser.parse_args()

    configure_root_logger()
    cpus = min(cpu_count(), len(args.files)) if args.jobs < 0 else args.jobs

    logging.info('Creating a pool with %d worker processes..' % cpus)
    pool = Pool(processes=cpus)
    pool.map(upload, zip([args] * len(args.files), args.files))
