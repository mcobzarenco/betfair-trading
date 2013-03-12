#!/usr/bin/env python

"""
CREATED BY: Birchy.
WEBSITE: www.bespokebots.com
FORUM: http://diybetfairbots.lefora.com/

A betfair API wrapper using only built-in Python libraries, with a strong
"Keep It Simple" theme. Python's string functions have proven to out perform
parsing libraries and regex for this application. Personally, I find this code
significantly faster and easier to work with than bloated libraries such as
ZSI or SUDS. Because the XML data is a known entity, we can parse it more
efficiently by using dedicated string functions rather than generic parsers.

If you wish to show your appreciation, donations can be sent via PayPal to:
accounts@bespokebots.com

For help, bug fixes or suggestions, please email me: support@bespokebots.com

Thank you and good luck!


* HOW IT WORKS:
* The basic theory is to load the request xml strings into memory at start up
  and then use those as templates. This uses less than 100KB of memory if using
  ALL templates. Most bots only require 7 or 8 of the 58+ available functions.
* gSoap library is used to create the raw xml templates, however this only needs
  to be called when doing a fresh build (i.e. when the WSDL file changes)
  The gSoap command prompts have been automated within __make_templates() but
  if you require a pure Python library, then this can be deleted as long as the
  "templates" folder is created externally and made available.
* Delete the "templates" FOLDER to trigger a rebuild of the XML requests.
* Tested on Ubuntu 8.10+ and should be OK with any operating system that
  supports Python version 2.6 or newer.

ROAD MAP:
  April 2010:
  * A few minor bugs fixed.
  * Http code separated into its own Class. This makes it easier to replace
    urllib2 with alternative http libraries such as pyCurl.
  * Some functions now return more information (i.e. place_bets(), etc).
  * set_betfair_odds() function added.
  * get_odds_spread() function added
  * place_bet_undersize() function added for greening up. DO NOT abuse!
  * get_market_profit_and_loss() function added.
  * API_TIMESTAMP added. This is useful for checking when an event will start
    by comparing the server GMT time against the marketTime (GMT) field returned
    by get_market().

  May 2010:
  * get_account_funds() now returns a dictionary rather than a single float.
  * added round up/down parameters to set_betfair_odds()
  * removed place_bets_undersize() as it was unreliable due to the 3 requests
  * place_bets() now handles undersize bets using only one request

  July 2010:
  * place_bets() updated to handle BSP bets (original function thought that
    BSP bets were undersize due to bet size = 0).
  * place_bets() now returns a list of bet responses instead of a dictionary.
  * get_all_markets() now returns a list of dictionaries instead of a list of
    delimited strings.
  * get_all_markets() was returning wrong results when specifying to/from dates.
    original function was using datetime.now() instead of a GMT/UTC timestamp.
  * example code added for calculating "time until event starts".

  August 2010:
  * get_complete_market_prices() added.

  September 2010:
  * get_all_markets() updated to handle escaped delimiters. was occasionally
    returning incorrect results, particularly on RSA horse racing.

  October 2010:
  * get_market_prices() and get_complete_market_prices() now return a
    dictionary. the previous list/grid format was not simple to use without
    reference to this source file.
  * include_started param added to get_all_markets().
  * source code "prettified" in accordance with pyLint rules.

  November 2010:
  * updated to include the Australian exchange.

  March 2011:
  * get_bet_history() added.

  June 2011:
  * get_account_statement() added. NOTE: this function is limited to make it
    more reliable. There are a number of server-side issues that Betfair have
    not (yet) rectified.
  * get_all_event_types() added. Used to cross reference event ids returned by
    get_bet_history() and/or get_account_statement().
  * "event_date" in get_all_markets() is now a datetime object instead of
    milliseconds since epoch.

  July 2011:
  * get_market_prices() now returns 'price' and 'amount' as a float instead of
    a string.

  October 2011:
  * Error messages updated. If server returns an unrecognised response, causing
    resp_code to be an empty string, all functions now return the complete
    response string rather than an empty string.
  * get_all_markets() now takes "countries" parameter as input. Dunno why I left
    it out in the first place. Must of been a lazy day!
  * place_bets() no longer has facility for undersize bets due to reliability
    issues.

  February 2012:
  * update_bets() now returns a list instead of a dict. This makes the response
    object type consistent with the place_bets() function.

  March 2012:
  * min_bet_size removed from __init__() of API class. This has been obsolete
    since place_bet_undersize() was removed.
  * place_bets() now checks if bets parameter is a valid list. This function
    used to return None if supplied bets was an empty list.

  April 2012:
  * get_mu_bets() now returns floats for 'price', 'size', 'bspLiability' and
    'handicap' instead of strings.
  * get_market_prices() and get_complete_market_prices() now return floats for
    'far_sp', 'actual_sp', 'last_price_matched', 'near_sp', 'total_matched' and
    'reduction_factor' instead of strings...UNLESS the value is an empty string,
    in which case it remains unchanged.
  * login() now returns more info if an API_ERROR occurs.

  May 2012:
  * get_market() now checks the data type of eventHierarchy as it is not always
    an ArrayOfEventId.
  * get_market() now returns the runners as a list instead of a dict.

  August 2012:
  * get_market_traded_volume() function added. uses getMarketTradedVolumeCompressed API.
"""

import os
import datetime
import sys
from math import ceil
from http import Http
import logging
from time import sleep, time
from functools import wraps


CALLS_PER_MIN = 60


