# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Various helpers to improve docstrings and textual output"""

__docformat__ = 'restructuredtext'

import re, textwrap

# for table2string
import numpy as np
from math import ceil
from StringIO import StringIO
from mvpa import cfg

from mvpa.base.externals import versions, exists
if __debug__:
    from mvpa.base import debug

__add_init2doc = False
__in_ipython = exists('running ipython env')

# if ran within IPython -- might need to add doc to init
if __in_ipython:
    __rst_mode = False                       # either to do ReST links at all
    if versions['ipython'] <= '0.8.1':
        __add_init2doc = True
else:
    __rst_mode = True

#
# Predefine some sugarings depending on syntax convention to be used
#
# XXX Might need to be removed or become proper cfg parameter
__rst_conventions = 'numpy'
if __rst_conventions == 'epydoc':
    _rst_sep = "`"
    _rst_indentstr = "  "
    def _rst_section(section_name):
        """Provide section heading"""
        return ":%s:" % section_name
elif __rst_conventions == 'numpy':
    _rst_sep = ""
    _rst_indentstr = ""
    def _rst_section(section_name):
        """Provide section heading"""
        return "%s\n%s" % (section_name, '-'*len(section_name))
else:
    raise ValueError, "Unknown convention %s for RST" % __rst_conventions


def _rst(s, snotrst=''):
    """Produce s only in __rst mode"""
    if __rst_mode:
        return s
    else:
        return snotrst

def _rst_underline(text, markup):
    """Add and underline RsT string matching the length of the given string.
    """
    return text + '\n' + markup * len(text)


def single_or_plural(single, plural, n):
    """Little helper to spit out single or plural version of a word.
    """
    ni = int(n)
    if ni > 1 or ni == 0:
        # 1 forest, 2 forests, 0 forests
        return plural
    else:
        return single


def handle_docstring(text, polite=True):
    """Take care of empty and non existing doc strings."""
    if text is None or not len(text):
        if polite:
            return '' #No documentation found. Sorry!'
        else:
            return ''
    else:
        # Problem is that first line might often have no offset, so might
        # need to be ignored from dedent call
        if not text.startswith(' '):
            lines = text.split('\n')
            text2 = '\n'.join(lines[1:])
            return lines[0] + "\n" + textwrap.dedent(text2)
        else:
            return textwrap.dedent(text)


def _indent(text, istr=_rst_indentstr):
    """Simple indenter
    """
    return '\n'.join(istr + s for s in text.split('\n'))


__parameters_str_re = re.compile("[\n^]\s*:?Parameters?:?\s*\n(:?\s*-+\s*\n)?")
"""regexp to match :Parameter: and :Parameters: stand alone in a line
or
Parameters
----------
in multiple lines"""


def _split_out_parameters(initdoc):
    """Split documentation into (header, parameters, suffix)

    Parameters
    ----------
    initdoc : string
      The documentation string
    """

    # TODO: bind it to the only word in the line
    p_res = __parameters_str_re.search(initdoc)
    if p_res is None:
        return initdoc, "", ""
    else:
        # Could have been accomplished also via re.match

        # where new line is after :Parameters:
        # parameters header index
        ph_i = p_res.start()

        # parameters body index
        pb_i = p_res.end()

        # end of parameters
        try:
            pe_i = initdoc.index('\n\n', pb_i)
        except ValueError:
            pe_i = len(initdoc)

        result = initdoc[:ph_i].rstrip('\n '), \
                 initdoc[pb_i:pe_i], initdoc[pe_i:]

    # XXX a bit of duplication of effort since handle_docstring might
    # do splitting internally
    return handle_docstring(result[0], polite=False).strip('\n'), \
           textwrap.dedent(result[1]).strip('\n'), \
           textwrap.dedent(result[2]).strip('\n')


__re_params = re.compile('(?:\n\S.*?)+$')
__re_spliter1 = re.compile('(?:\n|\A)(?=\S)')
__re_spliter2 = re.compile('[\n:]')
def _parse_parameters(paramdoc):
    """Parse parameters and return list of (name, full_doc_string)

    It is needed to remove multiple entries for the same parameter
    like it could be with adding parameters from the parent class

    It assumes that previously parameters were unwrapped, so their
    documentation starts at the begining of the string, like what
    should it be after _split_out_parameters
    """
    entries = __re_spliter1.split(paramdoc)
    result = [(__re_spliter2.split(e)[0].strip(), e)
              for e in entries if e != '']
    if __debug__:
        debug('DOCH', 'parseParameters: Given "%s", we split into %s' %
              (paramdoc, result))
    return result


