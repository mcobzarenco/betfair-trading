from __future__ import print_function, division

import argparse
import logging

import pymongo
import pandas as pd

from harb.common import *
from settings import *

def betfair2train(races):
    logging.info("Creating training set")
    races = pd.DataFrame.from_dict(races)
    races = races.rename(columns={'selection': 'runners'})
    races = races[races['runners'].map(lambda x: x is not None and len(x) > 0)]
    races = races[races['winners'].map(lambda x: x is not None)]

    del races['_id']
    races['sel_str'] = races['runners'].map(lambda x: reduce(lambda a, b: a + b, sorted(x)))
    gb = races.groupby('sel_str')

    ngroup = 0
    frames = []
    for (sel_str, events) in gb:
        if ngroup % 10000 == 0:
            logging.info("Converting race %d" % ngroup)
        ngroup += 1
        if len(events) == 1:
            events = events.irow(0).to_dict()
            events['event'] = [events['event']]
            events['event_id'] = [events['event_id']]
            try:
                events['ranking'] = [int(r not in events['winners']) for r in events['runners']]
            except:
                print(events)
                break
            del events['sel_str']
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
            del placed['sel_str']
            frames.append(placed)

    def fix_types(e):
        e['event_id'] = map(int, e['event_id'])
        return e
    return map(fix_types, frames)



def main(args):
    logging.info("Conecting to mongodb at %s:%d" % (args.host, args.port))
    db = pymongo.connection.Connection(args.host, args.port)[args.db]

    logging.info("Loading %d races in memory" % db[args.races].count())
    races = list(db['bf_races'].find())

    training_set = betfair2train(races)
    if args.remove_first:
        logging.info("Deleting training data in %s" % args.train)
        db['bf_training'].remove()
    logging.info("Inserting the training set into %s" % args.train)
    db['bf_training'].insert(training_set)


if __name__ == '__main__':
    configure_logging()
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--host', action='store', default=MONGODB_HOST, help="MongoDB host")
    parser.add_argument('--port', action='store', default=MONGODB_PORT, help="MongoDB port")
    parser.add_argument('--db', action='store', default=HARB_DB,  help='MongoDB database with races')
    parser.add_argument('--races', action='store', default="bf_races",  help='collection with races')
    parser.add_argument('--train', action='store', default="bf_training",  help='collection for storing the training set')
    parser.add_argument('--remove-first', action='store_true',  help='Market ID')
    #parser.print_help()

    try:
        args = parser.parse_args()
        main(args)
    except:
        print('Invoked with: %s' % args)
        raise


