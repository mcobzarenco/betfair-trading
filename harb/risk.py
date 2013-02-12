from __future__ import print_function, division

import logging
import time

import numpy as np
from numpy import array, sqrt, empty, argsort, zeros, ones, log, isnan, diag_indices_from, eye, dot, inf
from scipy import rand, randn
from scipy.stats import norm
from scipy.optimize import minimize


def nwin1_l2reg(p, q, ra):
    """
    Maximise expected reutrns w.r.t. p using market implied probabilites q.
    The risk aversion ra controls the amount of L2 reguralization:

        argmax_w (<R>_p - ra * dot(w , w))

    :param p: model probabilties
    :param q: market implied probabilities
    :param ra: risk aversion
    """
    assert len(p) == len(q)
    assert ra > 0

    R = p.reshape(1, -1).repeat(len(p), 0)
    R *= eye(R.shape[0]) - 1.0
    ix = diag_indices_from(R)
    R[ix] = p * (1.0 / q - 1.0)

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


# from numpy import r_
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
