#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Wrap the libsvm package into a very simple class interface."""

__docformat__ = 'restructuredtext'

import numpy as N

from mvpa.misc.param import Parameter
from mvpa.misc import warning
from mvpa.misc.state import StateVariable
from mvpa.clfs.classifier import Classifier
import _svm as svm

if __debug__:
    from mvpa.misc import debug

# we better expose those since they are mentioned in docstrings
from svmc import \
     C_SVC, NU_SVC, ONE_CLASS, EPSILON_SVR, \
     NU_SVR, LINEAR, POLY, RBF, SIGMOID, \
     PRECOMPUTED


class SVMBase(Classifier):
    """Support Vector Machine Classifier.

    This is a simple interface to the libSVM package.
    """
    # init the parameter interface
    params = Classifier.params.copy()
    params['eps'] = Parameter(0.00001,
                              min=0,
                              descr='tolerance of termination criterium')


    # Since this is internal feature of LibSVM, this state variable is present
    # here
    probabilities = StateVariable(enabled=False,
        doc="Estimates of samples probabilities as provided by LibSVM")


    def __init__(self,
                 kernel_type,
                 svm_type,
                 C=-1.0,
                 nu=0.5,
                 coef0=0.0,
                 degree=3,
                 eps=0.00001,
                 p=0.1,
                 gamma=0.0,
                 probability=0,
                 shrinking=1,
                 weight_label=None,
                 weight=None,
                 cache_size=100,
                 **kwargs):
        # XXX Determine which parameters depend on each other and implement
        # safety/simplifying logic around them
        # already done for: nr_weight
        # thought: weight and weight_label should be a dict
        """This is the base class of all classifier that utilize the libSVM
        package underneath. It is not really meant to be used directly. Unless
        you know what you are doing it is most likely better to use one of the
        subclasses.

        Here is the explaination for some of the parameters from the libSVM
        documentation:

        svm_type can be one of C_SVC, NU_SVC, ONE_CLASS, EPSILON_SVR, NU_SVR.

        - `C_SVC`: C-SVM classification
        - `NU_SVC`: nu-SVM classification
        - `ONE_CLASS`: one-class-SVM
        - `EPSILON_SVR`: epsilon-SVM regression
        - `NU_SVR`: nu-SVM regression

        kernel_type can be one of LINEAR, POLY, RBF, SIGMOID.

        - `LINEAR`: ``u'*v``
        - `POLY`: ``(gamma*u'*v + coef0)^degree``
        - `RBF`: ``exp(-gamma*|u-v|^2)``
        - `SIGMOID`: ``tanh(gamma*u'*v + coef0)``
        - `PRECOMPUTED`: kernel values in training_set_file

        cache_size is the size of the kernel cache, specified in megabytes.
        C is the cost of constraints violation. (we usually use 1 to 1000)
        eps is the stopping criterion. (we usually use 0.00001 in nu-SVC,
        0.001 in others). nu is the parameter in nu-SVM, nu-SVR, and
        one-class-SVM. p is the epsilon in epsilon-insensitive loss function
        of epsilon-SVM regression. shrinking = 1 means shrinking is conducted;
        = 0 otherwise. probability = 1 means model with probability
        information is obtained; = 0 otherwise.

        nr_weight, weight_label, and weight are used to change the penalty
        for some classes (If the weight for a class is not changed, it is
        set to 1). This is useful for training classifier using unbalanced
        input data or with asymmetric misclassification cost.

        Each weight[i] corresponds to weight_label[i], meaning that
        the penalty of class weight_label[i] is scaled by a factor of weight[i].

        If you do not want to change penalty for any of the classes,
        just set nr_weight to 0.
        """
        if weight_label == None:
            weight_label = []
        if weight == None:
            weight = []

        # init base class
        Classifier.__init__(self, **kwargs)

        if not len(weight_label) == len(weight):
            raise ValueError, "Lenght of 'weight' and 'weight_label' lists is" \
                              "is not equal."

        self.param = svm.SVMParameter(
                        kernel_type=kernel_type,
                        svm_type=svm_type,
                        C=C,
                        nu=nu,
                        cache_size=cache_size,
                        coef0=coef0,
                        degree=degree,
                        eps=eps,
                        p=p,
                        gamma=gamma,
                        nr_weight=len(weight),
                        probability=probability,
                        shrinking=shrinking,
                        weight_label=weight_label,
                        weight=weight)
        """Store SVM parameters in libSVM compatible format."""

        self.__model = None
        """Holds the trained SVM."""

        self.__C = C
        """Holds original value of C. self.param will be adjusted before training
        if C<0 and it is C-SVM, so we could scale 'default' C value"""


    def __repr__(self):
        """Definition of the object summary over the object
        """
        res = "SVMBase("
        sep = ""
        for k, v in self.param._params.iteritems():
            res += "%s%s=%s" % (sep, k, str(v))
            sep = ', '
        res += sep + "enable_states=%s" % (str(self.states.enabled))
        res += ")"
        return res


    def _getDefaultC(self, data):
        """Compute default C

        TODO: for non-linear SVMs
        """

        if self.param.kernel_type == svm.svmc.LINEAR:
            datasetnorm = N.mean(N.sqrt(N.sum(data*data, axis=1)))
            value = 1.0/(datasetnorm*datasetnorm)
            if __debug__:
                debug("SVM", "Default C computed to be %f" % value)
        else:
            warning("TODO: No computation of default C is not yet implemented" +
                    " for non-linear SVMs. Assigning 1.0")
            value = 1.0

        return value

    def _train(self, data):
        """Train SVM
        """
        # libsvm needs doubles
        if data.samples.dtype == 'float64':
            src = data.samples
        else:
            src = data.samples.astype('double')

        svmprob = svm.SVMProblem( data.labels.tolist(), src )

        #import pydb
        #pydb.debugger()
        if self.__C < 0 and \
               self.param.svm_type in [svm.svmc.C_SVC]:
            self.param.C = self._getDefaultC(data.samples)*abs(self.__C)

        self.__model = svm.SVMModel(svmprob, self.param)


    def _predict(self, data):
        """Predict values for the data
        """
        # libsvm needs doubles
        if data.dtype == 'float64':
            src = data
        else:
            src = data.astype('double')

        predictions = [ self.model.predict(p) for p in src ]

        if self.states.isEnabled("values"):
            if len(self.trained_labels) > 2:
                warning("'Values' for multiclass SVM classifier are ambiguous. You " +
                        "are adviced to wrap your classifier with " +
                        "MulticlassClassifier for explicit handling of  " +
                        "separate binary classifiers and corresponding " +
                        "'values'")
            # XXX We do duplicate work. model.predict calls predictValuesRaw
            # internally and then does voting or thresholding. So if speed becomes
            # a factor we might want to move out logic from libsvm over here to base
            # predictions on obtined values, or adjust libsvm to spit out values from
            # predict() as well
            #
            #try:
            values = [ self.model.predictValuesRaw(p) for p in src ]
            if len(values)>0 and len(self.trained_labels) == 2:
                if __debug__:
                    debug("SVM","Forcing values to be ndarray and reshaping " +
                          "them to be 1D vector")
                values = N.array(values).reshape(len(values))
            self.values = values
            # XXX we should probably do the same as shogun for
            # multiclass -- just spit out warning without
            # providing actual values 'per pair' or whatever internal multiclass
            # implementation it was
            #except TypeError:
            #    warning("Current SVM doesn't support probability estimation," +
            #            " thus no 'values' state")

        if self.states.isEnabled("probabilities"):
            self.probabilities = [ self.model.predictProbability(p) for p in src ]
            try:
                self.probabilities = [ self.model.predictProbability(p) for p in src ]
            except TypeError:
                warning("Current SVM %s doesn't support probability estimation," %
                        self + " thus no 'values' state")
        return predictions

    def untrain(self):
        if __debug__:
            debug("SVM", "Untraining %s and destroying libsvm model" % self)
        super(SVMBase, self).untrain()
        del self.__model
        self.__model = None

    model = property(fget=lambda self: self.__model)
    """Access to the SVM model."""



