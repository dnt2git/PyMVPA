# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generators for dataset resampling."""

__docformat__ = 'restructuredtext'

import random

import numpy as np

from mvpa2.base.node import Node
from mvpa2.base.collections import \
     SampleAttributesCollection, FeatureAttributesCollection
from mvpa2.base.dochelpers import _str, _repr

if __debug__:
    from mvpa2.base import debug

class Repeater(Node):
    """Node that yields the same dataset for a certain number of repetitions.

    Each yielded dataset has a dataset attribute that identifies the iteration
    (see the ``space`` setting).
    """

    def __init__(self, count, space='repetitons', **kwargs):
        """
        Parameters
        ----------
        count : int
          Positive integer that set the numbed of repetitions.
        space : str
          The name of the dataset attribute that will hold the actual repetiton
          in the yielded datasets.
        """
        Node.__init__(self, space=space, **kwargs)
        self.nruns = count


    def generate(self, ds):
        """Generate the desired number of repetitions."""
        space = self.get_space()
        for i in xrange(self.nruns):
            out = ds.copy(deep=False)
            out.a[space] = i
            yield out


    def __str__(self):
        return _str(self, str(self.nruns))


class Sifter(Node):
    """Exclude (do not generate) provided dataset on the values of the attributes.

    Example
    -------

    Typical usecase: it is necessary to generate all possible
    combinations of two chunks while being interested only in the
    combinations where both targets are present.

    >>> from mvpa2.datasets import Dataset
    >>> from mvpa2.generators.partition import NFoldPartitioner
    >>> from mvpa2.base.node import ChainNode
    >>> ds = Dataset(samples=np.arange(8).reshape((4,2)),
    ...              sa={'chunks':   [ 0 ,  1 ,  2 ,  3 ],
    ...                  'targets':  ['c', 'c', 'p', 'p']})

    Plain 'NFoldPartitioner(cvtype=2)' would provide also partitions
    with only two 'c's or 'p's present, which we do not want to
    include in our cross-validation since it would break balancing
    between training and testing sets.

    >>> par = ChainNode([NFoldPartitioner(cvtype=2, attr='chunks'),
    ...                  Sifter([('partitions', 2),
    ...                          ('targets', ['c', 'p'])])
    ...                 ], space='partitions')

    We have to provide appropriate 'space' parameter for the
    'ChainNode' so possible future splitting using 'TransferMeasure'
    could operate along that attribute.  Here we just matched default
    space of NFoldPartitioner -- 'partitions'.

    >>> print par
    <ChainNode: <NFoldPartitioner>-<Sifter: partitions=2, targets=['c', 'p']>>
    >>> for ds_ in par.generate(ds):
    ...     testing = ds[ds_.sa.partitions == 2]
    ...     print list(zip(testing.sa.chunks, testing.sa.targets))
    [(0, 'c'), (2, 'p')]
    [(0, 'c'), (3, 'p')]
    [(1, 'c'), (2, 'p')]
    [(1, 'c'), (3, 'p')]

    """
    def __init__(self, includes, *args, **kwargs):
        """
        Parameters
        ----------
        includes : list
          List of tuples rules (attribute, unique_values) where all
          listed 'unique_values' must be present in the dataset.
          Matching samples or features get selected to proceed to the
          next rule in the list.  If at some point not all listed
          values of the attribute are present, dataset does not pass
          through the 'Sifter'.
        """
        Node.__init__(self, *args, **kwargs)
        self._includes = includes

    def generate(self, ds):
        """Validate obtained dataset and yield if matches
        """
        # we  start by considering all samples
        sa_mask = np.ones(ds.nsamples, dtype=bool)
        fa_mask = np.ones(ds.nfeatures, dtype=bool)
        # Check the dataset against the rules
        for attrname, uvalues in self._includes:
            # just to assure consistency in order and type
            uvalues = np.unique(np.atleast_1d(uvalues))
            attr, col = ds.get_attr(attrname)

            # figure out which mask and adjust accordingly
            if isinstance(col, SampleAttributesCollection):
                mask = sa_mask
            elif isinstance(col, FeatureAttributesCollection):
                mask = fa_mask
            else:
                raise ValueError(
                    "%s cannot filter based on attribute %s=%s -- "
                    "only collections from .sa or .fa are supported."
                    % (self, attrname, attr))

            uvalues_ = np.unique(attr[mask])

            # do matching and reset those not matching
            mask[np.array([not a in uvalues for a in attr.value])] = False

            # exit if resultant attributes do no match
            uvalues_selected = np.unique(attr[mask])
            #if 'control' in uvalues:
            #    raise ValueError
            if not (np.all(uvalues_selected == uvalues) and len(uvalues_selected)):
                if __debug__ and 'SPL' in debug.active:
                    debug('SPL',
                          'Skipping dataset %s because selection using %s '
                          'attribute resulted in the set of values %s while '
                          'needing %s'
                          % (ds, attrname, uvalues_selected, uvalues))
                return
            # print attrname, attr.value, uvalues, uvalues_selected, mask

        yield ds

    def __str__(self):
        return _str(self, ', '.join("%s=%s" % x for x in self._includes))
