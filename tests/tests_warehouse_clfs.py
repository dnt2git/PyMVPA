#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Miscelaneous functions/datasets to be used in the unit tests"""

__docformat__ = 'restructuredtext'

# take care of conditional import of external classifiers
from mvpa.misc.clfhelper import *

# Define sets of classifiers
from mvpa.clfs.smlr import SMLR
from mvpa.clfs.ridge import *
from mvpa.clfs.knn import *

# assume that we at least have some SVMs
clfs = {'LinearSVMC': [], 'NonLinearSVMC': []}

if 'libsvm' in pymvpa_opt_clf_ext:
    clfs['LinearSVMC'] += [libsvm.svm.LinearCSVMC(probability=1),
                           libsvm.svm.LinearNuSVMC(probability=1)]
    clfs['NonLinearSVMC'] += [libsvm.svm.RbfCSVMC(probability=1),
                              libsvm.svm.RbfNuSVMC(probability=1)]
if 'shogun' in pymvpa_opt_clf_ext:
    import sg.svm
    clfs['LinearSVMC'].append(sg.svm.LinearCSVMC())
    clfs['NonLinearSVMC'].append(sg.svm.RbfCSVMC())


clfs['SVMC'] = clfs['LinearSVMC'] + clfs['NonLinearSVMC']

clfs['LinearC'] = clfs['LinearSVMC'] + \
                  [ SMLR(implementation="Python"), SMLR(implementation="C") ]

clfs['NonLinearC'] = clfs['NonLinearSVMC'] + [ kNN(k=1), RidgeReg() ]

clfs['all'] = clfs['LinearC'] + clfs['NonLinearC']

clfs['clfs_with_sens'] =  clfs['LinearC']