##REF: Name was automagically refactored
def enhanced_doc_string(item, *args, **kwargs):
    """Generate enhanced doc strings for various items.

    Parameters
    ----------
    item : str or class
      What object requires enhancing of documentation
    *args : list
      Includes base classes to look for parameters, as well, first item
      must be a dictionary of locals if item is given by a string
    force_extend : bool
      Either to force looking for the documentation in the parents.
      By default force_extend = False, and lookup happens only if kwargs
      is one of the arguments to the respective function (e.g. item.__init__)
    skip_params : list of str
      List of parameters (in addition to [kwargs]) which should not
      be added to the documentation of the class.

    It is to be used from a collector, ie whenever class is already created
    """
    # Handling of arguments
    if len(kwargs):
        if set(kwargs.keys()).issubset(set(['force_extend'])):
            raise ValueError, "Got unknown keyword arguments (smth among %s)" \
                  " in enhanced_doc_string." % kwargs
    force_extend = kwargs.get('force_extend', False)
    skip_params = kwargs.get('skip_params', [])

    # XXX make it work also not only with classes but with methods as well
    if isinstance(item, basestring):
        if len(args)<1 or not isinstance(args[0], dict):
            raise ValueError, \
                  "Please provide locals for enhanced_doc_string of %s" % item
        name = item
        lcl = args[0]
        args = args[1:]
    elif hasattr(item, "im_class"):
        # bound method
        raise NotImplementedError, \
              "enhanced_doc_string is not yet implemented for methods"
    elif hasattr(item, "__name__"):
        name = item.__name__
        lcl = item.__dict__
    else:
        raise ValueError, "Don't know how to extend docstring for %s" % item

    # check whether docstring magic is requested or not
    if not cfg.getboolean('doc', 'pimp docstrings', True):
        return  lcl['__doc__']

    if __debug__:
        debug('DOCH', 'Processing docstrings of %s' % name)

    #return lcl['__doc__']
    rst_lvlmarkup = ["=", "-", "_"]

    # would then be called for any child... ok - ad hoc for SVM???
    if hasattr(item, '_customize_doc') and name=='SVM':
        item._customize_doc()

    initdoc = ""
    if lcl.has_key('__init__'):
        func = lcl['__init__']
        initdoc = func.__doc__

        # either to extend arguments
        # do only if kwargs is one of the arguments
        # in python 2.5 args are no longer in co_names but in varnames
        extend_args = force_extend or \
                      'kwargs' in (func.func_code.co_names +
                                   func.func_code.co_varnames)

        if __debug__ and not extend_args:
            debug('DOCH', 'Not extending parameters for __init__ of  %s' % name)

        if initdoc is None:
            initdoc = "Initialize instance of %s" % name

        initdoc, params, suffix = _split_out_parameters(initdoc)

        if lcl.has_key('_paramsdoc'):
            params += '\n' + handle_docstring(lcl['_paramsdoc'])

        params_list = _parse_parameters(params)
        known_params = set([i[0] for i in params_list])
        # no need for placeholders
        skip_params = set(skip_params + ['kwargs', '**kwargs'])

        # XXX we do evil check here, refactor code to separate
        #     regressions out of the classifiers, and making
        #     retrainable flag not available for those classes which
        #     can't actually do retraining. Although it is not
        #     actually that obvious for Meta Classifiers
        if hasattr(item, '__tags__'):
            clf_internals = item.__tags__
            skip_params.update([i for i in ('retrainable',)
                                if not (i in clf_internals)])

        known_params.update(skip_params)
        if extend_args:
            # go through all the parents and obtain their init parameters
            parent_params_list = []
            for i in args:
                if hasattr(i, '__init__'):
                    # XXX just assign within a class to don't redo without need
                    initdoc_ = i.__init__.__doc__
                    if initdoc_ is None:
                        continue
                    splits_ = _split_out_parameters(initdoc_)
                    params_ = splits_[1]
                    parent_params_list += _parse_parameters(params_.lstrip())

            # extend with ones which are not known to current init
            for i, v in parent_params_list:
                if not (i in known_params):
                    params_list += [(i, v)]
                    known_params.update([i])

        # if there are parameters -- populate the list
        if len(params_list):
            params_ = '\n'.join([i[1].rstrip() for i in params_list
                                 if not i[0] in skip_params])
            initdoc += "\n\n%s\n" \
                       % _rst_section('Parameters') + _indent(params_)

        if suffix != "":
            initdoc += "\n\n" + suffix

        initdoc = handle_docstring(initdoc)

        # Finally assign generated doc to the constructor
        lcl['__init__'].__doc__ = initdoc

    docs = [ handle_docstring(lcl['__doc__']) ]

    # Optionally populate the class documentation with it
    if __add_init2doc and initdoc != "":
        docs += [ _rst_underline('Constructor information for `%s` class'
                                 % name, rst_lvlmarkup[2]),
                  initdoc ]

    # Add information about the ca if available
    if lcl.has_key('_cadoc') and len(item._cadoc):
        # to don't conflict with Notes section if such was already
        # present
        lcldoc = lcl['__doc__'] or ''
        if not 'Notes' in lcldoc:
            section_name = _rst_section('Notes')
        else:
            section_name = '\n'         # just an additional newline
        # no indent is necessary since ca list must be already indented
        docs += ['%s\nAvailable state variables:' % section_name,
                 handle_docstring(item._cadoc)]

    # Deprecated -- but actually we might like to have it in ipython
    # mode may be?
    if False: #len(args):
        bc_intro = _rst('  ') + 'Please refer to the documentation of the ' \
                   'base %s for more information:' \
                   % (single_or_plural('class', 'classes', len(args)))

        docs += ['\n' + _rst_section('See Also'),
                 bc_intro,
                 '  ' + ',\n  '.join(['%s%s.%s%s%s' % (_rst(':class:`~'),
                                                      i.__module__,
                                                      i.__name__,
                                                     _rst('`'),
                                                      _rst_sep)
                                      for i in args])
                ]

    itemdoc = '\n\n'.join(docs)
    # remove some bogus new lines -- never 3 empty lines in doc are useful
    result = re.sub("\s*\n\s*\n\s*\n", "\n\n", itemdoc)

    return result


