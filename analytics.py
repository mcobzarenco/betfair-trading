from __future__ import print_function, division

from collections import defaultdict

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


def pwin(rs, nwins=1):
    N = 10000
    R = empty((len(rs), N))
    for i, r in enumerate(rs):
        R[i, :] = randn(N) * r.sigma + r.mu

    for i in range(N):
        ar = argsort(-array(R[:, i])).tolist()
        R[:, i] = [ar.index(x) for x in range(len(ar))]
    return sum(R < nwins, 1) / float(N)



def fit_trueskill(sorted_games):
    ratings = defaultdict(lambda: {'rating': (Rating(),), 'n_games': 0, 'n_wins': 0})

    curr_game = 0
    for game in sorted_games:
        winners = game['winners']
        if winners is None:
            continue

        runners = list(game['selection'])
        if len(runners) < 2:
            continue

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
    return ratings


#ms = c.get_all_markets(hours=24, countries=['GBR'])
#predicates = lambda x: x['menu_path'].startswith('\\Horse Racing\\GB') and\
#                       x['market_name'].lower() == 'to be placed'
#len(filter(predicates, ms))