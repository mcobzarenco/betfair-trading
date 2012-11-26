#!/usr/bin/python
from __future__ import print_function, division

import logging
import argparse
import sys

from betfair import api
from feeds import MasterTimer, QuoteFeed, TradeFeed


class InstructionEngine(object):
    def __init__(self, client):
        self._c = client

    def aim_position(self):
        pass

    def bet(self, bet_type, price, size):
        return {"marketId": self.market_id,
                "selectionId": self.sel_id,
                "betType": bet_type, # 'B' or 'L'
                "price": str(price),
                "size": str(size),
                "betCategoryType": "E", # "E", "M" or "L"
                "betPersistenceType": "NONE", # "NONE", "SP" or "IP"
                "bspLiability": "0", # should be "0" if unused
                "asianLineId": "0" # should be "0" if unused
        }



class LiquidBot1(object):
    def __init__(self, client, market_id, sel_id):
        logging.info('Initialising LiquidBot1 for market_id=%s, sel_id=%s' % (market_id, sel_id))
        self.c = client
        self.market_id = market_id
        self.sel_id = sel_id


    def bet(self, bet_type, price, size):
        return {"marketId": self.market_id,
                "selectionId": self.sel_id,
                "betType": bet_type, # 'B' or 'L'
                "price": str(price),
                "size": str(size),
                "betCategoryType": "E", # "E", "M" or "L"
                "betPersistenceType": "NONE", # "NONE", "SP" or "IP"
                "bspLiability": "0", # should be "0" if unused
                "asianLineId": "0" # should be "0" if unused
                }


    def process_quotes(self, timestamp, quotes):
        selq = filter(lambda x: x['selection_id'] == self.sel_id,quotes['runners'])[0]
        best_lay = selq['lay_prices'][0]
        best_back = selq['back_prices'][0]

        qlay, qback = False, False
        curr_bets = self.c.get_mu_bets(self.market_id, status='U')
        if isinstance(curr_bets, str):
            curr_bets = []

        if best_lay['price'] > 4 or best_back['price'] > 4:
            logging.warning('prices > threshold, cancelling all bets')
            self.c.cancel_bets(map(lambda x: x['betId'], curr_bets))
            return

        for bet in curr_bets:
            bet_id = bet['betId']
            if bet['betType'] == 'B':
                qback = True
                if bet['price'] != best_lay['price']:
                    logging.info("Updating the back bet's price: %.2f -> %.2f" % (bet['price'], best_lay['price']))
                    self.c.update_bets([{'betId': bet_id,
                                         'oldPrice': str(bet['price']),
                                         'newPrice': str(best_lay['price']),
                                         'oldSize': str(bet['size']),
                                         'newSize': str(bet['size']),
                                         'oldBetPersistenceType': 'NONE',
                                         'newBetPersistenceType': 'NONE'
                                        }])
            if bet['betType'] == 'L':
                qlay = True
                if bet['price'] != best_back['price']:
                    logging.info("Updating the lay bet's price: %.2f -> %.2f" % (bet['price'], best_back['price']))
                    self.c.update_bets([{'betId': bet_id,
                                         'oldPrice': str(bet['price']),
                                         'newPrice': str(best_back['price']),
                                         'oldSize': str(bet['size']),
                                         'newSize': str(bet['size']),
                                         'oldBetPersistenceType': 'NONE',
                                         'newBetPersistenceType': 'NONE'
                                        }])

        bets = []
        if not qback:
            logging.info('No back bet, placing GBP10 @ %.2f' % best_lay['price'])
            bets.append(self.bet('B', best_lay['price'], '10'))
        if not qlay:
            logging.info('No lay bet, placing GBP10 @ %.2f' % best_back['price'])
            bets.append(self.bet('L', best_back['price'], '10'))
        if len(bets) > 0:
            self.c.place_bets(bets)


    def process_trades(self, timestamp, trades):
        pass



def main(args):
    l = logging.getLogger()
    l.setLevel(logging.DEBUG)
    l.handlers.append(logging.StreamHandler(sys.stdout))

    client = api.API()
    client.login('aristotle137', 'Antiquark_87')

    bot = LiquidBot1(client, args.market_id, args.selection_id)
    mt = MasterTimer()
    qf = QuoteFeed(client, args.market_id, [bot.process_quotes])
    tf = TradeFeed(client, args.market_id)
    mt.add_feed(qf, 1)
    mt.add_feed(tf, 1)
    mt.run()





parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('market_id', metavar='MARKET_ID',  help='Market ID')
parser.add_argument('selection_id', metavar='SELECTION_ID',  help='Selection ID')
args = parser.parse_args()

main(args)




