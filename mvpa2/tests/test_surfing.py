# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Unit tests for PyMVPA surface searchlight and related utilities"""

from mvpa2.testing import *
skip_if_no_external('nibabel')


import numpy as np
from numpy.testing.utils import assert_array_almost_equal

import nibabel as nb

import os
import tempfile

from mvpa2.testing.datasets import datasets

from mvpa2 import cfg
from mvpa2.base import externals
from mvpa2.datasets import Dataset, hstack
from mvpa2.measures.base import Measure
from mvpa2.datasets.mri import fmri_dataset

from mvpa2.misc.surfing import volgeom, volsurf, \
                                volume_mask_dict, surf_voxel_selection, \
                                queryengine

from mvpa2.support.nibabel import surf, surf_fs_asc

from mvpa2.measures.searchlight import sphere_searchlight, Searchlight
from mvpa2.misc.neighborhood import Sphere

if externals.exists('h5py'):
    from mvpa2.base.hdf5 import h5save, h5load


class SurfTests(unittest.TestCase):
    """Test for surfaces

    NNO Aug 2012

    'Ground truth' is whatever output is returned by the implementation
    as of mid-Aug 2012"""

    def test_surf(self):
        """Some simple testing with surfaces
        """

        s = surf.generate_sphere(10)

        assert_true(s.nvertices == 102)
        assert_true(s.nfaces == 200)

        v = s.vertices
        f = s.faces

        assert_true(v.shape == (102, 3))
        assert_true(f.shape == (200, 3))



        # another surface
        t = s * 10 + 2
        assert_true(t.same_topology(s))
        assert_array_equal(f, t.faces)

        assert_array_equal(v * 10 + 2, t.vertices)

        # allow updating, but should not affect original array
        # CHECKME: maybe we want to throw an exception instead
        assert_true((v * 10 + 2 == t.vertices).all().all())
        assert_true((s.vertices * 10 + 2 == t.vertices).all().all())

        # a few checks on vertices and nodes
        v_check = {40:(0.86511144 , -0.28109175, -0.41541501),
                   10:(0.08706015, -0.26794358, -0.95949297)}
        f_check = {10:(7, 8, 1), 40:(30, 31, 21)}


        vf_checks = [(v_check, lambda x:x.vertices),
                     (f_check, lambda x:x.faces)]

        eps = .0001
        for cmap, f in vf_checks:
            for k, v in cmap.iteritems():
                surfval = f(s)[k, :]
                assert_true((abs(surfval - v) < eps).all())

        # make sure same topology fails with different topology
        u = surf.generate_cube()
        assert_false(u.same_topology(s))

        # check that neighbours are computed correctly
        # even if we nuke the topology afterwards
        for _ in [0, 1]:
            nbrs = s.neighbors
            n_check = [(0, 96, 0.284629),
                       (40, 39, 0.56218349),
                       (100, 99, 0.1741202)]
            for i, j, k in n_check:
                assert_true(abs(nbrs[i][j] - k) < eps)


        def assign_zero(x):
            x.faces[:, :] = 0
            return None

        assert_raises(RuntimeError, assign_zero, s)

        # see if mapping to high res works
        h = surf.generate_sphere(40)

        low2high = s.map_to_high_resolution_surf(h, .1)
        partmap = {7: 141, 8: 144, 9: 148, 10: 153, 11: 157, 12: 281}
        for k, v in partmap.iteritems():
            assert_true(low2high[k] == v)

        # ensure that slow implementation gives same results as fast one
        low2high_slow = s.map_to_high_resolution_surf(h, .1)
        for k, v in low2high.iteritems():
            assert_true(low2high_slow[k] == v)

        #  should fail if epsilon is too small
        assert_raises(ValueError,
                      lambda x:x.map_to_high_resolution_surf(h, .01), s)

        n2f = s.node2faces
        for i in xrange(s.nvertices):
            nf = [10] if i < 2 else [5, 6] # number of faces expected

            assert_true(len(n2f[i]) in nf)


        # test dijkstra disances
        ds2 = s.dijkstra_distance(2)
        some_ds = {0: 3.613173280799, 1: 0.2846296765, 2: 0.,
                 52: 1.87458018, 53: 2.0487004817, 54: 2.222820777,
                 99: 3.32854360, 100: 3.328543604, 101: 3.3285436042}

        eps = np.finfo('f').eps
        for k, v in some_ds.iteritems():
            assert_true(abs(v - ds2[k]) < eps)

        # test I/O (throught ascii files)
        _, fn = tempfile.mkstemp('surf.asc', 'surftest')
        surf.write(fn, s, overwrite=True)
        s2 = surf.read(fn)
        os.remove(fn)

        assert_array_almost_equal(s.vertices, s2.vertices, 4)
        assert_array_almost_equal(s.faces, s2.faces, 4)

        # test plane (new feature end of August 2012)
        s3 = surf.generate_plane((0, 0, 0), (2, 0, 0), (0, 1, 0), 10, 20)
        assert_equal(s3.nvertices, 200)
        assert_equal(s3.nfaces, 342)
        assert_array_almost_equal(s3.vertices[-1, :], np.array([18., 19, 0.]))
        assert_array_almost_equal(s3.faces[-1, :], np.array([199, 198, 179]))


    def test_surf_fs_asc(self):
        s = surf.generate_sphere(5) * 100

        _, fn = tempfile.mkstemp('surf', 'test')
        surf_fs_asc.write(fn, s, overwrite=True)

        t = surf_fs_asc.read(fn)
        os.remove(fn)

        assert_array_almost_equal(s.vertices, t.vertices)
        assert_array_almost_equal(s.vertices, t.vertices)

        theta = np.asarray([0, 0., 180.])

        r = s.rotate(theta, unit='deg')

        l2r = surf_fs_asc.sphere_reg_leftrightmapping(s, r)
        l2r_expected = [0, 1, 2, 6, 5, 4, 3, 11, 10, 9, 8, 7, 15, 14, 13, 12,
                       16, 19, 18, 17, 21, 20, 23, 22, 26, 25, 24]

        assert_array_equal(l2r, np.asarray(l2r_expected))


        sides_facing = 'apism'
        for side_facing in sides_facing:
            l, r = surf_fs_asc.hemi_pairs_reposition(s + 10., t + (-10.),
                                                     side_facing)

            m = surf.merge(l, r)

            # not sure at the moment why medial rotation 
            # messes up - but leave for now
            eps = 666 if side_facing == 'm' else .001
            assert_true((abs(m.center_of_mass) < eps).all())

    def test_volgeom(self):
        sz = (17, 71, 37, 73) # size of 4-D 'brain volume'
        d = 2. # voxel size
        xo, yo, zo = -6., -12., -20. # origin
        mx = np.identity(4, np.float) * d # affine transformation matrix
        mx[3, 3] = 1
        mx[0, 3] = xo
        mx[1, 3] = yo
        mx[2, 3] = zo

        vg = volgeom.VolGeom(sz, mx) # initialize volgeom

        eq_shape_nvoxels = {(17, 71, 37): (True, True),
                           (71, 17, 37, 1): (False, True),
                           (17, 71, 37, 2): (True, True),
                            (17, 71, 37, 73): (True, True),
                           (2, 2, 2): (False, False)}

        for other_sz, (eq_shape, eq_nvoxels) in eq_shape_nvoxels.iteritems():
            other_vg = volgeom.VolGeom(other_sz, mx)
            assert_equal(other_vg.same_shape(vg), eq_shape)
            assert_equal(other_vg.nvoxels_mask == vg.nvoxels_mask, eq_nvoxels)

        nv = sz[0] * sz[1] * sz[2] # number of voxels
        nt = sz[3] # number of time points
        assert_equal(vg.nvoxels, nv)

        # a couple of hard-coded test cases
        # last two are outside the volume
        linidxs = [0, 1, sz[2], sz[1] * sz[2], nv - 1, -1 , nv]
        subidxs = ([(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0),
                    (sz[0] - 1, sz[1] - 1, sz[2] - 1)]
                   + [(sz[0], sz[1], sz[2])] * 2)

        xyzs = ([(xo, yo, zo), (xo, yo, zo + d), (xo, yo + d, zo),
                 (xo + d, yo, zo),
                 (xo + d * (sz[0] - 1), yo + d * (sz[1] - 1), zo + d * (sz[2] - 1))]
                + [(np.nan, np.nan, np.nan)] * 2)

        for i, linidx in enumerate(linidxs):
            lin = np.asarray([linidx])
            ijk = vg.lin2ijk(lin)


            ijk_expected = np.reshape(np.asarray(subidxs[i]), (1, 3))
            assert_array_almost_equal(ijk, ijk_expected)

            xyz = vg.lin2xyz(lin)

            xyz_expected = np.reshape(np.asarray(xyzs[i]), (1, 3))
            assert_array_almost_equal(xyz, xyz_expected)


        # check that some identities hold
        ab, bc, ac = vg.lin2ijk, vg.ijk2xyz, vg.lin2xyz
        ba, cb, ca = vg.ijk2lin, vg.xyz2ijk, vg.xyz2lin
        identities = [lambda x:ab(ba(x)),
                      lambda x:bc(cb(x)),
                      lambda x:ac(ca(x)),
                      lambda x:ba(ab(x)),
                      lambda x:cb(bc(x)),
                      lambda x:ca(ac(x)),
                      lambda x:bc(ab(ca(x))),
                      lambda x:ba(cb(ac(x)))]

        # 0=lin, 1=ijk, 2=xyz
        identities_input = [1, 2, 2, 0, 1, 0, 2, 0]

        # voxel indices to test
        linrange = [0, 1, sz[2], sz[1] * sz[2]] + range(0, nv, nv / 100)

        lin = np.reshape(np.asarray(linrange), (-1,))
        ijk = vg.lin2ijk(lin)
        xyz = vg.ijk2xyz(ijk)

        for j, identity in enumerate(identities):
            inp = identities_input[j]
            x = {0: lin,
                 1: ijk,
                 2: xyz}[inp]

            assert_array_equal(x, identity(x))

        # check that masking works
        assert_true(vg.contains_lin(lin).all())
        assert_false(vg.contains_lin(-lin - 1).any())

        assert_true(vg.contains_ijk(ijk).all())
        assert_false(vg.contains_ijk(-ijk - 1).any())


        # ensure that we have no rounding issues
        deltas = [-.51, -.49, 0., .49, .51]
        should_raise = [True, False, False, False, True]

        for delta, r in zip(deltas, should_raise):
            xyz_d = xyz + delta * d
            lin_d = vg.xyz2lin(xyz_d)

            if r:
                assert_raises(AssertionError,
                              assert_array_almost_equal, lin_d, lin)
            else:
                assert_array_almost_equal(lin_d, lin)


        # some I/O testing

        img = vg.get_empty_nifti_image()
        _, fn = tempfile.mkstemp('.nii', 'test')
        img.to_filename(fn)

        assert_true(os.path.exists(fn))

        vg2 = volgeom.from_any(img)
        vg3 = volgeom.from_any(fn)

        assert_array_equal(vg.affine, vg2.affine)
        assert_array_equal(vg.affine, vg3.affine)

        assert_equal(vg.shape[:3], vg2.shape[:3], 0)
        assert_equal(vg.shape[:3], vg3.shape[:3], 0)

        os.remove(fn)

        assert_true(len('%s%r' % (vg, vg)) > 0)

    def test_volgeom_masking(self):
        maskstep = 5
        vg = volgeom.VolGeom((2 * maskstep, 2 * maskstep, 2 * maskstep), np.identity(4))

        mask = vg.get_empty_array()
        sh = vg.shape

        # mask a subset of the voxels
        rng = range(0, sh[0], maskstep)
        for i in rng:
            for j in rng:
                for k in rng:
                    mask[i, j, k] = 1

        # make a new volgeom instance
        vg = volgeom.VolGeom(vg.shape, vg.affine, mask)

        data = vg.get_masked_nifti_image(nt=1)
        msk = vg.get_masked_nifti_image()
        dset = fmri_dataset(data, mask=msk)
        vg_dset = volgeom.from_any(dset)

        # ensure that the mask is set properly and 
        assert_equal(vg.nvoxels, vg.nvoxels_mask * maskstep ** 3)
        assert_equal(vg_dset, vg)

        dilates = range(0, 8, 2)
        nvoxels_masks = [] # keep track of number of voxels for each size
        for dilate in dilates:
            covers_full_volume = dilate * 2 >= maskstep * 3 ** .5 + 1

            # constr gets values: None, Sphere(0), 2, Sphere(2), ...
            for i, constr in enumerate([Sphere, lambda x:x if x else None]):
                dilater = constr(dilate)

                img_dilated = vg.get_masked_nifti_image(dilate=dilater)
                data = img_dilated.get_data()

                assert_array_equal(data, vg.get_masked_array(dilate=dilater))
                n = np.sum(data)

                # number of voxels in mask is increasing
                assert_true(all(n >= p for p in nvoxels_masks))

                # results should be identical irrespective of constr
                if i == 0:
                    # - first call with this value of dialte: has to be more 
                    #   voxels than very previous dilation value, unless the 
                    #   full volume is covered - then it can be equal too
                    # - every next call: ensure size matches
                    cmp = lambda x, y:(x >= y if covers_full_volume else x > y)
                    assert_true(all(cmp(n, p) for p in nvoxels_masks))
                    nvoxels_masks.append(n)
                else:
                    # same size as previous call
                    assert_equal(n, nvoxels_masks[-1])

                # if dilate is not None or zero, then it should 
                # have selected all the voxels if the radius is big enough
                assert_equal(np.sum(data) == vg.nvoxels, covers_full_volume)



    def test_volsurf(self):
        vg = volgeom.VolGeom((50, 50, 50), np.identity(4))

        density = 40
        outer = surf.generate_sphere(density) * 25. + 25
        inner = surf.generate_sphere(density) * 20. + 25


        vs = volsurf.VolSurf(vg, outer, inner)

        # increasingly select more voxels in 'grey matter'
        steps_start_stop = [(1, .5, .5), (5, .5, .5), (3, .3, .7),
                          (5, .3, .7), (5, 0., 1.), (10, 0., 1.)]

        mp = None
        expected_keys = set(range(density ** 2 + 2))
        selection_counter = []
        voxel_counter = []
        for sp, sa, so in steps_start_stop:
            n2v = vs.node2voxels(sp, sa, so)

            if mp is None:
                mp = n2v


            assert_equal(expected_keys, set(n2v.keys()))

            counter = 0
            for k, v2pos in n2v.iteritems():
                for v, pos in v2pos.iteritems():
                    # should be close to grey matter

                    assert_true(-1. <= pos and pos <= 2.)
                    counter += 1

            selection_counter.append(counter)
            img = vs.voxel_count_nifti_image(n2v)

            voxel_counter.append(np.sum(img.get_data() > 0))

        # hard coded number of expected voxels
        selection_expected = [1602, 1602, 4618, 5298, 7867, 10801]
        assert_equal(selection_counter, selection_expected)

        voxel_expected = [1498, 1498, 4322, 4986, 7391, 10141]
        assert_equal(voxel_counter, voxel_expected)

        # check that string building works
        assert_true(len('%s%r' % (vs, vs)) > 0)


    def test_volsurf_surf_from_volume(self):
        aff = np.eye(4)
        aff[0, 0] = aff[1, 1] = aff[2, 2] = 3

        sh = (40, 40, 40)

        vg = volgeom.VolGeom(sh, aff)

        p = volsurf.from_volume(vg).intermediate_surface
        q = volsurf.SurfaceFromVolume(vg)

        centers = [0, 10, 10000, (-1, -1, -1), (5, 5, 5)]
        radii = [0, 10, 20, 100]

        for center in centers:
            for radius in radii:
                x = p.circlearound_n2d(center, radius)
                y = q.circlearound_n2d(center, radius)
                assert_equal(x, y)


    def test_volume_mask_dict(self):
        # also tests the outside_node_margin feature
        sh = (10, 10, 10)
        msk = np.zeros(sh)
        for i in xrange(0, sh[0], 2):
            msk[i, :, :] = 1

        vol_affine = np.identity(4)
        vol_affine[0, 0] = vol_affine[1, 1] = vol_affine[2, 2] = 2

        vg = volgeom.VolGeom(sh, vol_affine, mask=msk)

        density = 10

        outer = surf.generate_sphere(density) * 10. + 5
        inner = surf.generate_sphere(density) * 5. + 5

        intermediate = outer * .5 + inner * .5
        xyz = intermediate.vertices

        radius = 50

        outside_node_margins = [None, 0, 100., np.inf, True]
        expected_center_count = [87] * 2 + [intermediate.nvertices] * 3
        for k, outside_node_margin in enumerate(outside_node_margins):

            sel = surf_voxel_selection.run_voxel_selection(radius, vg, inner,
                                outer, outside_node_margin=outside_node_margin)
            assert_equal(intermediate, sel.source)
            assert_equal(len(sel.keys()), expected_center_count[k])
            assert_true(set(sel.aux_keys()).issubset(set(['center_distances',
                                                    'grey_matter_position'])))

            msk_lin = msk.ravel()
            sel_msk_lin = sel.get_mask().ravel()
            for i in xrange(vg.nvoxels):
                if msk_lin[i]:
                    src = sel.target2nearest_source(i)
                    assert_false((src is None) ^ (sel_msk_lin[i] == 0))

                    if src is None:
                        continue

                    # index of node nearest to voxel i
                    src_anywhere = sel.target2nearest_source(i,
                                            fallback_euclidian_distance=True)

                    # coordinates of node nearest to voxel i
                    xyz_src = xyz[src_anywhere]

                    # coordinates of voxel i
                    xyz_trg = vg.lin2xyz(np.asarray([i]))

                    # distance between node nearest to voxel i, and voxel i
                    # this should be the smallest distancer
                    d = volgeom.distance(np.reshape(xyz_src, (1, 3)), xyz_trg)


                    # distances between all nodes and voxel i
                    ds = volgeom.distance(xyz, xyz_trg)

                    # order of the distances
                    is_ds = np.argsort(ds.ravel())

                    # go over all the nodes
                    # require that the node is in the volume
                    # mask

                    # index of node nearest to voxel i
                    ii = np.argmin(ds)

                    xyz_min = xyz[ii]
                    lin_min = vg.xyz2lin([xyz_min])




                    # linear index of voxel that contains xyz_src
                    lin_src = vg.xyz2lin(np.reshape(xyz_src, (1, 3)))

                    # when using multi-core support,
                    # pickling and unpickling can reduce the precision
                    # a little bit, causing rounding errors
                    eps = 1e-14

                    delta = np.abs(ds[ii] - d)
                    assert_false(delta > eps and ii in sel and
                                 i in sel[ii] and
                                 vg.contains_lin(lin_min))



    def test_surf_voxel_selection(self):
        vol_shape = (10, 10, 10)
        vol_affine = np.identity(4)
        vol_affine[0, 0] = vol_affine[1, 1] = vol_affine[2, 2] = 5

        vg = volgeom.VolGeom(vol_shape, vol_affine)

        density = 10

        outer = surf.generate_sphere(density) * 25. + 15
        inner = surf.generate_sphere(density) * 20. + 15

        vs = volsurf.VolSurf(vg, outer, inner)

        nv = outer.nvertices

        # select under variety of parameters
        # parameters are distance metric (dijkstra or euclidean), 
        # radius, and number of searchlight  centers
        params = [('d', 1., 10), ('d', 1., 50), ('d', 1., 100), ('d', 2., 100),
                  ('e', 2., 100), ('d', 2., 100), ('d', 20, 100),
                  ('euclidean', 5, None), ('dijkstra', 10, None)]

        # function that indicates for which parameters the full test is run
        test_full = lambda x:len(x[0]) > 1 or x[2] == 100

        expected_labs = ['grey_matter_position',
                         'center_distances']

        voxcount = []
        tested_double_features = False
        for param in params:
            distance_metric, radius, ncenters = param
            srcs = range(0, nv, nv / (ncenters or nv))
            sel = surf_voxel_selection.voxel_selection(vs, radius,
                                            source_surf_nodes=srcs,
                                            distance_metric=distance_metric)

            # see how many voxels were selected
            vg = sel.volgeom
            datalin = np.zeros((vg.nvoxels, 1))

            mp = sel
            for k, idxs in mp.iteritems():
                if idxs is not None:
                    datalin[idxs] = 1

            voxcount.append(np.sum(datalin))

            if test_full(param):
                assert_equal(np.sum(datalin), np.sum(sel.get_mask()))

                assert_true(len('%s%r' % (sel, sel)) > 0)

                # see if voxels containing inner and outer 
                # nodes were selected
                for sf in [inner, outer]:
                    for k, idxs in mp.iteritems():
                        xyz = np.reshape(sf.vertices[k, :], (1, 3))
                        linidx = vg.xyz2lin(xyz)

                        # only required if xyz is actually within the volume
                        assert_equal(linidx in idxs, vg.contains_lin(linidx))

                # check that it has all the attributes
                labs = sel.aux_keys()

                assert_true(all([lab in labs for lab in expected_labs]))


                if externals.exists('h5py'):
                    # some I/O testing
                    _, fn = tempfile.mkstemp('.h5py', 'test')
                    h5save(fn, sel)

                    sel2 = h5load(fn)
                    os.remove(fn)

                    assert_equal(sel, sel2)
                else:
                    sel2 = sel

                # check that mask is OK even after I/O
                assert_array_equal(sel.get_mask(), sel2.get_mask())


                # test I/O with surfaces
                _, outerfn = tempfile.mkstemp('outer.asc', 'test')
                _, innerfn = tempfile.mkstemp('inner.asc', 'test')
                _, volfn = tempfile.mkstemp('vol.nii', 'test')

                surf.write(outerfn, outer, overwrite=True)
                surf.write(innerfn, inner, overwrite=True)

                img = sel.volgeom.get_empty_nifti_image()
                img.to_filename(volfn)

                sel3 = surf_voxel_selection.run_voxel_selection(radius, volfn, innerfn,
                                outerfn, source_surf_nodes=srcs,
                                distance_metric=distance_metric)

                outer4 = surf.read(outerfn)
                inner4 = surf.read(innerfn)
                vs4 = vs = volsurf.VolSurf(vg, inner4, outer4)

                # check that two ways of voxel selection match
                sel4 = surf_voxel_selection.voxel_selection(vs4, radius,
                                                    source_surf_nodes=srcs,
                                                    distance_metric=distance_metric)

                assert_equal(sel3, sel4)

                os.remove(outerfn)
                os.remove(innerfn)
                os.remove(volfn)


                # compare sel3 with other selection results
                # NOTE: which voxels are precisely selected by sel can be quite
                #       off from those in sel3, as writing the surfaces imposes
                #       rounding errors and the sphere is very symmetric, which
                #       means that different neighboring nodes are selected
                #       to select a certain number of voxels.
                sel3cmp_difference_ratio = [(sel, .2), (sel4, 0.)]
                for selcmp, ratio in sel3cmp_difference_ratio:
                    nunion = ndiff = 0

                    for k in selcmp.keys():
                        p = set(sel3.get(k))
                        q = set(selcmp.get(k))
                        nunion += len(p.union(q))
                        ndiff += len(p.symmetric_difference(q))

                    assert_true(float(ndiff) / float(nunion) <= ratio)

                # check searchlight call
                # as of late Aug 2012, this is with the fancy query engine
                # as implemented by Yarik

                mask = sel.get_mask()
                keys = None if ncenters is None else sel.keys()

                dset_data = np.reshape(np.arange(vg.nvoxels), vg.shape)
                dset_img = nb.Nifti1Image(dset_data, vg.affine)
                dset = fmri_dataset(samples=dset_img, mask=mask)

                qe = queryengine.SurfaceVerticesQueryEngine(sel,
                                    # you can optionally add additional
                                    # information about each near-disk-voxels
                                    add_fa=['center_distances',
                                            'grey_matter_position'])
                assert_false('ERROR' in repr(qe))   #  to check if repr works
                voxelcounter = _Voxel_Count_Measure()
                searchlight = Searchlight(voxelcounter, queryengine=qe, roi_ids=keys, nproc=1,
                                          enable_ca=['roi_feature_ids'])
                sl_dset = searchlight(dset)

                selected_count = sl_dset.samples[0, :]
                mp = sel
                for i, k in enumerate(sel.keys()):
                    # check that number of selected voxels matches
                    assert_equal(selected_count[i], len(mp[k]))


                # check nearest node is *really* the nearest node

                allvx = sel.get_targets()
                intermediate = outer * .5 + inner * .5

                for vx in allvx:
                    nearest = sel.target2nearest_source(vx)

                    xyz = intermediate.vertices[nearest, :]
                    sqsum = np.sum((xyz - intermediate.vertices) ** 2, 1)

                    idx = np.argmin(sqsum)
                    assert_equal(idx, nearest)

                if not tested_double_features:           # test only once
                    # see if we have multiple features for the same voxel, we would get them all
                    dset1 = dset.copy()
                    dset1.fa['dset'] = [1]
                    dset2 = dset.copy()
                    dset2.fa['dset'] = [2]
                    dset_ = hstack((dset1, dset2))
                    dset_.sa = dset1.sa
                    dset_.a.imghdr = dset1.a.imghdr
                    roi_feature_ids = searchlight.ca.roi_feature_ids
                    sl_dset_ = searchlight(dset_)
                    # and we should get twice the counts
                    assert_array_equal(sl_dset_.samples, sl_dset.samples * 2)

                    # compare old and new roi_feature_ids
                    assert(len(roi_feature_ids) == len(searchlight.ca.roi_feature_ids))
                    nfeatures = dset.nfeatures
                    for old, new in zip(roi_feature_ids,
                                        searchlight.ca.roi_feature_ids):
                        # each new ids should comprise of old ones + (old + nfeatures)
                        # since we hstack'ed two datasets
                        assert_array_equal(np.hstack([(x, x + nfeatures) for x in old]),
                                           new)
                    tested_double_features = True

        # check whether number of voxels were selected is as expected
        expected_voxcount = [22, 93, 183, 183, 183, 183, 183, 183, 183]

        assert_equal(voxcount, expected_voxcount)

    def test_h5support(self):
        sh = (20, 20, 20)
        msk = np.zeros(sh)
        for i in xrange(0, sh[0], 2):
            msk[i, :, :] = 1
        vg = volgeom.VolGeom(sh, np.identity(4), mask=msk)

        density = 20

        outer = surf.generate_sphere(density) * 10. + 5
        inner = surf.generate_sphere(density) * 5. + 5

        intermediate = outer * .5 + inner * .5
        xyz = intermediate.vertices

        radius = 50

        backends = ['native', 'hdf5']

        for i, backend in enumerate(backends):
            if backend == 'hdf5' and not externals.exists('h5py'):
                continue

            sel = surf_voxel_selection.run_voxel_selection(radius, vg, inner,
                            outer, results_backend=backend)

            if i == 0:
                sel0 = sel
            else:
                assert_equal(sel0, sel)

    def test_agreement_surface_volume(self):
        '''test agreement between volume-based and surface-based
        searchlights when using euclidian measure'''

        #import runner
        def sum_ds(ds):
            return np.sum(ds)

        radius = 3

        # make a small dataset with a mask
        sh = (10, 10, 10)
        msk = np.zeros(sh)
        for i in xrange(0, sh[0], 2):
            msk[i, :, :] = 1
        vg = volgeom.VolGeom(sh, np.identity(4), mask=msk)

        # make an image
        nt = 6
        img = vg.get_masked_nifti_image(6)
        ds = fmri_dataset(img, mask=msk)


        # run the searchlight
        sl = sphere_searchlight(sum_ds, radius=radius)
        m = sl(ds)

        # now use surface-based searchlight
        v = volsurf.from_volume(ds)
        source_surf = v.intermediate_surface

        node_msk = np.logical_not(np.isnan(source_surf.vertices[:, 0]))

        # check that the mask matches with what we used earlier
        assert_array_equal(msk.ravel() + 0., node_msk.ravel() + 0.)

        source_surf_nodes = np.nonzero(node_msk)[0]

        sel = surf_voxel_selection.voxel_selection(v, float(radius),
                                        source_surf=source_surf,
                                        source_surf_nodes=source_surf_nodes,
                                        distance_metric='euclidian')

        qe = queryengine.SurfaceVerticesQueryEngine(sel)
        sl = Searchlight(sum_ds, queryengine=qe)
        r = sl(ds)

        # check whether they give the same results
        assert_array_equal(r.samples, m.samples)


class _Voxel_Count_Measure(Measure):
    # used to check voxel selection results
    is_trained = True
    def __init__(self, **kwargs):
        Measure.__init__(self, **kwargs)

    def _call(self, dset):
        return dset.nfeatures


def suite():
    """Create the suite"""
    return unittest.makeSuite(SurfTests)

if __name__ == '__main__':
    import runner