def table2string(table, out=None):
    """Given list of lists figure out their common widths and print to out

    Parameters
    ----------
    table : list of lists of strings
      What is aimed to be printed
    out : None or stream
      Where to print. If None -- will print and return string

    Returns
    -------
    string if out was None
    """

    print2string = out is None
    if print2string:
        out = StringIO()

    # equalize number of elements in each row
    Nelements_max = max(len(x) for x in table)
    for i, table_ in enumerate(table):
        table[i] += [''] * (Nelements_max - len(table_))

    # figure out lengths within each column
    atable = np.asarray(table)
    markup_strip = re.compile('^@[lrc]')
    col_width = [ max( [len(markup_strip.sub('', x))
                        for x in column] ) for column in atable.T ]
    string = ""
    for i, table_ in enumerate(table):
        string_ = ""
        for j, item in enumerate(table_):
            item = str(item)
            if item.startswith('@'):
                align = item[1]
                item = item[2:]
                if not align in ['l', 'r', 'c']:
                    raise ValueError, 'Unknown alignment %s. Known are l,r,c'
            else:
                align = 'c'

            NspacesL = ceil((col_width[j] - len(item))/2.0)
            NspacesR = col_width[j] - NspacesL - len(item)

            if align == 'c':
                pass
            elif align == 'l':
                NspacesL, NspacesR = 0, NspacesL + NspacesR
            elif align == 'r':
                NspacesL, NspacesR = NspacesL + NspacesR, 0
            else:
                raise RuntimeError, 'Should not get here with align=%s' % align

            string_ += "%%%ds%%s%%%ds " \
                       % (NspacesL, NspacesR) % ('', item, '')
        string += string_.rstrip() + '\n'
    out.write(string)

    if print2string:
        value = out.getvalue()
        out.close()
        return value