class LinearSVM(SVMBase):
    """Base class of all linear SVM classifiers that make use of the libSVM
    package. Still not meant to be used directly.
    """
    params = SVMBase.params.copy()
    def __init__(self,
                 svm_type,
                 C=-1.0,
                 nu=0.5,
                 eps=0.00001,
                 p=0.1,
                 probability=0,
                 shrinking=1,
                 weight_label=None,
                 weight=None,
                 cache_size=100,
                 **kwargs):
        """The constructor arguments are virtually identical to the ones of
        the SVMBase class, except that 'kernel_type' is set to LINEAR.
        """
        if weight_label == None:
            weight_label = []
        if weight == None:
            weight = []

        # init base class
        SVMBase.__init__(self, kernel_type=svm.svmc.LINEAR,
                         svm_type=svm_type, C=C, nu=nu, cache_size=cache_size,
                         eps=eps, p=p, probability=probability,
                         shrinking=shrinking, weight_label=weight_label,
                         weight=weight, **kwargs)



class LinearNuSVMC(LinearSVM):
    """Classifier for linear Nu-SVM classification.
    """
    params = LinearSVM.params.copy()
    params['nu'] = Parameter(0.5,
                             min=0.0,
                             max=1.0,
                             descr='fraction of datapoints within the margin')
    # overwrite eps param with new default value (information taken from libSVM
    # docs
    params['eps'] = Parameter(0.001,
                              min=0,
                              descr='tolerance of termination criterium')


    def __init__(self,
                 nu=0.5,
                 eps=0.001,
                 probability=0,
                 shrinking=1,
                 weight_label=None,
                 weight=None,
                 cache_size=100,
                 **kwargs):
        """
        """
        if weight_label == None:
            weight_label = []
        if weight == None:
            weight = []

        # init base class
        LinearSVM.__init__(self, svm_type=svm.svmc.NU_SVC,
                           nu=nu, eps=eps, probability=probability,
                           shrinking=shrinking, weight_label=weight_label,
                           weight=weight, cache_size=cache_size, **kwargs)



