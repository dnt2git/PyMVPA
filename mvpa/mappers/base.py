# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Data mapper"""

__docformat__ = 'restructuredtext'

import numpy as N

from mvpa.base.types import is_datasetlike

from mvpa.mappers.metric import Metric

from mvpa.misc.vproperty import VProperty
from mvpa.base.dochelpers import enhancedDocString

if __debug__:
    from mvpa.base import warning
    from mvpa.base import debug


def accepts_dataset_as_samples(fx):
    """Decorator to extract samples from Datasets.

    Little helper to allow methods to be written for plain data (if they
    don't need information from a Dataset), but at the same time also
    accept whole Datasets as input.
    """
    def extract_samples(obj, data):
        if is_datasetlike(data):
            return fx(obj, data.samples)
        else:
            return fx(obj, data)
    return extract_samples


class Mapper(object):
    """Interface to provide mapping between two spaces: IN and OUT.
    Methods are prefixed correspondingly. forward/reverse operate
    on the entire dataset. get(In|Out)Id[s] operate per element::

              forward
             --------->
         IN              OUT
             <--------/
               reverse
    """
    def __init__(self, metric=None, inspace=None):
        """
        :Parameters:
          metric : Metric
            Optional metric
        """
        self.__metric = None
        self.__inspace = inspace
        """Pylint happiness"""
        self.setMetric(metric)
        """Actually assign the metric"""

    #
    # The following methods are abstract and merely define the intended
    # interface of a mapper and have to be implemented in derived classes. See
    # the docstrings of the respective methods for details about what they
    # should do.
    #

    def forward(self, data):
        """Map data from input to output space.

        Parameters
        ----------
        data: Dataset-like, anything
          Typically this is a `Dataset`, but it might also be a plain data
          array, or even something completely different(TM) that is supported
          by a subclass' implementation. If such an object is Dataset-like it
          is handled by a dedicated method that also transforms dataset
          attributes if necessary.
        """
        if is_datasetlike(data):
            return self._forward_dataset(data)
        else:
            return self._forward_data(data)


    def _forward_data(self, data):
        """Forward-map some data.

        This is a private method that has to be implemented in derived
        classes.

        Parameters
        ----------
        data : anything (supported the derived class)
        """
        raise NotImplementedError


    def _forward_dataset(self, dataset):
        """Forward-map a dataset.

        This is a private method that can be reimplemented in derived
        classes. The default implementation forward-maps the dataset samples
        and returns a new dataset that is a shallow copy of the input with
        the mapped samples.

        Parameters
        ----------
        dataset : Dataset-like
        """
        msamples = self._forward_data(dataset.samples)
        mds = dataset.copy(deep=False)
        mds.samples = msamples
        return mds


    def reverse(self, data):
        """Reverse-map data from output back into input space.

        Parameters
        ----------
        data: Dataset-like, anything
          Typically this is a `Dataset`, but it might also be a plain data
          array, or even something completely different(TM) that is supported
          by a subclass' implementation. If such an object is Dataset-like it
          is handled by a dedicated method that also transforms dataset
          attributes if necessary.
        """
        if is_datasetlike(data):
            return self._reverse_dataset(data)
        else:
            return self._reverse_data(data)


    def _reverse_data(self, data):
        """Reverse-map some data.

        This is a private method that has to be implemented in derived
        classes.

        Parameters
        ----------
        data : anything (supported the derived class)
        """
        raise NotImplementedError


    def _reverse_dataset(self, dataset):
        """Reverse-map a dataset.

        This is a private method that can be reimplemented in derived
        classes. The default implementation reverse-maps the dataset samples
        and returns a new dataset that is a shallow copy of the input with
        the mapped samples.

        Parameters
        ----------
        dataset : Dataset-like
        """
        msamples = self._reverse_data(dataset.samples)
        mds = dataset.copy(deep=False)
        mds.samples = msamples
        return mds


    def get_insize(self):
        """Returns the size of the entity in input space"""
        raise NotImplementedError


    def get_outsize(self):
        """Returns the size of the entity in output space"""
        raise NotImplementedError


    #
    # The following methods are candidates for reimplementation in derived
    # classes, in cases where the provided default behavior is not appropriate.
    #
    def is_valid_outid(self, outId):
        """Validate feature id in OUT space.

        Override if OUT space is not simly a 1D vector
        """
        return(outId >= 0 and outId < self.get_outsize())


    def is_valid_inid(self, inId):
        """Validate id in IN space.

        Override if IN space is not simly a 1D vector
        """
        return(inId >= 0 and inId < self.getInSize())


    def train(self, dataset):
        """Perform training of the mapper.

        This method is called to put the mapper in a state that allows it to
        perform the intended mapping. It takes care of running pre- and
        postprocessing that is potentially implemented in derived classes.

        Parameters
        ----------
        dataset: Dataset-like, anything
          Typically this is a `Dataset`, but it might also be a plain data
          array, or even something completely different(TM) that is supported
          by a subclass' implementation.

        Results
        -------
        whoknows
          Returns whatever is returned by the derived class.
        """
        # this mimics Classifier.train() -- we might merge them all at some
        # point
        self._pretrain(dataset)
        result = self._train(dataset)
        self._posttrain(dataset)
        return result


    def _train(self, dataset):
        """Worker method. Needs to be implemented by subclass."""
        raise NotImplementedError


    def _pretrain(self, dataset):
        """Preprocessing before actual mapper training.

        This method can be reimplemented in derived classes. By default it does
        nothing.

        Parameters
        ----------
        dataset: Dataset-like, anything
          Typically this is a `Dataset`, but it might also be a plain data
          array, or even something completely different(TM) that is supported
          by a subclass' implementation.
        """
        pass


    def _posttrain(self, dataset):
        """Postprocessing after actual mapper training.

        This method can be reimplemented in derived classes. By default it does
        nothing.

        Parameters
        ----------
        dataset: Dataset-like, anything
          Typically this is a `Dataset`, but it might also be a plain data
          array, or even something completely different(TM) that is supported
          by a subclass' implementation.
        """
        pass


    def _get_outids(self, in_ids):
        """Determine the output ids from a list of input space id/coordinates.

        Parameters
        ----------
        in_ids : list
          List of input ids whos output ids shall be determined.

        Returns
        -------
        list
          The list that contains all corresponding output ids. The default
          implementation returns an empty list -- meaning there is no
          one-to-one, or one-to-many correspondance of input and output feature
          spaces.
        """
        # reimplement in derived classes to actually perform something useful
        return []


    def getNeighbor(self, outId, *args, **kwargs):
        """Get feature neighbors in input space, given an id in output space.

        This method has to be reimplemented whenever a derived class does not
        provide an implementation for :meth:`~mvpa.mappers.base.Mapper.getInId`.
        """
        if self.metric is None:
            raise RuntimeError, "No metric was assigned to %s, thus no " \
                  "neighboring information is present" % self

        if self.is_valid_outid(outId):
            inId = self.getInId(outId)
            for inId in self.getNeighborIn(inId, *args, **kwargs):
                yield self.getOutId(inId)


    #
    # The following methods provide common functionality for all mappers
    # and there should be no immediate need to reimplement them
    #
    def getNeighborIn(self, inId, *args, **kwargs):
        """Return the list of coordinates for the neighbors.

        :Parameters:
          inId
            id (index) of an element in input dataspace.
          *args, **kwargs
            Any additional arguments are passed to the embedded metric of the
            mapper.

        XXX See TODO below: what to return -- list of arrays or list
        of tuples?
        """
        if self.metric is None:
            raise RuntimeError, "No metric was assigned to %s, thus no " \
                  "neighboring information is present" % self

        is_valid_inid = self.is_valid_inid
        if is_valid_inid(inId):
            for neighbor in self.metric.getNeighbor(inId, *args, **kwargs):
                if is_valid_inid(neighbor):
                    yield neighbor


    def getNeighbors(self, outId, *args, **kwargs):
        """Return the list of coordinates for the neighbors.

        By default it simply constructs the list based on
        the generator returned by getNeighbor()
        """
        return [ x for x in self.getNeighbor(outId, *args, **kwargs) ]


    def get_outids(self, in_ids=None, **kwargs):
        """Determine the output ids from a list of input space id/coordinates.

        Parameters
        ----------
        in_ids : list
          List of input ids whos output ids shall be determined.
        **kwargs: anything
          Further qualification of coordinates in particular spaces. Spaces are
          identified by the respected keyword and the values expresses an
          additional criterion. If the mapper has any information about the
          given space it uses this information to further restrict the set of
          output ids. Information about unkown spaces is returned as is.

        Returns
        -------
        (list, dict)
          The list that contains all corresponding output ids. The default
          implementation returns an empty list -- meaning there is no
          one-to-one, or one-to-many correspondance of input and output feature
          spaces. The dictionary contains all space-related information that
          have not been processed by the mapper (i.e. the spaces they referred
          to are unknown to the mapper. By default all additional keyword
          arguments are returned as is.
        """
        ourspace = self.get_inspace()
        # first contrain the set of in_ids if a known space is given
        if not ourspace is None and kwargs.has_key(ourspace):
            # merge with the current set, if there is any
            if in_ids is None:
                in_ids = kwargs[ourspace]
            else:
                # XXX maybe allow for a 'union' mode??
                in_ids = list(set(in_ids).intersection(kwargs[ourspace]))

            # remove the space contraint, since it has been processed
            del kwargs[ourspace]

        # return early if there is nothing to do
        if in_ids is None:
            return ([], kwargs)

        if __debug__:
            # check for proper coordinate (also handle the case of 1d coords
            # given
            for in_id in in_ids:
                if not self.is_valid_inid(in_id):
                    raise ValueError(
                            "Invalid input id/coordinate (%s) for mapper '%s' "
                            % (str(in_id), self))

        # this whole thing only works for C-ordered arrays
        return (self._get_outids(in_ids), kwargs)


    def __repr__(self):
        if self.__metric is not None:
            s = "metric=%s" % repr(self.__metric)
        else:
            s = ''
        return "%s(%s)" % (self.__class__.__name__, s)


    def __call__(self, data):
        """Calls the mappers forward() method.
        """
        return self.forward(data)


    def get_inspace(self):
        """
        """
        return self.__inspace


    def set_inspace(self, name):
        """
        """
        self.__inspace = name


    def getMetric(self):
        """To make pylint happy"""
        return self.__metric


    def setMetric(self, metric):
        """To make pylint happy"""
        if metric is not None and not isinstance(metric, Metric):
            raise ValueError, "metric for Mapper must be an " \
                              "instance of a Metric class . Got %s" \
                                % `type(metric)`
        self.__metric = metric


    metric = property(fget=getMetric, fset=setMetric)
    nfeatures = VProperty(fget=get_outsize)



