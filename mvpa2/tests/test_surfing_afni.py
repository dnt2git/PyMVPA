# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Unit tests for PyMVPA surface searchlight functions specific for 
handling AFNI datasets"""

import numpy as np
import nibabel as ni

import os
import tempfile

from mvpa2.testing import *
from mvpa2.testing.datasets import datasets

from mvpa2 import cfg
from mvpa2.base import externals
from mvpa2.datasets import Dataset
from mvpa2.measures.base import Measure
from mvpa2.datasets.mri import fmri_dataset

import mvpa2.misc.surfing.surf as surf
import mvpa2.misc.surfing.surf_fs_asc as surf_fs_asc
import mvpa2.misc.surfing.volgeom as volgeom
import mvpa2.misc.surfing.volsurf as volsurf
import mvpa2.misc.surfing.sparse_attributes as sparse_attributes
import mvpa2.misc.surfing.surf_voxel_selection as surf_voxel_selection

import mvpa2.misc.surfing.afni_niml as afni_niml
import mvpa2.misc.surfing.afni_niml_dset as afni_niml_dset

class SurfTests(unittest.TestCase):
    """Test for AFNI I/O together with surface-based stuff

    NNO Aug 2012

    added as requested by Yarik and Michael

    'Ground truth' is whatever output is returned by the implementation
    as of mid-Aug 2012"""

    def _set_rng(self):
        keys = [(17 * i ** 5 + 78234745 * i + 8934) % (2 ** 32 - 1)
                        for i in xrange(624)]
        keys = np.asanyarray(keys, dtype=np.uint32)
        np.random.set_state(('MT19937', keys, 0))

    def _test_afni_niml_dset(self):
        sz = (10000, 45)
        self._set_rng()

        expected_vals = {(0, 0):-2.13856 , (sz[0] - 1, sz[1] - 1): 0.81124502,
                         (sz[0], sz[1] - 1):None, (sz[0] - 1, sz[1]):None,
                         sz:None}


        fmts = ['text', 'binary', 'base64']
        tps = [np.int32, np.int64, np.float32, np.float64]

        data = np.random.normal(size=sz)

        labels = ['lab_%d' % round(np.random.uniform() * 1000)
                        for _ in xrange(sz[1])]
        node_indices = np.argsort(np.random.uniform(size=(sz[0],)))
        node_indices = np.reshape(node_indices, (sz[0], 1))


        eps = np.finfo('f').eps

        # test I/O
        _, fn = tempfile.mkstemp('data.niml.dset', 'test')

        modes = ['normal', 'skipio', 'sparse2full']

        for fmt in fmts:
            for tp in tps:
                for mode in modes:
                    dset = dict(data=np.asarray(data, tp),
                                labels=labels,
                                node_indices=node_indices)
                    dset_keys = dset.keys()

                    if mode == 'skipio':
                        r = afni_niml_dset.dset2rawniml(dset)
                        s = afni_niml.rawniml2string(r)
                        r2 = afni_niml.string2rawniml(s)
                        dset2 = afni_niml_dset.rawniml2dset(r2)[0]

                    else:
                        afni_niml_dset.write(fn, dset, fmt)
                        dset2 = afni_niml_dset.read(fn)
                        os.remove(fn)


                    for k in dset_keys:
                        v = dset[k]
                        v2 = dset2[k]

                        if k == 'data':
                            if mode == 'sparse2full':
                                nfull = 2 * sz[0]

                                dset3 = afni_niml_dset.sparse2full(dset2,
                                                            pad_to_node=nfull)

                                assert_equal(dset3['data'].shape[0], nfull)

                                idxs = dset['node_indices'][:, 0]
                                idxs3 = dset3['node_indices'][:, 0]
                                vbig = np.zeros((nfull, sz[1]))
                                vbig[idxs, :] = v[np.arange(sz[0]), :]
                                v = vbig
                                v2 = dset3['data'][idxs3, :]
                            else:
                                for pos, val in expected_vals.iteritems():
                                    if val is None:
                                        assert_raises(IndexError, lambda x:x[pos], v2)
                                    else:
                                        val2 = np.asarray(val, tp)
                                        assert_true(abs(v2[pos] - val2) < eps)
                        if type(v) is list:
                            assert_equal(v, v2)
                        else:
                            eps = .0001
                            if mode != 'sparse2full' or k == 'data':
                                _assert_array_equal_eps(v, v2, eps)

def test_afni_suma_spec(self):
    datapath = os.path.join(pymvpa_datadbroot,
                        'tutorial_data', 'tutorial_data', 'data', 'surfing')




def _assert_array_equal_eps(x, y, eps=.0001):
    if x.shape != y.shape:
        raise ValueError('not equal size: %r != %r' % (x.shape, y.shape))

    xr = np.reshape(x, (-1,))
    yr = np.reshape(y, (-1,))

    delta = np.abs(xr - yr)

    m = -(delta <= eps)

    # deal with NaNs
    if ((any(-np.isnan(xr[m])) or any(-np.isnan(yr[m])))):
        raise ValueError('arrays differ more than %r' % eps)


def suite():
    """Create the suite"""
    return unittest.makeSuite(SurfTests)


if __name__ == '__main__':
    import runner
