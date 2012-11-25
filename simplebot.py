from betfair.api import API
from time import sleep, time

# Created by Birchy 06/02/2012
# bespokebots.com
# NOTE:
# To make this bot fully automated for use on a (Linux) VPS server, you will
# need to remove the "print" statements and write the data to a log file.
# This is because the "print" will fail after you logout of the remote server
# due to the terminal no longer being available. You should launch the bot 
# with the command "python simplebot.py &" rather than "python simplebot.py".
# Adding the "&" will detach the process from the terminal so it will continue
# running when you logout of the remote server.

class SimpleBot(object):
    """lay all odds-on horses in UK win-only races"""
    def __init__(self):
        rps = 1 # Refreshes Per Second
        self.api = API('uk') # exchange ('uk' or 'aus')
        self.no_session = True
        self.throttle = {'rps': 1.0 / rps, 'next_req': time()}

    def login(self, uname = '', pword = '', prod_id = '', vend_id = ''):
        """login to betfair"""
        if uname and pword and prod_id and vend_id:
            resp = self.api.login(uname, pword, prod_id, vend_id)
            if resp == 'OK': self.no_session = False
            return resp
        else:
            return 'login() ERROR: INCORRECT_INPUT_PARAMETERS'

    def get_markets(self):
        """returns a list of markets or an error string"""
        # NOTE: get_all_markets is NOT subject to data charges!
        markets = self.api.get_all_markets(
                events = ['7'], # horse racing
                hours = 0.5, # starting in the next 30 mins (0.25 = 15 mins, 2 = 120 mins, etc)
                include_started = False, # exclude in-play markets
                countries = ['GBR'] # British racing only
                )
        if type(markets) is list:
            # sort markets by start time + filter
            for market in markets[:]: # loop through a COPY of markets as we're modifying it on the fly...
                markets.remove(market)
                if (market['bsp_market'] == 'Y' # BSP markets only
                    and market['market_name'] != 'To Be Placed' # NOT place markets
                    and market['market_status'] == 'ACTIVE' # market is active
                    and market['market_type'] == 'O' # Odds market only
                    and market['no_of_winners'] == 1 # single winner market
                    ):
                    # calc seconds til start of race
                    delta = market['event_date'] - self.api.API_TIMESTAMP
                    sec_til_start = delta.days * 86400 + delta.seconds # 1 day = 86400 sec
                    temp = [sec_til_start, market]
                    markets.append(temp)
            markets.sort() # sort into time order (earliest race first)
            return markets
        elif markets == 'API_ERROR: NO_SESSION':
            self.no_session = True
        else:
            return markets

    def do_throttle(self):
        """return only when it is safe to send another data request"""
        wait = self.throttle['next_req'] - time()
        if wait > 0: sleep(wait)
        self.throttle['next_req'] = time() + self.throttle['rps']

    def check_strategy(self, market_id = ''):
        """check market for suitable bet"""
        if market_id:
            # get market prices
            self.do_throttle()
            prices = self.api.get_market_prices(market_id)
            if type(prices) is dict and prices['status'] == 'ACTIVE':
                # loop through runners and prices and create bets
                bets = []
                for runner in prices['runners']:
                    if runner['back_prices']: # make sure prices are available!
                        back_price = runner['back_prices'][0]['price']
                        if back_price < 1.99:
                            # horse is odds-on, so lets lay it...
                            # set price to current back price + 1 pip (i.e. put our bet at front of queue)
                            bet_price = self.api.set_betfair_odds(price = back_price, pips = +1)
                            bet_size = 2.00 # minimum stake
                            bet = {
                                'marketId': market_id,
                                'selectionId': runner['selection_id'],
                                'betType': 'L',
                                'price': '%.2f' % bet_price, # set string to 2 decimal places
                                'size': '%.2f' % bet_size,
                                'betCategoryType': 'E',
                                'betPersistenceType': 'NONE',
                                'bspLiability': '0',
                                'asianLineId': '0'
                                }
                            bets.append(bet)
                # place bets (if any have been created)
                if bets:
                    resp = self.api.place_bets(bets)
                    s = 'PLACING BETS...\n'
                    s += 'Bets: ' + str(bets) + '\n'
                    s += 'Place bets response: ' + str(resp) + '\n'
                    s += '---------------------------------------------'
                    print s
                    # check session
                    if resp == 'API_ERROR: NO_SESSION':
                        self.no_session = True
            elif prices == 'API_ERROR: NO_SESSION':
                self.no_session = True
            elif type(prices) is not dict:
                s = 'check_strategy() ERROR: prices = ' + str(prices) + '\n'
                s += '---------------------------------------------'
                print s

    def start(self, uname = '', pword = '', prod_id = '', vend_id = ''):
        """start the main loop"""
        # login/monitor status
        login_status = self.login(uname, pword, prod_id, vend_id)
        while login_status == 'OK':
            # get list of markets starting soon
            markets = self.get_markets()
            if type(markets) is list:
                if len(markets) == 0:
                    # no markets found...
                    s = 'No markets found. Sleeping for 30 seconds...'
                    print s
                    sleep(30) # bandwidth saver!
                else:
                    print 'Found', len(markets), 'markets. Checking strategy...'
                    for market in markets:
                        # do we have bets on this market?
                        market_id = market[1]['market_id']
                        mu_bets = self.api.get_mu_bets(market_id)
                        if mu_bets == 'NO_RESULTS':
                            # we have no bets on this market...
                            self.check_strategy(market_id)
            # check if session is still OK
            if self.no_session:
                login_status = self.login(uname, pword, prod_id, vend_id)
                s = 'API ERROR: NO_SESSION. Login resp =' + str(login_status) + '\n'
                s += '---------------------------------------------'
                print s
        # main loop ended...
        s = 'login_status = ' + str(login_status) + '\n'
        s += 'MAIN LOOP ENDED...\n'
        s += '---------------------------------------------'
        print s


bot = SimpleBot()
bot.start('username', 'password', '82', '0') # product id 82 = free api