class ProjectionMapper(Mapper):
    """Linear mapping between multidimensional spaces.

    This class cannot be used directly. Sub-classes have to implement
    the `_train()` method, which has to compute the projection matrix
    `_proj` and optionally offset vectors `_offset_in` and
    `_offset_out` (if initialized with demean=True, which is default)
    given a dataset (see `_train()` docstring for more information).

    Once the projection matrix is available, this class provides
    functionality to perform forward and backwards linear mapping of
    data, the latter by default using pseudo-inverse (but could be
    altered in subclasses, like hermitian (conjugate) transpose in
    case of SVD).  Additionally, `ProjectionMapper` supports optional
    selection of arbitrary component (i.e. columns of the projection
    matrix) of the projection.

    Forward and back-projection matrices (a.k.a. *projection* and
    *reconstruction*) are available via the `proj` and `recon`
    properties.
    """

    _DEV__doc__ = """Think about renaming `demean`, may be `translation`?"""

    def __init__(self, selector=None, demean=True):
        """Initialize the ProjectionMapper

        :Parameters:
          selector: None | list
            Which components (i.e. columns of the projection matrix)
            should be used for mapping. If `selector` is `None` all
            components are used. If a list is provided, all list
            elements are treated as component ids and the respective
            components are selected (all others are discarded).
          demean: bool
            Either data should be demeaned while computing
            projections and applied back while doing reverse()
        """
        Mapper.__init__(self)

        self._selector = selector
        self._proj = None
        """Forward projection matrix."""
        self._recon = None
        """Reverse projection (reconstruction) matrix."""
        self._demean = demean
        """Flag whether to demean the to be projected data, prior to projection.
        """
        self._offset_in = None
        """Offset (most often just mean) in the input space"""
        self._offset_out = None
        """Offset (most often just mean) in the output space"""

    __doc__ = enhancedDocString('ProjectionMapper', locals(), Mapper)


    @accepts_dataset_as_samples
    def _pretrain(self, samples):
        """Determine the projection matrix.

        :Parameters:
          dataset : Dataset
            Dataset to operate on
        """
        self._offset_in = samples.mean(axis=0)


    def _posttrain(self, dataset):
        # perform component selection
        if self._selector is not None:
            self.selectOut(self._selector)


    def _demeanData(self, data):
        """Helper which optionally demeans
        """
        if self._demean:
            # demean the training data
            data = data - self._offset_in

            if __debug__ and "MAP_" in debug.active:
                debug("MAP_",
                      "%s: Mean of data in input space %s was subtracted" %
                      (self.__class__.__name__, self._offset_in))
        return data


    def forward(self, data, demean=None):
        """Perform forward projection.

        :Parameters:
          data: ndarray
            Data array to map
          demean: boolean | None
            Override demean setting for this method call.

        :Returns:
          NumPy array
        """
        # let arg overwrite instance flag
        if demean is None:
            demean = self._demean

        if self._proj is None:
            raise RuntimeError, "Mapper needs to be train before used."

        d = N.asmatrix(data)

        # Remove input offset if present
        if demean and self._offset_in is not None:
            d = d - self._offset_in

        # Do forward projection
        res = (d * self._proj).A

        # Add output offset if present
        if demean and self._offset_out is not None:
            res += self._offset_out

        return res


    def reverse(self, data):
        """Reproject (reconstruct) data into the original feature space.

        :Returns:
          NumPy array
        """
        if self._proj is None:
            raise RuntimeError, "Mapper needs to be trained before used."
        d = N.asmatrix(data)
        # Remove offset if present in output space
        if self._demean and self._offset_out is not None:
            d = d - self._offset_out

        # Do reverse projection
        res = (d * self.recon).A

        # Add offset in input space
        if self._demean and self._offset_in is not None:
            res += self._offset_in

        return res

    def _computeRecon(self):
        """Given that a projection is present -- compute reconstruction matrix.
        By default -- pseudoinverse of projection matrix.  Might be overridden
        in derived classes for efficiency.
        """
        return N.linalg.pinv(self._proj)

    def _getRecon(self):
        """Compute (if necessary) and return reconstruction matrix
        """
        # (re)build reconstruction matrix
        recon = self._recon
        if recon is None:
            self._recon = recon = self._computeRecon()
        return recon


    def get_insize(self):
        """Returns the number of original features."""
        return self._proj.shape[0]


    def get_outsize(self):
        """Returns the number of components to project on."""
        return self._proj.shape[1]


    def selectOut(self, outIds):
        """Choose a subset of components (and remove all others)."""
        self._proj = self._proj[:, outIds]
        if self._offset_out is not None:
            self._offset_out = self._offset_out[outIds]
        # invalidate reconstruction matrix
        self._recon = None

    proj  = property(fget=lambda self: self._proj, doc="Projection matrix")
    recon = property(fget=_getRecon, doc="Backprojection matrix")



