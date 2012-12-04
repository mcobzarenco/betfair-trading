from __future__ import print_function, division

from collections import defaultdict

import numpy as np
from numpy import array, argmax, repeat, sqrt, empty, argsort
from scipy import randn
from scipy.stats import norm

from trueskill import Rating, rate


def pwin_1vs1(r1, r2):
    mu = r2.mu - r1.mu
    sigma = sqrt(r1.sigma**2 + r2.sigma**2)
    return norm.cdf(0, loc=mu, scale=sigma)


def pwin_1vs1_mc(r1, r2):
    N = 10000
    r1s = randn(N) * r1.sigma + r1.mu
    r2s = randn(N) * r2.sigma + r2.mu
    return float(sum(r1s > r2s)) / N

def pwin_mc(rs):
    N = 10000
    rss = [randn(N) * rs[i].sigma + rs[i].mu for i in range(len(rs))]
    wins = []
    for i in range(len(rs)):
        r = reduce(lambda x, y: x & (rss[i] > y), rss[:i] + rss[i+1:], array([True]*N))
        wins.append(float(sum(r)) / N)
    return wins


class HorseModel(object):
    def __init__(self):
        pass


    def fit(self, sorted_games):
        ratings = defaultdict(lambda: {'rating': (Rating(),), 'n_games': 0, 'n_wins': 0})
        stats = {'n_games':0}

        curr_game = 0
        for game in sorted_games:
            winners = game['winners']
            if winners is None:
                continue

            runners = list(game['selection'])
            if len(runners) < 2:
                continue

            stats['n_games'] += 1
            rating_groups = [ratings[r]['rating'] for r in runners]
            ranks = [int(r not in winners) for r in runners]
            new_ratings = rate(rating_groups, ranks)
            assert len(new_ratings) == len(runners)
            for i, runner in enumerate(runners):
                rating = ratings[runner]
                rating['rating'] = new_ratings[i]
                rating['n_games'] += 1
                if runner in winners:
                    rating['n_wins'] += 1

            curr_game+= 1
            if curr_game % 1000 == 0:
                print('%d games done.' % curr_game)

        stats['n_runners'] = len(ratings)
        self._ratings = ratings

        return stats


    def pwin(self, runners, nwins=1, prior_for_unobs=True):
        assert(prior_for_unobs)
        N = 10000
        R = empty((len(runners), N))
        for i, r in enumerate(self.get_ratings(runners)):
            R[i, :] = randn(N) * r.sigma + r.mu

        for i in xrange(N):
            ar = argsort(-array(R[:, i])).tolist()
            R[:, i] = [ar.index(x) for x in range(len(ar))]
        return np.sum(R < nwins, 1) / float(N)


    def as_dict(self):
        if not hasattr(self, '_ratings'):
            return []
        items = self._ratings.items()
        dicts = map(lambda x: {'runner': x[0], 'mu': x[1]['rating'][0].mu, 'sigma': x[1]['rating'][0].sigma,
                               'n_wins': x[1]['n_wins'], 'n_games': x[1]['n_games']}, items)
        return dicts


    def get_ratings(self, runners):
        return [self._ratings[x]['rating'][0] for x in runners]




    #ms = c.get_all_markets(hours=24, countries=['GBR'])
    #predicates = lambda x: x['menu_path'].startswith('\\Horse Racing\\GB') and\
    #                       x['market_name'].lower() == 'to be placed'
    #len(filter(predicates, ms))