def _str(obj, *args, **kwargs):
    """Helper to get a structured __str__ for all objects.

    If an object has a `descr` attribute, its content will be used instead of
    an auto-generated description.

    Optional additional information might be added under certain debugging
    conditions (e.g. `id(obj)`).

    Parameters
    ----------
    obj : object
      This will typically be `self` of the to be documented object.
    *args, **kwargs : str
      An arbitrary number of additional items. All of them must be of type
      `str`. All items will be appended comma separated to the class name.
      Keyword arguments will be appended as `key`=`value.

    Returns
    -------
    str
    """
    truncate = cfg.get_as_dtype('verbose', 'truncate str', int, default=200)

    if hasattr(obj, 'descr'):
        s = obj.descr
    else:
        s ='%s' % obj.__class__.__name__
        auto_descr = ', '.join(list(args)
                       + ["%s=%s" % (k, v) for k, v in kwargs.iteritems()])
        if len(auto_descr):
            s += ': %s' % auto_descr

    if not truncate is None and len(s) > truncate - 5:
        # take <...> into account
        truncate -= 5
        s = "%s..." % s[:truncate]

    if __debug__ and 'DS_ID' in debug.active:
        # in case there was nothing but the class name
        if s[-1]:
            s += ', id=%i' % id(obj)
        else:
            s += ' id=%i' % id(obj)


    # finally wrap in <> and return
    return '<%s>' % s


def borrowdoc(cls, methodname=None):
    """Return a decorator to borrow docstring from another `cls`.`methodname`

    Examples
    --------
    To borrow `__repr__` docstring from parent class `Mapper`, do::

       @borrowdoc(Mapper)
       def __repr__(self):
           ...

    Parameters
    ----------
    cls
      Usually a parent class
    methodname : None or str
      Name of the method from which to borrow.  If None, would use
      the same name as of the decorated method
    """

    def _borrowdoc(method):
        """Decorator which assigns to the `method` docstring from another
        """
        if methodname is None:
            other_method = getattr(cls, method.__name__)
        else:
            other_method = getattr(cls, methodname)
        if hasattr(other_method, '__doc__'):
            method.__doc__ = other_method.__doc__
        return method
    return _borrowdoc


def borrowkwargs(cls, methodname=None, exclude=None):
    """Return  a decorator which would borrow docstring for ``**kwargs``

    Notes
    -----
    TODO: take care about ``*args`` in  a clever way if those are also present

    Examples
    --------
    In the simplest scenario -- just grab all arguments from parent class::

           @borrowkwargs(A)
           def met1(self, bu, **kwargs):
               pass

    Parameters
    ----------
    methodname : None or str
      Name of the method from which to borrow.  If None, would use
      the same name as of the decorated method
    exclude : None or list of arguments to exclude
      If function does not pass all ``**kwargs``, you would need to list
      those here to be excluded from borrowed docstring
    """

    def _borrowkwargs(method):
        """Decorator which borrows docstrings for ``**kwargs`` for the `method`
        """
        if methodname is None:
            other_method = getattr(cls, method.__name__)
        else:
            other_method = getattr(cls, methodname)
        # TODO:
        # method.__doc__ = enhanced_from(other_method.__doc__)

        mdoc, odoc = method.__doc__, other_method.__doc__
        if mdoc is None:
            mdoc = ''

        mpreamble, mparams, msuffix = _split_out_parameters(mdoc)
        opreamble, oparams, osuffix = _split_out_parameters(odoc)
        mplist = _parse_parameters(mparams)
        oplist = _parse_parameters(oparams)
        known_params = set([i[0] for i in mplist])

        # !!! has to not rebind exclude variable
        skip_params = exclude or []         # handle None
        skip_params = set(['kwargs', '**kwargs'] + skip_params)

        # combine two and filter out items to skip
        aplist = [i for i in mplist if not i[0] in skip_params]
        aplist += [i for i in oplist
                   if not i[0] in skip_params.union(known_params)]

        docstring = mpreamble
        if len(aplist):
            params_ = '\n'.join([i[1].rstrip() for i in aplist])
            docstring += "\n\n%s\n" \
                         % _rst_section('Parameters') + _indent(params_)

        if msuffix != "":
            docstring += "\n\n" + msuffix

        docstring = handle_docstring(docstring)

        # Finally assign generated doc to the method
        method.__doc__ = docstring
        return method
    return _borrowkwargs