class CombinedMapper(Mapper):
    """Meta mapper that combines several embedded mappers.

    This mapper can be used the map from several input dataspaces into a common
    output dataspace. When :meth:`~mvpa.mappers.base.CombinedMapper.forward`
    is called with a sequence of data, each element in that sequence is passed
    to the corresponding mapper, which in turned forward-maps the data. The
    output of all mappers is finally stacked (horizontally or column or
    feature-wise) into a single large 2D matrix (nsamples x nfeatures).

    .. note::
      This mapper can only embbed mappers that transform data into a 2D
      (nsamples x nfeatures) representation. For mappers not supporting this
      transformation, consider wrapping them in a
      :class:`~mvpa.mappers.base.ChainMapper` with an appropriate
      post-processing mapper.

    CombinedMapper fully supports forward and backward mapping, training,
    runtime selection of a feature subset (in output dataspace) and retrieval
    of neighborhood information.
    """
    def __init__(self, mappers, **kwargs):
        """
        :Parameters:
          mappers: list of Mapper instances
            The order of the mappers in the list is important, as it will define
            the order in which data snippets have to be passed to
            :meth:`~mvpa.mappers.base.CombinedMapper.forward`.
          **kwargs
            All additional arguments are passed to the base-class constructor.
        """
        Mapper.__init__(self, **kwargs)

        if not len(mappers):
            raise ValueError, \
                  'CombinedMapper needs at least one embedded mapper.'

        self._mappers = mappers


    def forward(self, data):
        """Map data from the IN spaces into to common OUT space.

        :Parameter:
          data: sequence
            Each element in the `data` sequence is passed to the corresponding
            embedded mapper and is mapped individually by it. The number of
            elements in `data` has to match the number of embedded mappers. Each
            element is `data` has to provide the same number of samples
            (first dimension).

        :Returns:
          array: nsamples x nfeatures
            Horizontally stacked array of all embedded mapper outputs.
        """
        if not len(data) == len(self._mappers):
            raise ValueError, \
                  "CombinedMapper needs a sequence with data for each " \
                  "Mapper"

        # return a big array for the result of the forward mapped data
        # of each embedded mapper
        try:
            return N.hstack(
                    [self._mappers[i].forward(d) for i, d in enumerate(data)])
        except ValueError:
            raise ValueError, \
                  "Embedded mappers do not generate same number of samples. " \
                  "Check input data."


    def reverse(self, data):
        """Reverse map data from OUT space into the IN spaces.

        :Parameter:
          data: array
            Single data array to be reverse mapped into a sequence of data
            snippets in their individual IN spaces.

        :Returns:
          list
        """
        # assure array and transpose
        # i.e. transpose of 1D does nothing, but of 2D puts features
        # along first dimension
        data = N.asanyarray(data).T

        if not len(data) == self.get_outsize():
            raise ValueError, \
                  "Data shape does match mapper reverse mapping properties."

        result = []
        fsum = 0
        for m in self._mappers:
            # calculate upper border
            fsum_new = fsum + m.get_outsize()

            result.append(m.reverse(data[fsum:fsum_new].T))

            fsum = fsum_new

        return result


    def train(self, dataset):
        """Trains all embedded mappers.

        The provided training dataset is splitted appropriately and the
        corresponding pieces are passed to the
        :meth:`~mvpa.mappers.base.Mapper.train` method of each embedded mapper.

        :Parameter:
          dataset: :class:`~mvpa.datasets.base.Dataset` or subclass
            A dataset with the number of features matching the `outSize` of the
            `CombinedMapper`.
        """
        if dataset.nfeatures != self.get_outsize():
            raise ValueError, "Training dataset does not match the mapper " \
                              "properties."

        fsum = 0
        for m in self._mappers:
            # need to split the dataset
            fsum_new = fsum + m.get_outsize()
            m.train(dataset[:, range(fsum, fsum_new)])
            fsum = fsum_new


    def get_insize(self):
        """Returns the size of the entity in input space"""
        return N.sum(m.get_insize() for m in self._mappers)


    def get_outsize(self):
        """Returns the size of the entity in output space"""
        return N.sum(m.get_outsize() for m in self._mappers)


    def selectOut(self, outIds):
        """Remove some elements and leave only ids in 'out'/feature space.

        .. note::
          The subset selection is done inplace

        :Parameter:
          outIds: sequence
            All output feature ids to be selected/kept.
        """
        # determine which features belong to what mapper
        # and call its selectOut() accordingly
        ids = N.asanyarray(outIds)
        fsum = 0
        for m in self._mappers:
            # bool which meta feature ids belongs to this mapper
            selector = N.logical_and(ids < fsum + m.get_outsize(), ids >= fsum)
            # make feature ids relative to this dataset
            selected = ids[selector] - fsum
            fsum += m.get_outsize()
            # finally apply to mapper
            m.selectOut(selected)


    def getNeighbor(self, outId, *args, **kwargs):
        """Get the ids of the neighbors of a single feature in output dataspace.

        :Parameters:
          outId: int
            Single id of a feature in output space, whos neighbors should be
            determined.
          *args, **kwargs
            Additional arguments are passed to the metric of the embedded
            mapper, that is responsible for the corresponding feature.

        Returns a list of outIds
        """
        fsum = 0
        for m in self._mappers:
            fsum_new = fsum + m.get_outsize()
            if outId >= fsum and outId < fsum_new:
                return m.getNeighbor(outId - fsum, *args, **kwargs)
            fsum = fsum_new

        raise ValueError, "Invalid outId passed to CombinedMapper.getNeighbor()"


    def __repr__(self):
        s = Mapper.__repr__(self).rstrip(' )')
        # beautify
        if not s[-1] == '(':
            s += ' '
        s += 'mappers=[%s])' % ', '.join([m.__repr__() for m in self._mappers])
        return s



