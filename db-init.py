from __future__ import print_function, division

import logging
from pymongo import MongoClient

from harb.common import configure_root_logger


HOST = 'localhost'
PORT = 30001
DB = 'betfair'

VWAO_COLL = 'vwao'
TRAIN_COLL = 'train'


def ensure_index(collection, index):
    logging.info('Ensuring index on %s: %s' % (collection, index))
    collection.ensure_index(index)

configure_root_logger(True)

db = MongoClient(HOST, PORT)[DB]
logging.info('Initializing indexes in database %s' % db)

ensure_index(db[VWAO_COLL], [('scheduled_off', 1)])
ensure_index(db[VWAO_COLL], [('event_id', 1), ('selection', 1)])

ensure_index(db[TRAIN_COLL], [('scheduled_off', 1)])
ensure_index(db[TRAIN_COLL], [('event_id', 1)])


