#emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""PyMVPA measures.

Module Description
==================

Provide some measures given a dataset. Most of the time, derivatives of
`FeaturewiseDatasetMeasure` are used, such as

* `OneWayAnova`
* `CorrCoef`
* `IterativeRelief`
* `NoisePerturbationSensitivity`

Also many classifiers natively provide sensitivity estimators via the call to
`getSensitivityAnalyzer` method
"""

__docformat__ = 'restructuredtext'

if __debug__:
    from mvpa.base import debug
    debug('INIT', 'mvpa.measures')

if __debug__:
    debug('INIT', 'mvpa.measures end')
