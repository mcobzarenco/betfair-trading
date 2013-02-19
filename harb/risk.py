from __future__ import print_function, division

import logging
import time

import numpy as np
from numpy import array, sqrt, empty, argsort, zeros, ones, log, isnan, diag_indices_from, eye, dot, inf
from scipy import rand, randn
from scipy.stats import norm
from scipy.optimize import minimize


def nwin1_bet_returns(w, odds):
    assert len(w) == len(odds)
    R = w.reshape(1, -1).repeat(len(w), 0)
    R *= eye(R.shape[0]) - 1.0
    ix = diag_indices_from(R)
    R[ix] = w * (odds - 1.0)
    return np.sum(R, 1)


def _R_matrix(p, odds):
    assert len(p) == len(odds)
    R = p.reshape(1, -1).repeat(len(p), 0)
    R *= eye(R.shape[0]) - 1.0
    ix = diag_indices_from(R)
    R[ix] = p * (odds - 1.0)
    return R


def nwin1_l2reg(p, odds, ra):
    """
    Maximise expected reutrns w.r.t. p using market implied probabilites q to compute the bet odds.
    The risk aversion ra controls the amount of L2 regularization:

        argmax_w (<R(X | w, q)>_p - ra * dot(w , w))

    :param p: model probabilties
    :param q: market implied probabilities
    :param ra: risk aversion
    """
    assert ra > 0

    R = _R_matrix(p, odds)
    r = np.sum(R, 1)
    w = r / 2 / ra

    # print(R)
    # print("r=%s" % r)
    # print("e(w) = %f" % (dot(r, w) - ra * dot(w, w)))
    # print(dot(r, w), "  ---   ", -ra * dot(w, w))
    return w
    #payoffs = np.sum(R, 1)
    #utility = np.sum(log((self.wealth + payoffs) / self.wealth) * self.p)
    #np.sum(payoffs * self.p) - 0.2 * dot(w, w)


def nwin1_log_util(p, q, wealth):
    #TODO: convert the class to a function and tidy up
    assert wealth > 0
    R = _R_matrix(p, q)

    class RiskModel2(object):
        def __init__(self, p, q, wealth=100):
            self.N = len(p)
            self.p = p
            self.q = q
            self.wealth = wealth

    def exp_utility(self, w, q=None):
        if q is None:
            q = self.q

        R = w.reshape(1, -1).repeat(self.N, 0)
        R *= eye(R.shape[0]) - 1.0
        ix = diag_indices_from(R)
        R[ix] = w * (1.0 / q - 1.0)

        payoffs = np.sum(R, 1)
        #utility = np.sum(log((self.wealth + payoffs) / self.wealth) * self.p)
        #return utility if not isnan(utility) else -inf
        return np.sum(payoffs * self.p) - 0.2 * dot(w, w)

    def optimal_w(self):
        constraints = [{'type': 'eq',
                        'fun': lambda w: sum(w * w) - 1}]
        min = minimize(lambda w: -self.exp_utility(w), zeros(self.N), method='BFGS', options={'disp': True})
        return min['x']


class RiskModel(object):
    def __init__(self, alpha, covariance, risk_aversion):
        assert covariance.shape == (len(alpha), len(alpha))
        self.N = len(alpha)
        self.a = alpha
        self.C = covariance
        self.ra = risk_aversion


    def adj_return(self, w):
        return dot(self.a, w) - self.ra * dot(dot(w, self.C), w)


    def optimal_w(self):
        constraints = [{'type': 'eq',
                        'fun': lambda w: sum(w) - 1,
                        'jac': lambda w: np.ones_like(w)}]
        min = minimize(lambda w: -self.adj_return(w), ones(self.N) / self.N, method='SLSQP', constraints=constraints)
        return min['x']



# from numpy import r_
#
# w = r_[0.0, -2.0, 2.0]
# odds = r_[3.9, 7.6, 7.8]
#
# print(nwin1_bet_returns(w, odds))


# from analytics import RiskModel2
#
# p = rand(3)
# p /= sum(p)
# q = p + randn(3) / 100
#
# print(p)
# print(q)
#
# st = time.clock()
# print(nwin1_l2reg(p, q, 0.2))
# print('exact took %.2f milisec' % ((time.clock() - st) * 1000.0))
#
# rm = RiskModel2(p, q)
# st = time.clock()
# print(rm.optimal_w())
# print('opt took %.2f milisec' % ((time.clock() - st) * 1000.0))

# odds = np.array([9.63506448,  2.53987236,  7.40156126])
# p = np.array([0.14765513,  0.5729512,  0.23492542])
#
# implied = (1.0 / odds) / np.sum(1.0 / odds)
# w = nwin1_l2reg(implied, 1.1 * 1 / implied, 0.1)
# print(implied)
# print(w)
# print(np.sum(nwin1_bet_returns(w, 0.9 * 1 / implied) * implied))

#print(nwin1_l2reg(p, .5 * odds, 0.1))