class Throtller(object):
    def __init__(self, calls_per_min=CALLS_PER_MIN):
        self._secs_between_calls = 60.0 / calls_per_min
        self._last_call = 0.0

    def throttle(self, f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            diff = time() - self._last_call
            logging.debug('Last call %.2f seconds ago' % diff)
            if diff < self._secs_between_calls:
                logging.debug('Sleeping for %.2f seconds' % (self._secs_between_calls - diff))
                sleep(self._secs_between_calls - diff)
            self._last_call = time()
            return f(*args, **kwargs)
        return wrapped


throttle = Throtller().throttle


class API_T(object):
    """betfair API library
    NOTES:
    * API_TIMESTAMP only indicates the time of the betfair server when it last
      sent us a reply, so is only as accurate as our request frequency. Use of
      datetime.utcnow() may be less accurate because it only indicates the local
      time and does not compensate for internet lag.
    * To calculate the time remaining until event starts, we need to use the
      marketTime field returned by the get_market() function (GMT/UTC time).
      EXAMPLE:
        market_id = '123456'
        market_data = self.get_market(market_id)
        start_time = datetime.strptime(market_data['marketTime'],
                                       '%Y-%m-%dT%H:%M:%S.%fZ')
        delta = start_time - self.API_TIMESTAMP
        sec_til_start = delta.days * 86400 + delta.seconds # 1 day = 86400 sec
    """
    API_TIMESTAMP = None # datetime object indicating betfair server time (GMT)

    def __init__(self, exchange = "uk"):
        self.http = Http()
        self.abs_path = os.path.abspath(os.path.dirname(__file__))
        self.templates = {"global": {}, "uk": {}, "aus": {}}
        self.session_token = ""
        self.exchange = exchange # must be "uk" OR "aus"!
        if self.exchange not in ["uk", "aus"]:
            raise Exception("Invalid exchange string. MUST be 'uk' OR 'aus'!")
        self.odds_table = []
        self.__init_odds_table()
        self.__load_templates()
        self.free_api = False # see Login() function

    def __init_odds_table(self):
        """loads the lookup table for the set_betfair_odds() function"""
        self.odds_table = [1.01, 1.02, 1.03, 1.04, 1.05, 1.06, 1.07, 1.08, 1.09,
            1.1, 1.11, 1.12, 1.13, 1.14, 1.15, 1.16, 1.17, 1.18, 1.19, 1.2,
            1.21, 1.22, 1.23, 1.24, 1.25, 1.26, 1.27, 1.28, 1.29, 1.3, 1.31,
            1.32, 1.33, 1.34, 1.35, 1.36, 1.37, 1.38, 1.39, 1.4, 1.41, 1.42,
            1.43, 1.44, 1.45, 1.46, 1.47, 1.48, 1.49, 1.5, 1.51, 1.52, 1.53,
            1.54, 1.55, 1.56, 1.57, 1.58, 1.59, 1.6, 1.61, 1.62, 1.63, 1.64,
            1.65, 1.66, 1.67, 1.68, 1.69, 1.7, 1.71, 1.72, 1.73, 1.74, 1.75,
            1.76, 1.77, 1.78, 1.79, 1.8, 1.81, 1.82, 1.83, 1.84, 1.85, 1.86,
            1.87, 1.88, 1.89, 1.9, 1.91, 1.92, 1.93, 1.94, 1.95, 1.96, 1.97,
            1.98, 1.99, 2.0, 2.02, 2.04, 2.06, 2.08, 2.1, 2.12, 2.14, 2.16,
            2.18, 2.2, 2.22, 2.24, 2.26, 2.28, 2.3, 2.32, 2.34, 2.36, 2.38, 2.4,
            2.42, 2.44, 2.46, 2.48, 2.5, 2.52, 2.54, 2.56, 2.58, 2.6, 2.62,
            2.64, 2.66, 2.68, 2.7, 2.72, 2.74, 2.76, 2.78, 2.8, 2.82, 2.84,
            2.86, 2.88, 2.9, 2.92, 2.94, 2.96, 2.98, 3.0, 3.05, 3.1, 3.15, 3.2,
            3.25, 3.3, 3.35, 3.4, 3.45, 3.5, 3.55, 3.6, 3.65, 3.7, 3.75, 3.8,
            3.85, 3.9, 3.95, 4.0, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9,
            5.0, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 6.0, 6.2, 6.4,
            6.6, 6.8, 7.0, 7.2, 7.4, 7.6, 7.8, 8.0, 8.2, 8.4, 8.6, 8.8, 9.0,
            9.2, 9.4, 9.6, 9.8, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5,
            14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0,
            19.5, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0,
            30.0, 32.0, 34.0, 36.0, 38.0, 40.0, 42.0, 44.0, 46.0, 48.0, 50.0,
            55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0, 110.0,
            120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0, 200.0,
            210.0, 220.0, 230.0, 240.0, 250.0, 260.0, 270.0, 280.0, 290.0,
            300.0, 310.0, 320.0, 330.0, 340.0, 350.0, 360.0, 370.0, 380.0,
            390.0, 400.0, 410.0, 420.0, 430.0, 440.0, 450.0, 460.0, 470.0,
            480.0, 490.0, 500.0, 510.0, 520.0, 530.0, 540.0, 550.0, 560.0,
            570.0, 580.0, 590.0, 600.0, 610.0, 620.0, 630.0, 640.0, 650.0,
            660.0, 670.0, 680.0, 690.0, 700.0, 710.0, 720.0, 730.0, 740.0,
            750.0, 760.0, 770.0, 780.0, 790.0, 800.0, 810.0, 820.0, 830.0,
            840.0, 850.0, 860.0, 870.0, 880.0, 890.0, 900.0, 910.0, 920.0,
            930.0, 940.0, 950.0, 960.0, 970.0, 980.0, 990.0, 1000.0]

    def __send_request(self, global_serv = True, req_xml = "", soap_action = ""):
        """sends http request"""
        # add session token to request
        req_xml = self.set_value(req_xml, "<sessionToken>", self.session_token,
            "</sessionToken>")
        # setup url
        if global_serv:
            url = "https://api.betfair.com/global/v3/BFGlobalService"
        elif self.exchange == "uk":
            url = "https://api.betfair.com/exchange/v5/BFExchangeService"
        elif self.exchange == "aus":
            url = "https://api-au.betfair.com/exchange/v5/BFExchangeService"
        else:
            raise Exception("Invalid server. Must be 'uk' OR 'aus'!")
        # send request
        resp_xml = self.http.send_http_request(url, req_xml, soap_action)
        resp_xml = resp_xml.replace('"', "'")
        # update server timestamp - default to utcnow() rather than None
        self.API_TIMESTAMP = datetime.datetime.utcnow()
        s_time = self.get_value(resp_xml, "<timestamp xsi:type='xsd:dateTime'>", "</timestamp>")
        if s_time:
            self.API_TIMESTAMP = datetime.datetime.strptime(s_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        # update session token + return
        token = self.get_value(resp_xml, "<sessionToken xsi:type='xsd:string'>",
            "</")
        if token:
            self.session_token = token
        return resp_xml

    def set_betfair_odds(self, price = 0.0, pips = 0, round_up = False,
        round_down = False):
        """convert calculated odds to betfair increments & add/subtract pips.
        * "pips" should be an integer. pips = 3 ADDS 3 pips to price. pips = -1
          SUBTRACTS 1 pip from price, etc, etc. Returned price defaults to
          1000 or 1.01 if calculated price is outside these limits.
        """
        # set calculated odds to nearest increment
        price = float(price)
        prc = price
        if price < 1.01:
            prc = increment = 1.01
        elif price < 2:
            increment = 0.01
        elif price < 3:
            increment = 0.02
        elif price < 4:
            increment = 0.05
        elif price < 6:
            increment = 0.1
        elif price < 10:
            increment = 0.2
        elif price < 20:
            increment = 0.5
        elif price < 30:
            increment = 1.0
        elif price < 50:
            increment = 2.0
        elif price < 100:
            increment = 5.0
        elif price < 1000:
            increment = 10.0
        else:
            price = 1000.0
            increment = 1000.0
        if round_up:
            prc = round(ceil(prc / increment) * increment, 2)
        elif round_down:
            prc = round(int(prc / increment) * increment, 2)
        else:
            prc = round(round(prc / increment) * increment, 2)
        # add/subtract pips
        if price <= 0:
            return prc # prc = 1.01
        else:
            if pips != 0 and self.odds_table.count(prc) > 0:
                index = self.odds_table.index(prc) + pips
                if index < 0:
                    index = 0
                if index > 349:
                    index = 349
                prc = self.odds_table[index]
        return prc

    def get_odds_spread(self, back_odds = 0.0, lay_odds = 0.0):
        """returns the No. of pips difference between back and lay odds"""
        # make sure odds are correct increment
        back_odds = self.set_betfair_odds(back_odds)
        lay_odds = self.set_betfair_odds(lay_odds)
        # search odds array and calculate difference
        diff = self.odds_table.index(lay_odds) \
            - self.odds_table.index(back_odds)
        return diff

    def login(self, username = "", password = "", product_id = "82",
        vendor_id = "0"):
        """login to betfair"""
        # are we using free api?
        if product_id == "82": self.free_api = True
        req_xml = self.templates["global"]["login"]
        req_xml = self.set_value(req_xml, "<username>", username, "</username>")
        req_xml = self.set_value(req_xml, "<password>", password, "</password>")
        req_xml = self.set_value(req_xml, "<productId>", product_id,
            "</productId>")
        req_xml = self.set_value(req_xml, "<vendorSoftwareId>", vendor_id,
            "</vendorSoftwareId>")
        resp_xml = self.__send_request(True, req_xml, "login")
        resp_code = self.get_value(resp_xml, "LoginErrorEnum'>", "</")
        if resp_code == "API_ERROR":
            resp_code += ": " + self.get_value(resp_xml,
                "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
        return resp_code

    def keep_alive(self):
        """prevents session time out (approx 20 mins) when no other API calls
        are being made
        """
        req_xml = self.templates["global"]["keepAlive"]
        resp_xml = self.__send_request(True, req_xml, "keepAlive")
        api_error = self.get_value(resp_xml,
            "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
        return api_error

    def logout(self):
        """logout of betfair"""
        req_xml = self.templates["global"]["logout"]
        resp_xml = self.__send_request(True, req_xml, "logout")
        resp_code = self.get_value(resp_xml, "LogoutErrorEnum'>", "</")
        if resp_code == "OK":
            self.session_token = "" # reset session
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
        return resp_code

    @throttle
    def get_account_funds(self):
        """get available account funds"""
        req_xml = self.templates[self.exchange]["getAccountFunds"]
        resp_xml = self.__send_request(False, req_xml, "getAccountFunds")
        resp_code = self.get_value(resp_xml, "GetAccountFundsErrorEnum'>", "</")
        if not resp_code:
            # occurs rarely - could be an error on betfairs' servers??
            return 'API_ERROR: empty response code. Response XML = ' + resp_xml
        elif resp_code == "OK":
            funds = {}
            resp_xml = self.get_value(resp_xml, "</header>",
                "<errorCode xsi:type='n2:GetAccountFundsErrorEnum'>")
            fields = resp_xml.split("</")
            for field in fields[:-1]:
                key = self.get_value(field, "<", " ")
                val = field.rpartition("'>")[2]
                try:
                    funds[key] = float(val)
                except:
                    funds[key] = val # probably minorErrorCode
            return funds
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
            return resp_code

    def get_active_event_types(self):
        """returns a dictionary containing active event type names and ids"""
        req_xml = self.templates["global"]["getActiveEventTypes"]
        resp_xml = self.__send_request(True, req_xml, "getActiveEventTypes")
        resp_code = self.get_value(resp_xml, "GetEventsErrorEnum'>", "</")
        if resp_code == "OK":
            resp_xml = self.get_value(resp_xml,
                "<eventTypeItems xsi:type='n2:ArrayOfEventType'>",
                "</eventTypeItems>")
            events = resp_xml.split("</n2:EventType>")
            events_list = {}
            for event in events[:-1]:
                eid = self.get_value(event, "<id xsi:type='xsd:int'>", "</id>")
                name = self.get_value(event, "<name xsi:type='xsd:string'>",
                    "</name>")
                if name: events_list[name] = eid
            return events_list
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
            return resp_code

    def get_all_event_types(self):
        """returns a dictionary containing ALL event type names and ids"""
        req_xml = self.templates["global"]["getAllEventTypes"]
        resp_xml = self.__send_request(True, req_xml, "getAllEventTypes")
        resp_code = self.get_value(resp_xml, "GetEventsErrorEnum'>", "</")
        if resp_code == "OK":
            resp_xml = self.get_value(resp_xml,
                "<eventTypeItems xsi:type='n2:ArrayOfEventType'>",
                "</eventTypeItems>")
            events = resp_xml.split("</n2:EventType>")
            events_list = {}
            for event in events[:-1]:
                eid = self.get_value(event, "<id xsi:type='xsd:int'>", "</id>")
                name = self.get_value(event, "<name xsi:type='xsd:string'>",
                    "</name>")
                if name: events_list[name] = eid
            return events_list
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
            return resp_code

    @throttle
    def get_market(self, market_id = ""):
        """returns static data for given market id"""
        if market_id:
            req_xml = self.templates[self.exchange]["getMarket"]
            req_xml = self.set_value(req_xml, "<marketId>", market_id,
                "</marketId>")
            resp_xml = self.__send_request(False, req_xml, "getMarket")
            resp_code = self.get_value(resp_xml, "GetMarketErrorEnum'>", "</")
            if resp_code == "OK":
                temp = {"event_ids": [], "runners": []}
                # parse event hierarchy
                data_type = self.get_value(resp_xml, "<eventHierarchy xsi:", ">")
                if "ArrayOfEventId" in data_type:
                    event_ids = self.get_value(resp_xml, "<eventHierarchy xsi:type='n2:ArrayOfEventId'>", "</eventHierarchy>")
                    for event_id in event_ids.split("</n2:EventId>")[:-1]:
                        s = event_id.rpartition(">")[2]
                        temp["event_ids"].append(s)
                # parse runners array
                data_type = self.get_value(resp_xml, "<runners xsi:", ">")
                if "ArrayOfRunner" in data_type:
                    runners = self.get_value(resp_xml, "<runners xsi:type='n2:ArrayOfRunner'>", "</runners>")
                    for runner in runners.split("</n2:Runner>")[:-1]:
                        asian_line_id = self.get_value(runner, "<asianLineId xsi:type='xsd:int'>", "</asianLineId>")
                        handicap = self.get_value(runner, "<handicap xsi:type='xsd:double'>", "</handicap>")
                        name = self.get_value(runner, "<name xsi:type='xsd:string'>", "</name>")
                        selection_id = self.get_value(runner, "<selectionId xsi:type='xsd:int'>", "</selectionId>")
                        d = {   "asian_line_id": asian_line_id,
                                "handicap": handicap,
                                "name": name,
                                "selection_id": selection_id
                            }
                        temp["runners"].append(d)
                # parse market info
                info = self.get_value(resp_xml, "<market xsi:type='n2:Market'>", "</market>")
                info = self.remove_string(info, "<eventHierarchy xsi:", "</eventHierarchy>")
                info = self.remove_string(info, "<runners xsi:", "</runners>")
                for field in info.split("</"):
                    key = self.get_value(field, "<", " ")
                    val = field.rpartition(">")[2]
                    if key: temp[key] = val
                return temp
            else:
                if resp_code == "API_ERROR":
                    resp_code += ": " + self.get_value(resp_xml,
                        "<errorCode xsi:type='n2:APIErrorEnum'>",
                        "</errorCode>")
                elif resp_code == '':
                    resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
                return resp_code
        return None

    @throttle
    def get_all_markets(self, events = None, hours = None, include_started = True, countries = None):
        """get all current markets. returns a list of markets. each market is a
           dictionary: keys match the api names, all values are strings.
        * "events" should be set as a list[] of event id's (if req'd)
        * "hours" can be an integer or float or None and indicates how far into
           the future to get markets. Hours = 0.25 is equal to 15 minutes,
           0.5 = 30 minutes, 1 = 1 hour, etc. None = unlimited.
        * "include_started" indicates whether or not to include markets that
           have already started. This does not guarantee the market will have
           status "in-play" because some markets (i.e. financials) do not
           indicate.
        * "countries" [optional] should be a list[] of ISO3 country codes from which
          to include sports, e.g. GBR horse racing. A list of ISO3 codes is available
          here: http://en.wikipedia.org/wiki/ISO_3166-1_alpha-3
        """
        req_xml = self.templates[self.exchange]["getAllMarkets"]
        req_xml = self.remove_string(req_xml, "<locale>", "</locale>\n")
        # set event ids (if req'd)
        if events:
            temp = ""
            for event in events:
                temp += "<int>" + str(event) + "</int>\n"
            req_xml = self.set_value(req_xml, "<eventTypeIds>\n", temp, "</eventTypeIds>")
        else: # unused - remove from request
            req_xml = self.remove_string(req_xml, "<eventTypeIds>", "</eventTypeIds>\n")
        # set from/to dates
        if hours:
            # get current time in GMT/UTC (betfair server is GMT)
            now_gmt = self.API_TIMESTAMP
            if not now_gmt:
                now_gmt = datetime.datetime.utcnow()
            from_date = now_gmt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            if include_started: from_date = "null"
            to_date = (now_gmt + datetime.timedelta(hours = hours)
                ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            req_xml = self.set_value(req_xml, "<fromDate>", from_date,
                "</fromDate>")
            req_xml = self.set_value(req_xml, "<toDate>", to_date, "</toDate>")
        else: # unused - remove from request
            req_xml = self.remove_string(req_xml, "<fromDate>", "</toDate>\n")
        # set country codes
        if countries and type(countries) is list:
            temp = ""
            for country in countries:
                temp += "<Country>" + country + "</Country>\n"
            req_xml = self.set_value(req_xml, "<countries>\n", temp, "</countries>")
        else:
            # unused - remove from request
            req_xml = self.remove_string(req_xml, "<countries>", "</countries>\n")
        # send request/check response
        resp_xml = self.__send_request(False, req_xml, "getAllMarkets")
        resp_xml = resp_xml.replace("\:", "") # remove escaped delimiter
        resp_xml = resp_xml.replace("\~", "") # remove escaped delimiter
        resp_code = self.get_value(resp_xml, "GetAllMarketsErrorEnum'>", "</")
        if resp_code == "OK":
            data = self.get_value(resp_xml,
                "<marketData xsi:type='xsd:string'>", "</marketData>")
            markets = data.split(":")[1:]
            keys = ["market_id", "market_name", "market_type", "market_status",
                    "event_date", "menu_path", "event_hierarchy", "bet_delay",
                    "exchange_id", "country_code", "last_refresh",
                    "no_of_runners", "no_of_winners", "total_matched",
                    "bsp_market", "turning_in_play"]
            ret = []
            for market in markets:
                vals = market.split("~")
                temp = dict(zip(keys, vals))
                # convert event start date to datetime object
                if temp.has_key('event_date'):
                    temp['event_date'] = datetime.datetime.utcfromtimestamp(int(temp['event_date']) / 1000)
                # convert numbers to floats or ints
                nums = ["no_of_runners", "no_of_winners", "total_matched"]
                for k in nums:
                    try:
                        temp[k] = int(temp[k])
                    except:
                        try:
                            temp[k] = float(temp[k])
                        except:
                            pass
                ret.append(temp)
            return ret
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
            return resp_code

    @throttle
    def get_market_prices(self, market_id = "", currency_code = ""):
        """returns a dict OR an error string"""
        req_xml = self.templates[self.exchange]["getMarketPricesCompressed"]
        if currency_code:
            req_xml = self.set_value(req_xml, "<currencyCode>", currency_code,
                "</currencyCode>")
        else: # remove from request (user default currency will be used)
            req_xml = self.remove_string(req_xml, "<currencyCode>", "</currencyCode>\n")
        req_xml = self.set_value(req_xml, "<marketId>",
            market_id, "</marketId>")
        resp_xml = self.__send_request(False, req_xml, "getMarketPricesCompressed")
        # check response
        resp_code = self.get_value(resp_xml, "GetMarketPricesErrorEnum'>", "</")
        if resp_code == "OK":
            # parse response
            prices = self.get_value(resp_xml,
                "<marketPrices xsi:type='xsd:string'>", "</marketPrices>")
            prices = prices.replace("\:", "") # remove escaped delimiters
            rows = prices.split(":")
            temp_dict = {}
            for row in rows:
                if "|" in row:
                    # this is a runner...
                    fields = row.split("|")
                    if len(fields) > 2:
                        # parse info (fields[0])
                        keys = ["selection_id", "order_index", "total_matched",
                                "last_price_matched", "handicap",
                                "reduction_factor", "vacant", "far_sp",
                                "near_sp", "actual_sp"]
                        vals = fields[0].split("~")
                        runner = dict(zip(keys, vals))
                        if not runner.has_key("back_prices"):
                            runner["back_prices"] = []
                        if not runner.has_key("lay_prices"):
                            runner["lay_prices"] = []
                        # parse prices (fields[1+])
                        keys = ["price", "amount", "type", "depth"]
                        for i in xrange(1, 3):
                            # fields[1] = backs, fields[2] = lays
                            vals = fields[i].split("~")[:-1]
                            key_count = len(keys)
                            price_count = len(vals) / key_count
                            for j in xrange(price_count):
                                start = j * key_count
                                stop = start + key_count
                                temp = dict(zip(keys, vals[start:stop]))
                                temp["price"] = float(temp["price"])
                                temp["amount"] = float(temp["amount"])
                                if i == 1:
                                    runner["back_prices"].append(temp)
                                elif i == 2:
                                    runner["lay_prices"].append(temp)
                        # convert prices and amounts to floats
                        floats = ["far_sp", "actual_sp", "last_price_matched",
                                "near_sp", "total_matched", "reduction_factor"]
                        for k in runner:
                            if k in floats:
                                try:
                                    runner[k] = float(runner[k])
                                except:
                                    pass
                        # append to market dict
                        temp_dict["runners"].append(runner)
                else:
                    # split market info
                    keys = ["market_id", "currency", "status", "in_play_delay",
                            "no_of_winners", "info", "discount_allowed",
                            "base_rate", "refresh_time", "none_runners",
                            "bsp_market"]
                    vals = row.split("~")
                    temp_dict = dict(zip(keys, vals))
                    temp_dict["runners"] = []
                    # convert numbers to floats or ints
                    nums = ["no_of_winners", "base_rate"]
                    for k in nums:
                        try:
                            temp_dict[k] = int(temp_dict[k])
                        except:
                            try:
                                temp_dict[k] = float(temp_dict[k])
                            except:
                                pass
            return temp_dict
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
        return resp_code

    @throttle
    def get_complete_market_prices(self, market_id = "", currency_code = ""):
        """returns a dict OR an error string"""
        req_xml = self.templates[self.exchange]["getCompleteMarketPricesCompressed"]
        if currency_code:
            req_xml = self.set_value(req_xml, "<currencyCode>", currency_code,
                "</currencyCode>")
        else: # remove from request (user default currency will be used)
            req_xml = self.remove_string(req_xml, "<currencyCode>", "</currencyCode>\n")
        req_xml = self.set_value(req_xml, "<marketId>",
            market_id, "</marketId>")
        resp_xml = self.__send_request(False, req_xml,
            "getCompleteMarketPricesCompressed")
        # check response code
        resp_code = self.get_value(resp_xml,
            "GetCompleteMarketPricesErrorEnum'>", "</")
        if resp_code == "OK":
            # parse response
            prices = self.get_value(resp_xml,
                "<completeMarketPrices xsi:type='xsd:string'>",
                "</completeMarketPrices>")
            prices = prices.replace("\:", "") # remove escaped delimiters
            rows = prices.split(":")
            temp_dict = {}
            for row in rows:
                if "|" in row:
                    # this is a runner...
                    fields = row.split("|")
                    if len(fields) > 1:
                        # parse info (fields[0])
                        keys = ["selection_id", "order_index", "total_matched",
                                "last_price_matched", "handicap",
                                "reduction_factor", "vacant", "asian_line_id",
                                "far_sp", "near_sp", "actual_sp"]
                        vals = fields[0].split("~")
                        runner = dict(zip(keys, vals))
                        if not runner.has_key("prices"):
                            runner["prices"] = []
                        # parse prices (fields[1+])
                        keys = ["price", "back_amount", "lay_amount",
                                "bsp_back_amount", "bsp_lay_amount"]
                        vals = fields[1].split("~")[:-1]
                        key_count = len(keys)
                        price_count = len(vals) / key_count
                        for j in xrange(price_count):
                            start = j * key_count
                            stop = start + key_count
                            temp = dict(zip(keys, vals[start:stop]))
                            # convert to floats
                            for k in keys:
                                temp[k] = float(temp[k])
                            runner["prices"].append(temp)
                        # convert to floats
                        floats = ["far_sp", "actual_sp", "last_price_matched",
                                "near_sp", "total_matched", "reduction_factor"]
                        for k in runner:
                            if k in floats:
                                try:
                                    runner[k] = float(runner[k])
                                except:
                                    pass
                        # append to market dict
                        temp_dict["runners"].append(runner)
                else:
                    # split market info
                    keys = ["market_id", "in_play_delay", "none_runners"]
                    vals = row.split("~")
                    temp_dict = dict(zip(keys, vals))
                    temp_dict["runners"] = []
            return temp_dict
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
            return resp_code


    @throttle
    def get_market_traded_volume(self, market_id = "", currency_code = ""):
        """returns a list of runners and price/volume data OR an error string"""
        req_xml = self.templates[self.exchange]["getMarketTradedVolumeCompressed"]
        if currency_code:
            req_xml = self.set_value(req_xml, "<currencyCode>", currency_code, "</currencyCode>")
        else: # remove from request (user default currency will be used)
            req_xml = self.remove_string(req_xml, "<currencyCode>", "</currencyCode>\n")
        req_xml = self.set_value(req_xml, "<marketId>", market_id, "</marketId>")
        resp_xml = self.__send_request(False, req_xml, "getMarketTradedVolumeCompressed")
        # check response
        resp_code = self.get_value(resp_xml, "GetMarketTradedVolumeCompressedErrorEnum'>", "</")
        if resp_code == "OK":
            # parse response
            temp_list = []
            volumes = self.get_value(resp_xml, "<tradedVolume xsi:type='xsd:string'>", "</tradedVolume>")
            runners = volumes.split(":")[1:]
            for runner in runners:
                temp_dict = {}
                amounts = runner.split("|")
                for amount in amounts:
                    fields = amount.split("~")
                    if len(fields) == 2:
                        # parse price/volume info
                        temp_dict["volumes"].append({"price": float(fields[0]), "amount": float(fields[1])})
                    else:
                        # parse runner info
                        temp_dict["selection_id"] = fields[0]
                        temp_dict["asian_line_id"] = fields[1]
                        temp_dict["final_bsp_price"] = float(fields[2]) # only >0 when final BSP is calculated
                        temp_dict["final_bsp_back_volume"] = float(fields[3]) # only >0 when final BSP is calculated
                        temp_dict["final_bsp_lay_volume"] = float(fields[4]) # only >0 when final BSP is calculated
                        temp_dict["volumes"] = []
                temp_list.append(temp_dict)
            return temp_list
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml, "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
        return resp_code

    def place_bets(self, bets = None):
        """returns a LIST of bet responses or an error code. parameter hints:
            bets[] is a LIST of bets. Each bet should be a dict of parameters:
                e.g. {
                    "marketId": "",
                    "selectionId": "",
                    "betType": "", # 'B' or 'L'
                    "price": "",
                    "size": "",
                    "betCategoryType": "", # "E", "M" or "L"
                    "betPersistenceType": "", # "NONE", "SP" or "IP"
                    "bspLiability": "", # should be "0" if unused
                    "asianLineId": "" # should be "0" if unused
                    }
        to place a BSP bet for stake 2.00:
            set "size" and "price" = "0"
            set "betCategoryType" = "M"
            set "bspLiability" = "2.0"
        """
        if bets and type(bets) is list:
            # build PlaceBets array string
            temp = ""
            for bet in bets:
                temp += "<PlaceBets>\n"
                temp += "<marketId>" + bet["marketId"] + "</marketId>\n"
                temp += "<selectionId>" + bet["selectionId"] \
                    + "</selectionId>\n"
                temp += "<betType>" + bet["betType"] + "</betType>\n"
                temp += "<price>" + bet["price"] + "</price>\n"
                temp += "<size>" + bet["size"] + "</size>\n"
                temp += "<betCategoryType>" + bet["betCategoryType"] \
                    + "</betCategoryType>\n"
                temp += "<betPersistenceType>" + bet["betPersistenceType"] \
                    + "</betPersistenceType>\n"
                temp += "<bspLiability>" + bet["bspLiability"] \
                    + "</bspLiability>\n"
                temp += "<asianLineId>" + bet["asianLineId"] \
                    + "</asianLineId>\n"
                temp += "</PlaceBets>\n"
            # send request
            if temp:
                req_xml = self.templates[self.exchange]["placeBets"]
                req_xml = self.set_value(req_xml, "<bets>", temp, "</bets>")
                resp_xml = self.__send_request(False, req_xml, "placeBets")
                resp_code = self.get_value(resp_xml, "PlaceBetsErrorEnum'>", "</")
                if resp_code == "OK":
                    # parse bet responses
                    results_array = self.get_value(resp_xml,
                        "<betResults xsi:type='n2:ArrayOfPlaceBetsResult'>",
                        "</betResults>")
                    results = results_array.split("</n2:PlaceBetsResult>")
                    temp = []
                    for result in results[:-1]:
                        bet_id = self.get_value(result, "<betId xsi:type='xsd:long'>", "</betId>")
                        price = self.get_value(result, "<averagePriceMatched xsi:type='xsd:double'>",
                            "</averagePriceMatched>")
                        code = self.get_value(result, "<resultCode xsi:type='n2:PlaceBetsResultEnum'>",
                            "</resultCode>")
                        size = self.get_value(result, "<sizeMatched xsi:type='xsd:double'>",
                            "</sizeMatched>")
                        success = self.get_value(result, "<success xsi:type='xsd:boolean'>", "</success>")
                        temp.append({
                            "bet_id": bet_id,
                            "price": price,
                            "code": code,
                            "size": size,
                            "success": success
                            })
                    return temp
                else:
                    if resp_code == "API_ERROR":
                        resp_code += ": " + self.get_value(resp_xml,
                            "<errorCode xsi:type='n2:APIErrorEnum'>",
                            "</errorCode>")
                    elif resp_code == '':
                        resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
                return resp_code
        else:
            return "place_bets() ERROR: no bets supplied!"
        return None

    def update_bets(self, bets = None):
        """returns a LIST of bet info if all bets were updated, otherwise an error code.
        bets[] is a LIST of bets. Each bet should be a Dictionary of parameters:
            # betId,
            # oldPrice, newPrice,
            # oldSize, newSize,
            # oldBetPersistenceType, newBetPersistenceType
        see place_bets() function for more info.
        *** NOTE ***
        * Betfair API 6 Manual states:
        * Warning: If newPrice AND newSize are both specified, the newSize
          value is ignored.
        * For example, a bet is placed for size 100 at odds 1.5.
        * UpdateBets is called with newSize = 200, newPrice = 2.0.
        * The original bet will be cancelled and a new bet will be placed for
          100 at odds of 2.0.
        """
        if bets:
            req_xml = self.templates[self.exchange]["updateBets"]
            temp = ""
            for bet in bets:
                # are we trying to change size AND price?
                if (bet["oldPrice"] != bet["newPrice"]
                    and bet["oldSize"] != bet["newSize"]):
                    # update size first, then price
                    bet1 = bet.copy()
                    bet1["newPrice"] = bet1["oldPrice"]
                    resp1 = self.update_bets([bet1])
                    bet2 = bet.copy()
                    bet2["oldSize"] = bet2["newSize"]
                    resp2 = self.update_bets([bet2])
                    return (resp1, resp2)
                else:
                    temp += "<UpdateBets>\n"
                    temp += "<betId>" + bet["betId"] + "</betId>\n"
                    temp += "<oldPrice>" + bet["oldPrice"] + "</oldPrice>\n"
                    temp += "<newPrice>" + bet["newPrice"] + "</newPrice>\n"
                    temp += "<oldSize>" + bet["oldSize"] + "</oldSize>\n"
                    temp += "<newSize>" + bet["newSize"] + "</newSize>\n"
                    temp += "<oldBetPersistenceType>" \
                        + bet["oldBetPersistenceType"] \
                        + "</oldBetPersistenceType>\n"
                    temp += "<newBetPersistenceType>" \
                        + bet["newBetPersistenceType"] \
                        + "</newBetPersistenceType>\n"
                    temp += "</UpdateBets>\n"
            if temp:
                req_xml = self.set_value(req_xml, "<bets>", temp, "</bets>")
                resp_xml = self.__send_request(False, req_xml, "updateBets")
                resp_code = self.get_value(resp_xml,
                    "UpdateBetsErrorEnum'>", "</")
                if resp_code == "OK":
                    # parse bet ids
                    results_array = self.get_value(resp_xml,
                        "<betResults xsi:type='n2:ArrayOfUpdateBetsResult'>",
                        "</betResults>")
                    results = results_array.split("</n2:UpdateBetsResult>")
                    temp = []
                    for result in results:
                        bet_id = self.get_value(result, "<betId xsi:type='xsd:long'>", "</betId>")
                        new_bet_id = self.get_value(result, "<newBetId xsi:type='xsd:long'>", "</newBetId>")
                        size_cancelled = self.get_value(result, "<sizeCancelled xsi:type='xsd:double'>",
                            "</sizeCancelled>")
                        new_size = self.get_value(result, "<newSize xsi:type='xsd:double'>", "</newSize>")
                        new_price = self.get_value(result, "<newPrice xsi:type='xsd:double'>", "</newPrice>")
                        code = self.get_value(result, "<resultCode xsi:type='n2:UpdateBetsResultEnum'>",
                            "</resultCode>")
                        success = self.get_value(result, "<success xsi:type='xsd:boolean'>", "</success>")
                        if bet_id:
                            temp.append({
                                "old_bet_id": bet_id,
                                "new_bet_id": new_bet_id,
                                "size_cancelled": size_cancelled,
                                "new_size": new_size,
                                "new_price": new_price,
                                "code": code,
                                "success": success
                                })
                    return temp
                else:
                    if resp_code == "API_ERROR":
                        resp_code += ": " + self.get_value(resp_xml,
                            "<errorCode xsi:type='n2:APIErrorEnum'>",
                            "</errorCode>")
                    elif resp_code == '':
                        resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
                return resp_code
        else:
            return "update_bets() ERROR: no bets supplied!"
        return None

    def cancel_bets(self, bet_ids = None):
        """cancels bets on a SINGLE market.
        bet_ids = a list[] of bet id numbers as returned by get_mu_bets()
        """
        if bet_ids:
            if len(bet_ids) <= 40:
                req_xml = self.templates[self.exchange]["cancelBets"]
                ids = ""
                for bid in bet_ids:
                    ids += "<CancelBets><betId>" + bid \
                        + "</betId></CancelBets>\n"
                req_xml = self.set_value(req_xml, "<bets>\n", ids, "</bets>")
                resp_xml = self.__send_request(False, req_xml, "cancelBets")
                resp_code = self.get_value(resp_xml,
                    "CancelBetsErrorEnum'>", "</")
                if resp_code == "API_ERROR":
                    resp_code += ": " + self.get_value(resp_xml,
                        "<errorCode xsi:type='n2:APIErrorEnum'>",
                        "</errorCode>")
                elif resp_code == '':
                    resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
                return resp_code
            else:
                return "ERROR: too many bet ids! (max = 40)"
        else:
            return "ERROR: no bet ids specified!"
        return None

    @throttle
    def get_mu_bets(self, market_id = "0", status = "MU",
        order_by = "PLACED_DATE", sort_order = "ASC",
        record_count = "200", start_record = "0"):
        """return all current matched/unmatched bets as a LIST.
        * market_id = market id OR "0"
        * status = "M", "U" or "MU"
        * order_by = "NONE", "BET_ID", "PLACED_DATE" or "MATCHED_DATE"
        * sort_order = "ASC" or "DESC"
        * record_count = (string) integer. Number of records to return.
          200 is maximum limit.
        * start_record = (string) integer. Start record. Count starts at zero.
        """
        if market_id:
            req_xml = self.templates[self.exchange]["getMUBets"]
            # remove none-mandatory fields (can be implemented if REALLY needed)
            req_xml = self.remove_string(req_xml, "<betIds>", "</betIds>\n")
            req_xml = self.remove_string(req_xml, "<matchedSince>", "</matchedSince>\n")
            req_xml = self.remove_string(req_xml, "<excludeLastSecond>", "</excludeLastSecond>\n")
            # set values
            req_xml = self.set_value(req_xml, "<marketId>", market_id, "</marketId>")
            req_xml = self.set_value(req_xml, "<betStatus>", status, "</betStatus>")
            req_xml = self.set_value(req_xml, "<orderBy>", order_by, "</orderBy>")
            req_xml = self.set_value(req_xml, "<sortOrder>", sort_order, "</sortOrder>")
            req_xml = self.set_value(req_xml, "<recordCount>", record_count, "</recordCount>")
            req_xml = self.set_value(req_xml, "<startRecord>", start_record, "</startRecord>")
            # get response
            resp_xml = self.__send_request(False, req_xml, "getMUBets")
            resp_code = self.get_value(resp_xml, "GetMUBetsErrorEnum'>", "</")
            if resp_code == "OK":
                # loop through bets and build return
                bets_list = []
                resp_xml = self.get_value(resp_xml, "ArrayOfMUBet'>", "</bets>")
                bets = resp_xml.split("</n2:MUBet>")[:-1]
                for bet in bets:
                    temp = {} # reset
                    fields = bet.split("</")[:-1]
                    for field in fields:
                        key = field.rpartition("<")[2].partition(" ")[0]
                        val = field.rpartition(">")[2]
                        if key:
                            # convert values to floats
                            if key in ["price", "size", "bspLiability", "handicap"]:
                                val = float(val)
                            temp[key] = val
                    bets_list.append(temp)
                return bets_list
            else:
                if resp_code == "API_ERROR":
                    resp_code += ": " + self.get_value(resp_xml,
                        "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
                elif resp_code == '':
                    resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
            return resp_code
        else:
            return "ERROR: market_id should be a string integer. market_id given = " + market_id

    def get_market_profit_and_loss(self, market_id = ""):
        """returns P&L for given market"""
        if market_id:
            req_xml = self.templates[self.exchange]["getMarketProfitAndLoss"]
            # NOTE: <marketID> for this call but <marketId> for all others!!
            req_xml = self.set_value(req_xml, "<marketID>", market_id, "</marketID>")
            req_xml = self.remove_string(req_xml, "<locale>", "</locale>\n")
            resp_xml = self.__send_request(False, req_xml, "getMarketProfitAndLoss")
            resp_code = self.get_value(resp_xml,
                "GetMarketProfitAndLossErrorEnum'>", "</")
            if resp_code == "OK":
                # parse P&L info
                pl_list = []
                tmp = self.get_value(resp_xml,
                    "<annotations xsi:type='n2:ArrayOfProfitAndLoss'>",
                    "</annotations>")
                for pnl in tmp.split("</n2:ProfitAndLoss>")[:-1]:
                    temp = {'marketId': market_id} # reset
                    fields = pnl.split("</")[:-1]
                    for field in fields:
                        key = field.rpartition("<")[2].partition(" ")[0]
                        val = field.rpartition(">")[2]
                        if key:
                            if key == 'ifWin':
                                val = float(val)
                            if key == 'ifLoss':
                                val = float(val)
                            temp[key] = val
                    pl_list.append(temp)
                return pl_list
            else:
                if resp_code == "API_ERROR":
                    resp_code += ": " + self.get_value(resp_xml,
                        "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
                elif resp_code == '':
                    resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
                return resp_code

    def __get_bet_history(self, bet_types_included = "S", detailed = "false",
        event_type_ids = None, market_types_included = None,
        placed_date_from = None, placed_date_to = None,
        sort_bets_by = "PLACED_DATE", start_record = "0", market_id = ""):
        """returns a 2 part dict. Key ["total_record_count"] displays the total
        number of records found for the query and should be used for paging
        the results (maximum is 100 records per page). Key ["bets"] is a list of
        bets, each bet being a dictionary of fields.
        * bet_types_included: C = Cancelled, L = Lapsed, M = Matched,
            MU = Matched and Unmatched, S = Settled, U = Unmatched.
        * detailed: "true" or "false". Whether to show details of all the
            matches on a single bet.
        * event_type_ids: [list] of event types.
        * market_types_included: [list] of market types.
            A = Asian Handicap, L = Line, O = Odds, R = Range,
            NOT_APPLICABLE = The market does not have a market type.
        * placed_date_from: datetime object. Return records for bets on or after
            this date.
        * placed_date_to: datetime object. Return records for bets on or before
            this date.
        * sort_bets_by: "BET_ID" = Order by Bet ID, "CANCELLED_DATE" = Order by
            Cancelled Date, "MARKET_NAME" = Order by Market Name,
            "MATCHED_DATE" = Order by Matched Date, "NONE" = Default order,
            "PLACED_DATE" = Order by Placed Date.
        * start_record: string integer. The first record number to return
            (supports paging). Record numbering starts from 0. For example, to
            retrieve the third record and higher, set startRecord to "2".
        * market_id: (optional), set as "0" if unused.
        """
        # check if input parameters are set
        gmt_now = datetime.datetime.utcnow()
        if market_id:
            event_type_ids = "" # must be blank if marketId is specified
        else:
            market_id = "0"
            if type(event_type_ids) is not list:
                return "ERROR: event_type_ids should be a list!"
        if type(market_types_included) is not list:
            return "ERROR: market_types_included should be a list!"
        if type(placed_date_from) is not datetime.datetime:
            return "ERROR: placed_date_from must be specified."
        if type(placed_date_to) is not datetime.datetime:
            return "ERROR: placed_date_to must be specified."
        # build xml request string
        req_xml = self.templates[self.exchange]["getBetHistory"]
        req_xml = self.remove_string(req_xml, "<locale>", "</locale>\n")
        req_xml = self.remove_string(req_xml, "<timezone>", "</timezone>\n")
        req_xml = self.set_value(req_xml, "<betTypesIncluded>",
            bet_types_included, "</betTypesIncluded>")
        req_xml = self.set_value(req_xml, "<detailed>", detailed, "</detailed>")
        temp = "\n"
        for event_id in event_type_ids:
            temp += "<int>" + str(event_id) + "</int>\n"
        req_xml = self.set_value(req_xml, "<eventTypeIds>", temp,
            "</eventTypeIds")
        temp = "\n"
        for market_type in market_types_included:
            temp += "<MarketTypeEnum>" + market_type + "</MarketTypeEnum>\n"
        req_xml = self.set_value(req_xml, "<marketTypesIncluded>", temp,
            "</marketTypesIncluded>")
        # (set dates)
        from_date = placed_date_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        to_date = placed_date_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        req_xml = self.set_value(req_xml, "<placedDateFrom>", from_date,
            "</placedDateFrom>")
        req_xml = self.set_value(req_xml, "<placedDateTo>", to_date,
            "</placedDateTo>")
        # (record sorting/counts)
        req_xml = self.set_value(req_xml, "<recordCount>", '100',
            "</recordCount>") # (max No. of records to return)
        req_xml = self.set_value(req_xml, "<sortBetsBy>", sort_bets_by,
            "</sortBetsBy>")
        req_xml = self.set_value(req_xml, "<startRecord>", str(start_record),
            "</startRecord>")
        req_xml = self.set_value(req_xml, "<marketId>", str(market_id),
            "</marketId>")
        # send request
        resp_xml = self.__send_request(False, req_xml, "getBetHistory")
        resp_code = self.get_value(resp_xml, "GetBetHistoryErrorEnum'>", "</")
        if resp_code == "OK":
            # parse response
            total_record_count = int(self.get_value(resp_xml,
                "<totalRecordCount xsi:type='xsd:int'>", "</totalRecordCount>"))
            history = self.get_value(resp_xml,
                "<betHistoryItems xsi:type='n2:ArrayOfBet'>",
                "</betHistoryItems>")
            bets = history.split("</n2:Bet>")[:-1]
            records = {'total_record_count': total_record_count, 'bets': []}
            for bet in bets:
                bet = bet.replace("<n2:Bet xsi:type='n2:Bet'>", "")
                fields = bet.split("</")[:-1]
                temp = {}
                for field in fields:
                    key = self.get_value(field, "<", " ")
                    val = field.rpartition(">")[2]
                    temp[key] = val
                records['bets'].append(temp)
            return records
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
        return resp_code

    def get_bet_history(self, bet_types_included = "S", detailed = "false",
        event_type_ids = None, market_types_included = None,
        placed_date_from = None, placed_date_to = None,
        sort_bets_by = "PLACED_DATE", start_record = "0", market_id = ""):
        """This is the public function and wraps __get_bet_history() in order to
        loop through multiple pages. The GetBetHistory API can only return 100
        records per request. Note that __get_bet_history() will be called
        multiple times, returning 100 records on each request"""
        records = self.__get_bet_history(bet_types_included, detailed,
            event_type_ids, market_types_included, placed_date_from,
            placed_date_to, sort_bets_by, start_record, market_id)
        if type(records) is dict:
            # do we need to request multiple pages?
            if records['total_record_count'] > 100:
                page_count = records['total_record_count'] / 100 + 1
                for page in xrange(1, page_count):
                    start_record = page * 100
                    temp = self.__get_bet_history(bet_types_included, detailed,
                        event_type_ids, market_types_included, placed_date_from,
                        placed_date_to, sort_bets_by, start_record, market_id)
                    if type(temp) is dict:
                        # add the new bets to existing list
                        records['bets'] += temp['bets']
                    # throttle request speed
                    if self.free_api:
                        sleep(60) # free api = 1 request per min
                    else:
                        sleep(0.1) # limit to approx 10 calls per second
            return records
        elif records == 'NO_RESULTS':
            return records
        else:
            return "ERROR in get_bet_history(): type(records) is not a dict..." + str(records)

    def get_account_statement(self, start_date = None, end_date = None):
        """get account statement/history.
        * start_date and end_date = datetime objects.
        * start_record = first record number to return.
        NOTE:
        This API function appears to be very buggy at Betfair's end. Main issues
        are that recordCount is ignored and startDate/endDate are ignored if
        itemsIncluded = EXCHANGE. All in all, pretty disappointing as this
        function is useful for checking settled bets with commission deducted.
        GetBetHistory will only return gross profit and gives no indication of
        how much commission we need to deduct.
        Due to the above issues, this function has been limited to take ONLY
        the startDate and endDate parameters.
        """
        # check input values
        gmt_now = datetime.datetime.utcnow()
        if type(start_date) is not datetime.datetime:
            return "ERROR in get_account_statement(): start_date must be a datetime object."
        if type(end_date) is not datetime.datetime:
            return "ERROR in get_account_statement(): end_date must be a datetime object."
        # create request xml
        req_xml = self.templates[self.exchange]["getAccountStatement"]
        req_xml = self.remove_string(req_xml, "<locale>", "</locale>\n")
        from_date = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        to_date = end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        req_xml = self.set_value(req_xml, "<startDate>", from_date, "</startDate>")
        req_xml = self.set_value(req_xml, "<endDate>", to_date, "</endDate>")
        req_xml = self.set_value(req_xml, "<startRecord>", "0", "</startRecord>")
        req_xml = self.set_value(req_xml, "<recordCount>", "99999", "</recordCount>")
        req_xml = self.set_value(req_xml, "<itemsIncluded>", "ALL", "</itemsIncluded>")
        req_xml = self.set_value(req_xml, "<ignoreAutoTransfers>", "false", "</ignoreAutoTransfers>")
        # send request
        resp_xml = self.__send_request(False, req_xml, "getAccountStatement")
        resp_code = self.get_value(resp_xml, "GetAccountStatementErrorEnum'>", "</")
        if resp_code == "OK":
            # parse response
            history = self.get_value(resp_xml,
                "<items xsi:type='n2:ArrayOfAccountStatementItem'>",
                "</items>")
            items = history.split("</n2:AccountStatementItem>")[:-1]
            records = []
            for item in items:
                item = item.replace("<n2:AccountStatementItem xsi:type='n2:AccountStatementItem'>", "")
                fields = item.split("</")[:-1]
                temp = {}
                for field in fields:
                    key = self.get_value(field, "<", " ")
                    val = field.rpartition(">")[2]
                    temp[key] = val
                records.append(temp)
            return records
        else:
            if resp_code == "API_ERROR":
                resp_code += ": " + self.get_value(resp_xml,
                    "<errorCode xsi:type='n2:APIErrorEnum'>", "</errorCode>")
            elif resp_code == '':
                resp_code = "SERVER_RESPONSE_ERROR: Response XML = " + resp_xml
        return resp_code

    def get_value(self, xml = "", start_tag = "", end_tag = ""):
        """returns the substring from between start_tag and end_tag"""
        part = xml.partition(start_tag)[2]
        return part.partition(end_tag)[0]

    def set_value(self, xml = "", start_tag = "", value = "", end_tag = ""):
        """inserts a substring between start_tag and end_tag
        any existing substring will be overwritten
        """
        try:
            pos1 = xml.index(start_tag) + len(start_tag)
            pos2 = xml.index(end_tag, pos1)
            return xml[:pos1] + value + xml[pos2:]
        except:
            return "" # tags not found
        return None

    def remove_string(self, xml, start_tag = "", end_tag = ""):
        """removes the substring from start_tag to end_tag
        start_tag and end_tag are also removed
        """
        return xml.partition(start_tag)[0] + xml.partition(end_tag)[2]

    def __make_templates(self):
        """builds the XML request templates from the remote WSDL files
        NOTES: * requires gSOAP installed
               * standard gSoap doesn't support HTTPS, so we download the
                 WSDL file first
               * you ONLY need to call this function when the WSDL changes
               * can be replaced by external script or command lines
        """
        # create the templates folder
        file_path = self.abs_path + "/templates/"
        if not os.path.exists(file_path): os.mkdir(file_path)
        # build service files
        urls = {
            "global": "https://api.betfair.com/global/v3/BFGlobalService.wsdl",
            "uk": "https://api.betfair.com/exchange/v5/BFExchangeService.wsdl",
            "aus": "https://api-au.betfair.com/exchange/v5/BFExchangeService.wsdl"
            }
        for key in urls:
            # create sub folder
            fp = file_path + key + "/"
            if not os.path.exists(fp): os.mkdir(fp)
            # get wsdl xml source + save to file
            xml = self.http.send_http_request(urls[key])
            fn = urls[key].rpartition("/")[2].partition(".")[0] # file name
            open(fp + fn + ".wsdl", "w").write(xml)
            # build the service files using gSoap tools
            cmd = "wsdl2h -s -o " + fp + fn + ".h " + fp + fn + ".wsdl"
            os.system(cmd) # builds a C++ header file
            cmd = "soapcpp2 -i -C -d " + fp + " " + fp + fn + ".h"
            os.system(cmd) # builds C++ stubs
            # save only the request xml files
            for fn in os.listdir(fp):
                if not fn.endswith(".req.xml"):
                    os.remove(fp + fn)
                else:
                    # tidy up XML
                    xml = open(fp + fn, "r").read()
                    xml = xml.replace(" ", "")
                    xml = xml.replace("\n\n", "\n")
                    xml = xml.replace("\"", "'")
                    # insert soap header (gSoap omits it?)
                    header = "<header>\n<sessionToken></sessionToken>\n</header>"
                    xml = xml.replace("<ns1:request>", "<ns1:request>\n" + header)
                    xml = xml.replace("<ns1:req>", "<ns1:req>\n" + header)
                    # save to templates folder
                    open(fp + fn, "w").write(xml)

    def __load_templates(self):
        """loads the raw XML templates/strings into a static Dictionary
        * look-up Key is the equivalent "Soap Action" string
        * memory footprint is low - loading EVERY request is less than 80KB
        """
        root_path = self.abs_path + "/templates/"
        if os.path.exists(root_path):
            for folder in os.listdir(root_path):
                if self.templates.has_key(folder):
                    fp = root_path + folder + "/"
                    for file_name in os.listdir(fp):
                        if file_name.endswith(".req.xml"):
                            soap_action = file_name.split(".")[1]
                            xml = open(fp + file_name, "r").read()
                            self.templates[folder][soap_action] = xml
        else:
            # templates do not exist so build them!
            self.__make_templates()
            self.__load_templates()


