from __future__ import print_function, division

import logging
from pymongo import MongoClient

from harb.common import configure_root_logger
from harb.db import VWAO_COLL, RACES_COLL, TRAIN_COLL


HOST = 'localhost'
PORT = 33000
DB = 'betfair'


def ensure_index(collection, index, unique=False):
    if unique:
        logging.info('Ensuring unique index on %s: %s' % (collection, index))
    else:
        logging.info('Ensuring index on %s: %s' % (collection, index))
    collection.ensure_index(index, unique=unique, drop_dups=unique)


configure_root_logger(True)

db = MongoClient(HOST, PORT)[DB]
logging.info('Initializing indexes in database %s' % db)

ensure_index(db[VWAO_COLL], [('scheduled_off', 1)])
ensure_index(db[VWAO_COLL], [('market_id', 1), ('selection', 1)], unique=True)
ensure_index(db[VWAO_COLL], [('market_id', 1), ('selection_id', 1)], unique=True)

ensure_index(db[RACES_COLL], [('market_id', 1)], unique=True)

ensure_index(db[TRAIN_COLL], [('scheduled_off', 1)])
ensure_index(db[TRAIN_COLL], [('market_id', 1)], unique=True)


