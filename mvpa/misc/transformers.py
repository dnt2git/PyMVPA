#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Simply functors that transform something."""

__docformat__ = 'restructuredtext'


import numpy as N

from mvpa.base import externals

if __debug__:
    from mvpa.base import debug


def Absolute(x):
    """Returns the elementwise absolute of any argument."""
    return N.absolute(x)


def OneMinus(x):
    """Returns elementwise '1 - x' of any argument."""
    return 1 - x


def Identity(x):
    """Return whatever it was called with."""
    return x


def FirstAxisMean(x):
    """Mean computed along the first axis."""
    return N.mean(x, axis=0)


def SecondAxisMean(x):
    """Mean across 2nd axis

    Use cases:
     - to combine multiple sensitivities to get sense about
       mean sensitivity across splits
    """
    return N.mean(x, axis=1)


def SecondAxisSumOfAbs(x):
    """Sum of absolute values along the 2nd axis

    Use cases:
     - to combine multiple sensitivities to get sense about
       what features are most influential
    """
    return N.abs(x).sum(axis=1)


def SecondAxisMaxOfAbs(x):
    """Max of absolute values along the 2nd axis
    """
    return N.abs(x).max(axis=1)


def GrandMean(x):
    """Just what the name suggests."""
    return N.mean(x)


def L2Normed(x, norm=1.0, reverse=False):
    """Norm the values so that regular vector norm becomes `norm`

    More verbose: Norm that the sum of the squared elements of the
    returned vector becomes `norm`.
    """
    xnorm = N.linalg.norm(x)
    return x * (norm/xnorm)

def L1Normed(x, norm=1.0, reverse=False):
    """Norm the values so that L_1 norm (sum|x|) becomes `norm`"""
    xnorm = N.sum(N.abs(x))
    return x * (norm/xnorm)


def RankOrder(x, reverse=False):
    """Rank-order by value. Highest gets 0"""

    # XXX was Yarik on drugs? please simplify this beast
    nelements = len(x)
    indexes = N.arange(nelements)
    t_indexes = indexes
    if not reverse:
        t_indexes = indexes[::-1]
    tosort = zip(x, indexes)
    tosort.sort()
    ztosort = zip(tosort, t_indexes)
    rankorder = N.empty(nelements, dtype=int)
    rankorder[ [x[0][1] for x in ztosort] ] = \
               [x[1] for x in ztosort]
    return rankorder


def ReverseRankOrder(x):
    """Convinience functor"""
    return RankOrder(x, reverse=True)


class OverAxis(object):
    """Helper to apply transformer over specific axis
    """

    def __init__(self, transformer, axis=None):
        """Initialize transformer wrapper with an axis.

        :Parameters:
          transformer
            A callable to be used
          axis : None or int
            If None -- apply transformer across all the data. If some
            int -- over that axis
        """
        self.transformer = transformer
        # sanity check
        if not (axis is None or isinstance(axis, int)):
            raise ValueError, "axis must be specified by integer"
        self.axis = axis


    def __call__(self, x, *args, **kwargs):
        transformer = self.transformer
        axis = self.axis
        if axis is None:
            return transformer(x, *args, **kwargs)

        x = N.asanyarray(x)
        shape = x.shape
        if axis >= len(shape):
            raise ValueError, "Axis given in constructor %d is higher " \
                  "than dimensionality of the data of shape %s" % (axis, shape)

        # WRONG! ;-)
        #for ind in xrange(shape[axis]):
        #    results.append(transformer(x.take([ind], axis=axis),
        #                              *args, **kwargs))

        # TODO: more elegant/speedy solution?
        shape_sweep = shape[:axis] + shape[axis+1:]
        shrinker = None
        """Either transformer reduces the dimensionality of the data"""
        #results = N.empty(shape_out, dtype=x.dtype)
        for index_sweep in N.ndindex(shape_sweep):
            if axis > 0:
                index = index_sweep[:axis]
            else:
                index = ()
            index = index + (slice(None),) + index_sweep[axis:]
            x_sel = x[index]
            x_t = transformer(x_sel, *args, **kwargs)
            if shrinker is None:
                if N.isscalar(x_t) or x_t.shape == shape_sweep:
                    results = N.empty(shape_sweep, dtype=x.dtype)
                    shrinker = True
                elif x_t.shape == x_sel.shape:
                    results = N.empty(x.shape, dtype=x.dtype)
                    shrinker = False
                else:
                    raise RuntimeError, 'Not handled by OverAxis kind of transformer'

            if shrinker:
                results[index_sweep] = x_t
            else:
                results[index] = x_t

        return results


