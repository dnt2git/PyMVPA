# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Base functionality of PyMVPA

Module Organization
===================

mvpa.base module contains various modules which are used through out
PyMVPA code, and are generic building blocks

.. packagetree::
   :style: UML

:group Basic: externals, config, verbosity, dochelpers
"""

__docformat__ = 'restructuredtext'


from sys import stdout, stderr

from mvpa.base.config import ConfigManager
from mvpa.base.verbosity import LevelLogger, OnceLogger, Logger

#
# Setup verbose and debug outputs
#
class _SingletonType(type):
    """Simple singleton implementation adjusted from
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/412551
    """
    def __init__(mcs, *args):
        type.__init__(mcs, *args)
        mcs._instances = {}

    def __call__(mcs, sid, instance, *args):
        if not sid in mcs._instances:
            mcs._instances[sid] = instance
        return mcs._instances[sid]

class __Singleton:
    """To ensure single instance of a class instantiation (object)

    """

    __metaclass__ = _SingletonType
    def __init__(self, *args):
        pass
    # Provided __call__ just to make silly pylint happy
    def __call__(self):
        raise NotImplementedError

#
# As the very first step: Setup configuration registry instance and
# read all configuration settings from files and env variables
#
cfg = __Singleton('cfg', ConfigManager())

verbose = __Singleton("verbose", LevelLogger(
    handlers = cfg.get('verbose', 'output', default='stdout').split(',')))

# Not supported/explained/used by now since verbose(0, is to print errors
#error = __Singleton("error", LevelLogger(
#    handlers=environ.get('MVPA_ERROR_OUTPUT', 'stderr').split(',')))

# Levels for verbose
# 0 -- nothing besides errors
# 1 -- high level stuff -- top level operation or file operations
# 2 -- cmdline handling
# 3 --
# 4 -- computation/algorithm relevant thingies

# Lets check if environment can tell us smth
if cfg.has_option('general', 'verbose'):
    verbose.level = cfg.getint('general', 'verbose')


class WarningLog(OnceLogger):
    """Logging class of messsages to be printed just once per each message

    """

    def __init__(self, btlevels=10, btdefault=False,
                 maxcount=1, *args, **kwargs):
        """Define Warning logger.

        It is defined by
          btlevels : int
            how many levels of backtrack to print to give a hint on WTF
          btdefault : bool
            if to print backtrace for all warnings at all
          maxcount : int
            how many times to print each warning
        """
        OnceLogger.__init__(self, *args, **kwargs)
        self.__btlevels = btlevels
        self.__btdefault = btdefault
        self.__maxcount = maxcount
        self.__explanation_seen = False


    def __call__(self, msg, bt=None):
        import traceback
        if bt is None:
            bt = self.__btdefault
        tb = traceback.extract_stack(limit=2)
        msgid = repr(tb[-2])         # take parent as the source of ID
        fullmsg = "WARNING: %s" % msg
        if not self.__explanation_seen:
            self.__explanation_seen = True
            fullmsg += "\n * Please note: warnings are "  + \
                  "printed only once, but underlying problem might " + \
                  "occur many times *"
        if bt and self.__btlevels > 0:
            fullmsg += "Top-most backtrace:\n"
            fullmsg += reduce(lambda x, y: x + "\t%s:%d in %s where '%s'\n" % \
                              y,
                              traceback.extract_stack(limit=self.__btlevels),
                              "")

        OnceLogger.__call__(self, msgid, fullmsg, self.__maxcount)


    def _setMaxCount(self, value):
        """Set maxcount for the warning"""
        self.__maxcount = value

    maxcount = property(fget=lambda x:x.__maxcount, fset=_setMaxCount)

# XXX what is 'bt'? Maybe more verbose name?
if cfg.has_option('warnings', 'bt'):
    warnings_btlevels = cfg.getint('warnings', 'bt')
    warnings_bt = True
else:
    warnings_btlevels = 10
    warnings_bt = False

if cfg.has_option('warnings', 'count'):
    warnings_maxcount = cfg.getint('warnings', 'count')
else:
    warnings_maxcount = 1

warning = WarningLog(
    handlers={
        False: cfg.get('warnings', 'output', default='stdout').split(','),
        True: []}[cfg.getboolean('warnings', 'suppress', default=False)],
    btlevels=warnings_btlevels,
    btdefault=warnings_bt,
    maxcount=warnings_maxcount
    )


if __debug__:
    from mvpa.base.verbosity import DebugLogger
    # NOTE: all calls to debug must be preconditioned with
    # if __debug__:

    debug = __Singleton("debug", DebugLogger(
        handlers=cfg.get('debug', 'output', default='stdout').split(',')))

    # set some debugging matricses to report
    # debug.registerMetric('vmem')

    # List agreed sets for debug
    debug.register('DBG',  "Debug output itself")
    debug.register('DOCH', "Doc helpers")
    debug.register('INIT', "Just sequence of inits")
    debug.register('RANDOM', "Random number generation")
    debug.register('EXT',  "External dependencies")
    debug.register('EXT_', "External dependencies (verbose)")
    debug.register('TEST', "Debug unittests")
    debug.register('MODULE_IN_REPR', "Include module path in __repr__")
    debug.register('ID_IN_REPR', "Include id in __repr__")
    debug.register('CMDLINE', "Handling of command line parameters")

    debug.register('DG',   "Data generators")
    debug.register('LAZY', "Miscelaneous 'lazy' evaluations")
    debug.register('LOOP', "Support's loop construct")
    debug.register('PLR',  "PLR call")
    debug.register('SLC',  "Searchlight call")
    debug.register('SA',   "Sensitivity analyzers")
    debug.register('IRELIEF', "Various I-RELIEFs")
    debug.register('SA_',  "Sensitivity analyzers (verbose)")
    debug.register('PSA',  "Perturbation analyzer call")
    debug.register('RFEC', "Recursive Feature Elimination call")
    debug.register('RFEC_', "Recursive Feature Elimination call (verbose)")
    debug.register('IFSC', "Incremental Feature Search call")
    debug.register('DS',   "*Dataset")
    debug.register('DS_NIFTI', "NiftiDataset(s)")
    debug.register('DS_',  "*Dataset (verbose)")
    debug.register('DS_ID',   "ID Datasets")
    debug.register('DS_STATS',"Datasets statistics")
    debug.register('SPL',   "*Splitter")

    debug.register('TRAN',  "Transformers")
    debug.register('TRAN_', "Transformers (verbose)")

    # CHECKs
    debug.register('CHECK_DS_SELECT',
                   "Check in dataset.select() for sorted and unique indexes")
    debug.register('CHECK_DS_SORTED', "Check in datasets for sorted")
    debug.register('CHECK_IDS_SORTED',
                   "Check for ids being sorted in mappers")
    debug.register('CHECK_TRAINED',
                   "Checking in checking if clf was trained on given dataset")
    debug.register('CHECK_RETRAIN', "Checking in retraining/retesting")
    debug.register('CHECK_STABILITY', "Checking for numerical stability")

    debug.register('MAP',   "*Mapper")
    debug.register('MAP_',  "*Mapper (verbose)")

    debug.register('COL',  "Generic Collectable")
    debug.register('UATTR', "Attributes with unique")
    debug.register('ST',   "State")
    debug.register('STV',  "State Variable")
    debug.register('COLR', "Collector for states and classifier parameters")
    debug.register('ES',   "Element selectors")

    debug.register('CLF',    "Base Classifiers")
    debug.register('CLF_',   "Base Classifiers (verbose)")
    #debug.register('CLF_TB',
    #    "Report traceback in train/predict. Helps to resolve WTF calls it")
    debug.register('CLFBST', "BoostClassifier")
    #debug.register('CLFBST_TB', "BoostClassifier traceback")
    debug.register('CLFBIN', "BinaryClassifier")
    debug.register('CLFMC',  "MulticlassClassifier")
    debug.register('CLFSPL', "SplitClassifier")
    debug.register('CLFFS',  "FeatureSelectionClassifier")
    debug.register('CLFFS_', "FeatureSelectionClassifier (verbose)")

    debug.register('STAT',   "Statistics estimates")
    debug.register('STAT_',  "Statistics estimates (verbose)")
    debug.register('STAT__', "Statistics estimates (very verbose)")

    debug.register('FS',     "FeatureSelections")
    debug.register('FS_',    "FeatureSelections (verbose)")
    debug.register('FSPL',   "FeatureSelectionPipeline")

    debug.register('SVM',    "SVM")
    debug.register('SVM_',   "SVM (verbose)")
    debug.register('LIBSVM', "Internal libsvm output")

    debug.register('SMLR',    "SMLR")
    debug.register('SMLR_',   "SMLR verbose")

    debug.register('LARS',    "LARS")
    debug.register('LARS_',   "LARS (verbose)")

    debug.register('ENET',    "ENET")
    debug.register('ENET_',   "ENET (verbose)")

    debug.register('GPR',     "GPR")
    debug.register('GPR_WEIGHTS', "Track progress of GPRWeights computation")
    debug.register('KERNEL',  "Kernels module")
    debug.register('MOD_SEL', "Model Selector (also makes openopt's iprint=0)")
    debug.register('OPENOPT', "OpenOpt toolbox verbose (iprint=1)")

    debug.register('SG',  "PyMVPA SG wrapping")
    debug.register('SG_', "PyMVPA SG wrapping verbose")
    debug.register('SG__', "PyMVPA SG wrapping debug")
    debug.register('SG_SVM', "Internal shogun debug output for SVM itself")
    debug.register('SG_FEATURES', "Internal shogun debug output for features")
    debug.register('SG_LABELS', "Internal shogun debug output for labels")
    debug.register('SG_KERNELS', "Internal shogun debug output for kernels")
    debug.register('SG_PROGRESS',
                   "Internal shogun progress bar during computation")

    debug.register('IOH',    "IO Helpers")
    debug.register('IO_HAM', "Hamster")
    debug.register('CM',   "Confusion matrix computation")
    debug.register('ROC',  "ROC analysis")
    debug.register('CROSSC', "Cross-validation call")
    debug.register('CERR', "Various ClassifierErrors")

    debug.register('ATL',    "Atlases")
    debug.register('ATL_',   "Atlases (verbose)")
    debug.register('ATL__',  "Atlases (very verbose)")

    # Lets check if environment can tell us smth
    if cfg.has_option('general', 'debug'):
        debug.setActiveFromString(cfg.get('general', 'debug'))

    # Lets check if environment can tell us smth
    if cfg.has_option('debug', 'metrics'):
        debug.registerMetric(cfg.get('debug', 'metrics').split(","))



if __debug__:
    debug('INIT', 'mvpa.base end')
