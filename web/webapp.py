from __future__ import print_function, division

import datetime
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
import pandas as pd

from bottle import route, run, template, debug, static_file, response
from backtest import SCORECARDS_COLL, STRATEGIES_COLL, BETS_COLL, MARKETS_COLL


VWAO_COLL = 'vwao'

PAPER_STRATS_COLL = 'paper_strats'
PAPER_BETS_COLL = 'paper_bets'

SCORECARD_TABLE_FIELDS = {'timestamp': 1, '_id': 1, 'params': 1, 'events': 1, 'llik': 1, 'strategy_id': 1}
SCORECARD_TABLE_ORDER = ['timestamp', '_id', 'mu', 'sigma', 'beta', 'tau', 'mean_pnl', 'diff_lik']

db = MongoClient(port=33000)['betfair']


def to_json(x):
    if isinstance(x, datetime.date) or isinstance(x, datetime.datetime):
        return x.isoformat()
    else:
        repr_json = getattr(x, "__repr_json__", None)
        if repr_json:
            return repr_json()
        else:
            return dict((k, v) for k, v in x.__dict__.iteritems() if not k.startswith("_"))



@route('/static/<filename:path>')
def server_static(filename="index.html"):
    return static_file(filename, root='static/')


@route('/')
def index():
    json_scorecards = scorecards()
    json_ptrading = paper_strats()
    response.set_header('Content-Type', 'text/html')
    return template('templates/index', json_scorecards=json_scorecards, json_ptrading=json_ptrading)


@route('/paper')
def paper():
    json_strats = paper_strats()
    response.set_header('Content-Type', 'text/html')
    return template('templates/paper', json_strats=json_strats)


@route('/detail/<scorecard_id>')
def detail(scorecard_id):
    json_scorecard = scorecard(scorecard_id)
    response.set_header('Content-Type', 'text/html')
    return template('templates/detail', json_scorecard=json_scorecard)


@route('/api/scorecards')
def scorecards():
    scards = list(db[SCORECARDS_COLL].find(fields=SCORECARD_TABLE_FIELDS))
    scards = map(lambda s: {'timestamp': s['timestamp'].isoformat(),
                            '_id': str(s['_id']),
                            'strategy_id': str(s['strategy_id']),
                            'mu': s['params']['ts']['mu'],
                            'sigma': s['params']['ts']['sigma'],
                            'beta': s['params']['ts']['beta'],
                            'tau': s['params']['ts']['tau'],
                            'mean_pnl': s['events']['pnl_net']['mean'],
                            'llik_model': s['llik']['model'],
                            'llik_implied': s['llik']['implied'],
                            'diff': (s['llik']['model'] - s['llik']['implied']) / s['events']['coll']['count']}, scards)
    response.set_header('Content-Type', 'application/json')
    return json.dumps(scards)


@route('/api/scorecard/<scorecard_id>')
def scorecard(scorecard_id):
    scard = db[SCORECARDS_COLL].find_one({'_id': ObjectId(scorecard_id)}, fields={'_id': 0, 'strategy_id': 0})
    scard['scorecard_id'] = scorecard_id
    response.set_header('Content-Type', 'application/json')
    return json.dumps(scard, default=to_json)


@route('/api/bets/<scorecard_id>')
def bets(scorecard_id):
    bets = list(db[BETS_COLL].find({'scorecard_id': ObjectId(scorecard_id)},
                                   fields={'_id': 0}))
    for bet in bets:
        bet['scorecard_id'] = str(bet['scorecard_id'])
    response.set_header('Content-Type', 'application/json')
    return json.dumps(bets, default=to_json)


@route('/api/bets/<scorecard_id>/<event_id>')
def bets_event(scorecard_id, event_id):
    bets = list(db[BETS_COLL].find({'scorecard_id': ObjectId(scorecard_id), 'event_id': int(event_id)},
                                   fields={'_id': 0, 'scorecard_id': 0}))
    for bet in bets:
        vwao = db[VWAO_COLL].find_one({'event_id': int(event_id), 'selection': bet['selection']})
        bet['volume_matched'] = vwao['volume_matched']
    response.set_header('Content-Type', 'application/json')
    return json.dumps(bets, default=to_json)


@route('/api/events/<scorecard_id>')
def events(scorecard_id):
    events = list(db[EVENTS_COLL].find({'scorecard_id': ObjectId(scorecard_id)},
                                       fields={'_id': 0, 'scorecard_id': 0}))
    response.set_header('Content-Type', 'application/json')
    return json.dumps(events, default=to_json)


@route('/api/paper/strategies')
def paper_strats():
    strats = list(db[PAPER_STRATS_COLL].find())
    for strat in strats:
        strat['_id'] = str(strat['_id'])
        strat['strategy_id'] = str(strat['strategy_id'])
    response.set_header('Content-Type', 'application/json')
    return json.dumps(strats, default=to_json)


@route('/api/paper/add/<strategy_id>')
def add_paper_strat(strategy_id):
    try:
        db[PAPER_STRATS_COLL].insert({'strategy_id': ObjectId(strategy_id)})
    except Exception as e:
        return json.dumps({'success': False, 'strategy_id': strategy_id, 'msg': str(e)})
    response.set_header('Content-Type', 'application/json')
    return json.dumps({'success': True, 'strategy_id': strategy_id})


@route('/api/paper/remove/<strategy_id>')
def remove_paper_strat(strategy_id):
    try:
        db[PAPER_STRATS_COLL].remove({'strategy_id': ObjectId(strategy_id)})
    except Exception as e:
        return json.dumps({'success': False, 'strategy_id': strategy_id, 'msg': str(e)})
    response.set_header('Content-Type', 'application/json')
    return json.dumps({'success': True, 'strategy_id': strategy_id})


debug(True)
run(host='localhost', port=8001, reloader=True)