def DistPValue(x, sd=0, distribution='rdist', fpp=None, nbins=400):
    """L2-Norm the values, convert them to p-values of a given distribution.

    :Parameters:
      x
        Data to operate on
      sd : int
        Samples dimension (if len(x.shape)>1) on which to operate
      distribution : string
        Which distribution to use. Known are: 'rdist' (later normal should
        be there as well)
      fpp : float
        At what p-value (both tails) if not None, to control for false
        positives. It would iteratively prune the tails (tentative real positives)
        until empirical p-value becomes less or equal to numerical.
      nbins : int
        Number of bins for the iterative pruning of positives

    WARNING: Highly experimental/slow/etc: no theoretical grounds have been
    presented in any paper, nor proven
    """
    externals.exists('scipy', raiseException=True)

    from mvpa.support.stats import scipy
    import scipy.stats as stats

    if not (distribution in ['rdist']):
        raise ValueError, "Actually only rdist supported at the moment" \
              " got %s" % distribution

    x = N.asanyarray(x)
    shape_orig = x.shape
    ndims = len(shape_orig)

    # XXX May be just utilize OverAxis transformer?
    if ndims > 2:
        raise NotImplementedError, \
              "TODO: add support for more than 2 dimensions"
    elif ndims == 1:
        x, sd = x[:, N.newaxis], 0

    # lets transpose for convenience
    if sd == 0: x = x.T


    # Output p-values of x in null-distribution
    pvalues = N.zeros(x.shape)
    # finally go through all data
    nd = x.shape[1]
    dist = stats.rdist(nd-1, 0, 1)
    for i, xx in enumerate(x):
        xx /= N.linalg.norm(xx)

        if fpp is not None:
            # Adaptive adjustment for false negatives:
            Nxx, xxx, pN_emp_prev = len(xx), xx, 1.0
            indexes = N.arange(Nxx)
            """What features belong to Null-distribution"""
            while True:
                Nxxx = len(xxx)
                dist = stats.rdist(Nxxx-1, 0, 1)

                Nhist = N.histogram(xxx, bins=nbins, normed=False)
                pdf = Nhist[0].astype(float)/Nxxx
                bins = Nhist[1]
                bins_halfstep = (bins[1] - bins[2])/2.0

                # theoretical CDF
                # was really unstable -- now got better ;)
                dist_cdf = dist.cdf(bins)

                # otherwise just recompute manually
                # dist_pdf = dist.pdf(bins)
                # dist_pdf /= N.sum(dist_pdf)

                # XXX can't recall the function... silly
                #     probably could use N.integrate
                cdf = N.zeros(nbins, dtype=float)
                #dist_cdf = cdf.copy()
                dist_prevv = cdf_prevv = 0.0
                for j in range(nbins):
                    cdf_prevv = cdf[j] = cdf_prevv + pdf[j]
                    #dist_prevv = dist_cdf[j] = dist_prevv + dist_pdf[j]

                # what bins fall into theoretical 'positives' in both tails
                p = (0.5 - N.abs(dist_cdf - 0.5) < fpp/2.0)

                # amount in empirical tails -- if we match theoretical, we
                # should have total >= p

                pN_emp = N.sum(pdf[p]) # / (1.0 * nbins)

                if __debug__:
                    debug('TRAN_', "empirical p=%.3f for theoretical p=%.3f"
                          % (pN_emp, fpp))

                if pN_emp <= fpp:
                    # we are done
                    break

                if pN_emp > pN_emp_prev:
                    if __debug__:
                        debug('TRAN_', "Diverging -- thus keeping last result "
                              "with p=%.3f" % pN_emp_prev)
                    # we better restore previous result
                    indexes, xxx, dist = indexes_prev, xxx_prev, dist_prev
                    break

                pN_emp_prev = pN_emp
                # very silly way for now -- just proceed by 1 bin
                keep = N.logical_and(xxx > bins[0], # + bins_halfstep,
                                     xxx < bins[-1]) # - bins_halfstep)
                if __debug__:
                    debug('TRAN_', "Keeping %d out of %d elements" %
                          (N.sum(keep), Nxxx))

                # Preserve them if we need to "roll back"
                indexes_prev, xxx_prev, dist_prev = indexes, xxx, dist
                # we should remove those which we assume to be positives and
                # which should not belong to Null-dist
                xxx, indexes = xxx[keep], indexes[keep]
                # L2 renorm it
                xxx = xxx / N.linalg.norm(xxx)

            Nindexes = len(indexes)
            Nrecovered = Nxx - Nindexes

            if __debug__:
                if  distribution == 'rdist':
                    assert(dist.args[0], Nindexes)
                debug('TRAN', "Positives recovery finished with %d out of %d "
                      "entries in Null-distribution, thus %d positives "
                      "were recovered" % (Nindexes, Nxx, Nrecovered))

            # And now we need to perform our duty -- assign p-values
            #dist = stats.rdist(Nindexes-1, 0, 1)
        pvalues[i, :] = dist.cdf(xx)

    # XXX we might add an option to transform it to z-scores?
    result = pvalues

    # transpose if needed
    if sd == 0:
        result = result.T

    return result
