from __future__ import print_function, division

import logging
import argparse
import sys


class Robot(object):
    def __init__(self, client, market_id):
        self.c = client
        self.market_id = market_id
        self.ie = InstructionEngine(client, market_id)


class InstructionEngine(object):
    def __init__(self, client, market_id):
        self.c = client
        self.market_id = market_id


    def update_bets(self, sel_id, backs, lays):
        _to_betfair_odds = lambda x: (self.c.set_betfair_odds(x[0]), round(x[1], 2))
        backs = set(map(_to_betfair_odds, backs))
        lays = set(map(_to_betfair_odds, lays))

        curr_bets = self.c.get_mu_bets(self.market_id, status='U')
        if isinstance(curr_bets, str):
            curr_bets = []
        else:
            curr_bets = filter(lambda x: x['selectionId'] == sel_id, curr_bets)

        cancel_ids = []
        for bet in curr_bets:
            try:
                if bet['betType'] == 'B':
                    backs.remove((bet['price'], bet['size']))
                else:
                    lays.remove((bet['price'], bet['size']))
            except KeyError:
                logging.info('[sel_id=%8s] Cancelling %s bet [bet_id=%s, GBP %.2f @ %.2f (p=%.3f)]' %
                             (sel_id, bet['betType'], bet['betId'], bet['size'], bet['price'], 1 / bet['price']))
                cancel_ids.append(bet['betId'])
        self.c.cancel_bets(cancel_ids)

        bets = []
        for back in backs:
            logging.info('[sel_id=%8s] Placing new BACK bet: GBP %.2f @ %.2f (p=%.3f)' % (sel_id, back[1], back[0], 1.0 / back[0]))
            bets.append(self._bet(sel_id, 'B', back[0], back[1]))
        for lay in lays:
            logging.info('[sel_id=%8s] Placing new  LAY bet: GBP %.2f @ %.2f (p=%.3f)' % (sel_id, lay[1], lay[0], 1.0 / lay[0]))
            bets.append(self._bet(sel_id, 'L', lay[0], lay[1]))
        if len(bets) > 0:
            self.c.place_bets(bets)


    def _bet(self, sel_id, bet_type, price, size):
            return {"marketId": self.market_id,
                    "selectionId": sel_id,
                    "betType": bet_type, # 'B' or 'L'
                    "price": str(price),
                    "size": str(size),
                    "betCategoryType": "E", # "E", "M" or "L"
                    "betPersistenceType": "NONE", # "NONE", "SP" or "IP"
                    "bspLiability": "0", # should be "0" if unused
                    "asianLineId": "0" # should be "0" if unused
                    }

    def pnl(self):
        pass