class LinearCSVMC(LinearSVM):
    """Classifier for linear C-SVM classification.
    """
    params = LinearSVM.params.copy()
    params['C'] = Parameter(1.0,
                            min=0.0,
                            descr='cumulative constraint violation')


    def __init__(self,
                 C=-1.0,
                 eps=0.00001,
                 probability=0,
                 shrinking=1,
                 weight_label=None,
                 weight=None,
                 cache_size=100,
                 **kwargs):
        """
        """
        if weight_label == None:
            weight_label = []
        if weight == None:
            weight = []

        # init base class
        LinearSVM.__init__(self, svm_type=svm.svmc.C_SVC,
                           C=C, eps=eps, probability=probability,
                           shrinking=shrinking, weight_label=weight_label,
                           weight=weight, cache_size=cache_size, **kwargs)



class RbfNuSVMC(SVMBase):
    """Nu-SVM classifier using a radial basis function kernel.
    """
    params = SVMBase.params.copy()
    params['nu'] = Parameter(0.5,
                             min=0.0,
                             max=1.0,
                             descr='fraction of datapoints within the margin')
    # overwrite eps param with new default value (information taken from libSVM
    # docs
    params['eps'] = Parameter(0.001,
                              min=0,
                              descr='tolerance of termination criterium')
    params['gamma'] = \
        Parameter(0.0, min=0.0, descr='kernel width parameter - if set to 0.0' \
                                      'defaults to 1/(#classes)')


    def __init__(self,
                 nu=0.5,
                 gamma=0.0,
                 eps=0.001,
                 probability=0,
                 shrinking=1,
                 weight_label=None,
                 weight=None,
                 cache_size=100,
                 **kwargs):
        """
        """
        if weight_label == None:
            weight_label = []
        if weight == None:
            weight = []

        # init base class
        SVMBase.__init__(self, kernel_type=svm.svmc.RBF,
                         svm_type=svm.svmc.NU_SVC, nu=nu, gamma=gamma,
                         cache_size=cache_size, eps=eps,
                         probability=probability, shrinking=shrinking,
                         weight_label=weight_label, weight=weight, **kwargs)



class RbfCSVMC(SVMBase):
    """C-SVM classifier using a radial basis function kernel.
    """
    params = SVMBase.params.copy()
    params['C'] = Parameter(1.0,
                            min=0.0,
                            descr='cumulative constraint violation')
    params['gamma'] = \
        Parameter(0.0, min=0.0, descr='kernel width parameter - if set to 0.0' \
                                      'defaults to 1/(#classes)')


    def __init__(self,
                 C=-1.0,
                 gamma=0.0,
                 eps=0.00001,
                 probability=0,
                 shrinking=1,
                 weight_label=None,
                 weight=None,
                 cache_size=100,
                 **kwargs):
        """
        """
        if weight_label == None:
            weight_label = []
        if weight == None:
            weight = []

        # init base class
        SVMBase.__init__(self, kernel_type=svm.svmc.RBF,
                         svm_type=svm.svmc.C_SVC, C=C, gamma=gamma,
                         cache_size=cache_size, eps=eps,
                         probability=probability, shrinking=shrinking,
                         weight_label=weight_label, weight=weight, **kwargs)


# check if there is a libsvm version with configurable
# noise reduction ;)
if hasattr(svm.svmc, 'svm_set_verbosity'):
    if __debug__ and "SVMLIB" in debug.active:
        debug("SVM", "Setting verbosity for libsvm to 255")
        svm.svmc.svm_set_verbosity(255)
    else:
        svm.svmc.svm_set_verbosity(0)
