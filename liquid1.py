#!/usr/bin/python
from __future__ import print_function, division

import logging
import argparse
import sys

import numpy as np
import pandas as pd

from betfair import api
from harb.feeds import MasterTimer, QuoteFeed
from robot import Robot


class LiquidBot1(Robot):
    def __init__(self, client, market_id, sel_id):
        super(LiquidBot1, self).__init__(client, market_id)
        logging.info('Initialising LiquidBot1 for market_id=%s, sel_id=%s' % (market_id, sel_id))
        self.sel_id = sel_id
        self._display_pnl = 0


    def process_quotes(self, timestamp, quotes):
        selq = filter(lambda x: x['selection_id'] == self.sel_id, quotes['runners'])[0]
        best_lay = selq['lay_prices'][0]['price']
        best_back = selq['back_prices'][0]['price']
        amt_lay, amt_back = 15.0, 15.0

        pnl =  self.market_pnl(quotes)

        curr_exp = filter(lambda x: x['selectionId'] == self.sel_id, self.c.get_market_profit_and_loss(self.market_id))[0]['ifWin']
        curr_exp -= pnl
        # logging.info('curr_exp=%.2f' % curr_exp)
        if curr_exp > 0:
            amt_back -= curr_exp
            if amt_back < 2.0: amt_back = 0.0
        else:
            amt_lay += curr_exp
            if amt_lay < 2.0: amt_lay = 0.0

        ps = best_lay / best_back
        back_bet, lay_bet = [(best_lay, amt_back)], [(best_back, amt_lay)]
        if ps < 0.25:
            lay_bet = [(selq['back_prices'][1]['price'], amt_lay)]
        elif ps > 4:
            back_bet = [(selq['lay_prices'][1]['price'], amt_back)]
        if amt_back < 2:
            back_bet = []
        if amt_lay < 2:
            lay_bet = []
        self.ie.update_bets(self.sel_id, back_bet, lay_bet)

        if self._display_pnl % 20 == 0:
            logging.info('Marked-to-Market PnL: %.2f' % pnl)
        self._display_pnl += 1


    def get_book_top(self, quotes):
        qs = []
        for r in quotes['runners']:
            back_prices = r['back_prices']
            if len(back_prices) > 0:
                back_amount, back_price = back_prices[0]['amount'], back_prices[0]['price']
            else:
                back_amount, back_price = np.nan, np.nan
            qs.append(['B', r['selection_id'], back_price, back_amount])

            lay_prices = r['lay_prices']
            if len(lay_prices) > 0:
                lay_amount, lay_price = lay_prices[0]['amount'], lay_prices[0]['price']
            else:
                lay_amount, lay_price = np.nan, np.nan
            qs.append(['L', r['selection_id'], lay_price, lay_amount])
        return pd.DataFrame(qs, columns=['bet_type', 'selection_id', 'price', 'amount']).set_index(['bet_type', 'selection_id'])


    def market_pnl(self, quotes):
        MIN_P = 0.00

        book_top = self.get_book_top(quotes)
        inv_odds = (1 / book_top.ix['B'].price).fillna(MIN_P)
        imp_prob = inv_odds / inv_odds.sum()

        pnl = self.c.get_market_profit_and_loss(self.market_id)
        payoffs = pd.DataFrame.from_dict(pnl).set_index('selectionId')['ifWin']
        return np.dot(imp_prob, payoffs)


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
    #tf = TradeFeed(client, args.market_id)
    mt.add_feed(qf, 1)
    #mt.add_feed(tf, 1)
    mt.run()





parser = argparse.ArgumentParser()
parser.add_argument('market_id', metavar='MARKET_ID',  help='Market ID')
parser.add_argument('selection_id', metavar='SELECTION_ID',  help='Selection ID')
args = parser.parse_args()

main(args)




