from __future__ import print_function, division

import datetime
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
import pandas as pd

from bottle import route, run, template, debug, static_file


SCORECARD_TABLE_FIELDS = {'timestamp': 1, '_id': 1, 'params': 1}
SCORECARD_TABLE_ORDER = ['timestamp', '_id', 'mu', 'sigma', 'beta', 'tau']

db = MongoClient(port=33000)['betfair']


def to_json(x):
    """ Converts numpy types, dates, pandas' frames and series to native types/strings for JSON conversion.
        Usage example: json.dumps(d, default=to_json)"""
    if isinstance(x, datetime.date) or isinstance(x, datetime.datetime):
        return x.isoformat()
    else:
        repr_json = getattr(x, "__repr_json__", None)
        if repr_json:
            return repr_json()
        else:
            return dict((k, v) for k, v in x.__dict__.iteritems() if not k.startswith("_"))


@route('/')
@route('/static/<filename:path>')
def server_static(filename="index.html"):
    return static_file(filename, root='static/')


@route('/scorecards')
def get_scorecard_table():
    scorecards = list(db['scorecards'].find(fields=SCORECARD_TABLE_FIELDS))
    scorecards = map(lambda s: {'timestamp': s['timestamp'],
                                '_id': s['_id'],
                                'mu': s['params']['ts']['mu'],
                                'sigma': s['params']['ts']['sigma'],
                                'beta': s['params']['ts']['beta'],
                                'tau': s['params']['ts']['tau']}, scorecards)
    return pd.DataFrame.from_dict(scorecards)[SCORECARD_TABLE_ORDER].to_html()


@route('/scorecard/<scorecard_id>')
def get_scorecard(scorecard_id):
    scorecard = db['scorecards'].find_one({'_id': ObjectId(scorecard_id)})
    del scorecard['_id']
    return json.dumps(scorecard, default=to_json)


@route('/bets/<scorecard_id>')
def get_bets(scorecard_id):
    bets = db['bets'].find_one({'scorecard_id': ObjectId(scorecard_id)})
    return pd.DataFrame.from_dict(bets['bets']).to_html()


debug(True)
run(host='localhost', port=8080, reloader=True)