class ChainMapper(Mapper):
    """Meta mapper that embedded a chain of other mappers.

    Each mapper in the chain is called successively to perform forward or
    reverse mapping.

    .. note::

      In its current implementation the `ChainMapper` treats all but the last
      mapper as simple pre-processing (in forward()) or post-processing (in
      reverse()) steps. All other capabilities, e.g. training and neighbor
      metrics are provided by or affect *only the last mapper in the chain*.

      With respect to neighbor metrics this means that they are determined
      based on the input space of the *last mapper* in the chain and *not* on
      the input dataspace of the `ChainMapper` as a whole
    """
    def __init__(self, mappers, **kwargs):
        """
        :Parameters:
          mappers: list of Mapper instances
          **kwargs
            All additional arguments are passed to the base-class constructor.
        """
        Mapper.__init__(self, **kwargs)

        if not len(mappers):
            raise ValueError, 'ChainMapper needs at least one embedded mapper.'

        self._mappers = mappers


    def forward(self, data):
        """Calls all mappers in the chain successively.

        :Parameter:
          data
            data to be chain-mapped.
        """
        mp = data
        for m in self._mappers:
            mp = m.forward(mp)

        return mp


    def reverse(self, data):
        """Calls all mappers in the chain successively, in reversed order.

        :Parameter:
          data: array
            data array to be reverse mapped into the orginal dataspace.
        """
        mp = data
        for m in reversed(self._mappers):
            mp = m.reverse(mp)

        return mp


    def train(self, dataset):
        """Trains the *last* mapper in the chain.

        :Parameter:
          dataset: :class:`~mvpa.datasets.base.Dataset` or subclass
            A dataset with the number of features matching the `outSize` of the
            last mapper in the chain (which is identical to the one of the
            `ChainMapper` itself).
        """
        if dataset.nfeatures != self.get_outsize():
            raise ValueError, "Training dataset does not match the mapper " \
                              "properties."

        self._mappers[-1].train(dataset)


    def get_insize(self):
        """Returns the size of the entity in input space"""
        return self._mappers[0].get_insize()


    def get_outsize(self):
        """Returns the size of the entity in output space"""
        return self._mappers[-1].get_outsize()


    def get_outids(self, in_id):
        """Determine the output id from a input space id/coordinate.

        Parameters
        ----------
        in_id : tuple, int

        Returns
        -------
        list
          The list contains all corresponding output ids. The default
          implementation return an empty list -- meaning there is no one-to-one,
          or one-to-many correspondance of input and output feature spaces.
        """
        return []


    def selectOut(self, outIds):
        """Remove some elements from the *last* mapper in the chain.

        :Parameter:
          outIds: sequence
            All output feature ids to be selected/kept.
        """
        self._mappers[-1].selectOut(outIds)


    def getNeighbor(self, outId, *args, **kwargs):
        """Get the ids of the neighbors of a single feature in output dataspace.

        .. note::

          The neighbors are determined based on the input space of the *last
          mapper* in the chain and *not* on the input dataspace of the
          `ChainMapper` as a whole!

        :Parameters:
          outId: int
            Single id of a feature in output space, whos neighbors should be
            determined.
          *args, **kwargs
            Additional arguments are passed to the metric of the embedded
            mapper, that is responsible for the corresponding feature.

        Returns a list of outIds
        """
        return self._mappers[-1].getNeighbor(outId, *args, **kwargs)


    def __repr__(self):
        s = Mapper.__repr__(self).rstrip(' )')
        # beautify
        if not s[-1] == '(':
            s += ' '
        s += 'mappers=[%s])' % ', '.join([m.__repr__() for m in self._mappers])
        return s
