from __future__ import print_function, division

import datetime
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
from bottle import route, run, template, debug, static_file, response, redirect

from harb.execution import trade_strategy, get_traded_strategies
from harb.db import BKT_SCORECARDS, BKT_SCORECARD_BETS, BKT_SCORECARD_MARKETS, PAPER_TRADING, PAPER_BETS


SCORECARD_TABLE_FIELDS = {'timestamp': 1, '_id': 1, 'params': 1, 'events': 1, 'llik': 1, 'strategy_id': 1}
SCORECARD_TABLE_ORDER = ['timestamp', '_id', 'mu', 'sigma', 'beta', 'tau', 'mean_pnl', 'diff_lik']

db = MongoClient(port=33000)['betfair']


def to_json(x):
    if isinstance(x, datetime.date) or isinstance(x, datetime.datetime):
        return x.isoformat()
    elif isinstance(x, ObjectId):
        return str(x)
    else:
        repr_json = getattr(x, "__repr_json__", None)
        if repr_json:
            return repr_json()
        else:
            return dict((k, v) for k, v in x.__dict__.iteritems() if not k.startswith("_"))


def retrieve_all_scorecards(coll):
    scards = list(coll.find(fields=SCORECARD_TABLE_FIELDS))
    scards = map(lambda s: {'timestamp': s['timestamp'].isoformat(),
                            'id': str(s['_id']),
                            'strategy_id': str(s['strategy_id']),
                            'mu': s['params']['ts']['mu'],
                            'sigma': s['params']['ts']['sigma'],
                            'beta': s['params']['ts']['beta'],
                            'tau': s['params']['ts']['tau'],
                            'mean_pnl': s['events']['pnl_net']['mean'],
                            'llik_model': s['llik']['model'],
                            'llik_implied': s['llik']['implied'],
                            'diff': (s['llik']['model'] - s['llik']['implied']) / s['events']['coll']['count']}, scards)
    return json.dumps(scards)


def retrieve_scorecard(coll, scorecard_id):
    scard = coll.find_one({'_id': ObjectId(scorecard_id)}, fields={'_id': 0, 'strategy_id': 0})
    scard['scorecard_id'] = scorecard_id
    return json.dumps(scard, default=to_json)


def retrieve_bets_for_scorecard(coll, scorecard_id, market_id=None):
    where_clause = {'scorecard_id': ObjectId(scorecard_id)}
    if market_id is not None:
        where_clause['market_id'] = market_id
    bets = list(coll.find(where_clause, fields={'_id': 0}))
    for bet in bets:
        bet['scorecard_id'] = str(bet['scorecard_id'])
    return json.dumps(bets, default=to_json)


def retrieve_markets_for_scorecard(coll, scorecard_id):
    markets = list(coll.find({'scorecard_id': ObjectId(scorecard_id)}, fields={'_id': 0, 'scorecard_id': 0}))
    return json.dumps(markets, default=to_json)


#### Routes ####


@route('/static/<filename:path>')
def server_static(filename="index.html"):
    return static_file(filename, root='static/')


@route('/')
def index():
    redirect('/backtests/summary')


@route('/backtests/summary')
def index():
    json_scorecards = retrieve_all_scorecards(db[BKT_SCORECARDS])
    json_ptrading = json.dumps(get_traded_strategies(db[PAPER_TRADING], True), default=to_json)
    response.set_header('Content-Type', 'text/html')
    return template('templates/backtests', json_scorecards=json_scorecards, json_ptrading=json_ptrading)


@route('/backtests/detail/<scorecard_id>')
def detail(scorecard_id):
    json_scorecard = retrieve_scorecard(db[BKT_SCORECARDS], scorecard_id)
    response.set_header('Content-Type', 'text/html')
    return template('templates/detail', json_scorecard=json_scorecard)


@route('/backtests/scorecards')
def backtests_scorecards():
    scards = retrieve_all_scorecards(db[BKT_SCORECARDS])
    response.set_header('Content-Type', 'application/json')
    return json.dumps(scards)


@route('/backtests/scorecards/<scorecard_id>')
def scorecard(scorecard_id):
    json_scorecard = retrieve_scorecard(db[BKT_SCORECARDS], scorecard_id)
    response.set_header('Content-Type', 'application/json')
    return json_scorecard


@route('/backtests/scorecards/<scorecard_id>/bets')
def scorecard_bets(scorecard_id):
    bets = retrieve_bets_for_scorecard(db[BKT_SCORECARD_BETS], scorecard_id)
    response.set_header('Content-Type', 'application/json')
    return bets


@route('/backtests/scorecards/<scorecard_id>/bets/<market_id>')
def scorecard_bets_for_market(scorecard_id, market_id):
    bets = retrieve_bets_for_scorecard(db[BKT_SCORECARD_BETS], scorecard_id, market_id)
    response.set_header('Content-Type', 'application/json')
    return bets


@route('/backtests/scorecards/<scorecard_id>/markets')
def scorecard_markets(scorecard_id):
    markets = retrieve_markets_for_scorecard(db[BKT_SCORECARD_MARKETS], scorecard_id)
    response.set_header('Content-Type', 'application/json')
    return markets


@route('/paper/summary')
def paper_summary():
    json_strats = json.dumps(get_traded_strategies(db[PAPER_TRADING]), default=to_json)
    response.set_header('Content-Type', 'text/html')
    return template('templates/paper', json_strats=json_strats)


@route('/paper/summary/<strategy_id>/bets')
def paper_summary_bets(strategy_id):
    bets = list(db[PAPER_BETS].find({'strategy_id': ObjectId(strategy_id)}, fields={'_id': 0}))
    for bet in bets:
        bet['strategy_id'] = str(bet['strategy_id'])
    json_bets = json.dumps(bets, default=to_json)
    response.set_header('Content-Type', 'text/html')
    return template('templates/paper-bets', json_bets=json_bets)


@route('/paper/strategies')
def paper_strategies():
    strats = get_traded_strategies(db[PAPER_TRADING])
    response.set_header('Content-Type', 'application/json')
    return json.dumps(strats, default=to_json)


@route('/paper/strategies/trading')
def paper_strategies_trading():
    strats = get_traded_strategies(db[PAPER_TRADING], True)
    response.set_header('Content-Type', 'application/json')
    return json.dumps(strats, default=to_json)


@route('/paper/add/<strategy_id>')
def add_paper_strat(strategy_id):
    ret = trade_strategy(db[PAPER_TRADING], strategy_id, True)
    response.set_header('Content-Type', 'application/json')
    return ret


@route('/paper/remove/<strategy_id>')
def remove_paper_strat(strategy_id):
    ret = trade_strategy(db[PAPER_TRADING], strategy_id, False)
    response.set_header('Content-Type', 'application/json')
    return ret


debug(True)
run(host='localhost', port=8001, reloader=True)
