from __future__ import print_function, division

import datetime
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
import pandas as pd

from bottle import route, run, template, debug, static_file


SCORECARD_TABLE_FIELDS = {'timestamp': 1, '_id': 1, 'params': 1, 'events': 1}
SCORECARD_TABLE_ORDER = ['timestamp', '_id', 'mu', 'sigma', 'beta', 'tau', 'mean_pnl']

db = MongoClient(port=30001)['betfair']


def to_json(x):
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


@route('/detail/<scorecard_id>')
def detail(scorecard_id):
    return template('templates/detail', json_scorecard=json.dumps(scorecard(scorecard_id), default=to_json))


@route('/scorecards')
def scorecards():
    scards = list(db['scorecards'].find(fields=SCORECARD_TABLE_FIELDS))
    scards = map(lambda s: {'timestamp': s['timestamp'].isoformat(),
                            '_id': str(s['_id']),
                            'mu': s['params']['ts']['mu'],
                            'sigma': s['params']['ts']['sigma'],
                            'beta': s['params']['ts']['beta'],
                            'tau': s['params']['ts']['tau'],
                            'mean_pnl': s['events']['pnl_net']['mean']}, scards)
    return json.dumps(scards)


@route('/scorecard/<scorecard_id>')
def scorecard(scorecard_id):
    scorecard = db['scorecards'].find_one({'_id': ObjectId(scorecard_id)})
    scorecard['_id'] = str(scorecard['_id'])
    return json.dumps(scorecard, default=to_json)


@route('/bets/<scorecard_id>')
def get_bets(scorecard_id):
    bets = db['bets'].find_one({'scorecard_id': ObjectId(scorecard_id)})
    return pd.DataFrame.from_dict(bets['bets']).to_html()


debug(True)
run(host='localhost', port=8080, reloader=True)
