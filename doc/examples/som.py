#!/usr/bin/env python
#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""
Self-organizing Maps
====================

.. index:: mapper, self-organizing map, SOM, SimpleSOMMapper

This is a demonstration that shows how a self-organizing map (SOM) can be used
to map high-dimensional data into a two-dimensional representation. For the sake
of an easy visualization 'high-dimensional' in this case is 3D.

In general SOMs might be useful for visualizing high-dimensional data in terms
of the its similarity structure. Especially large SOMs (i.e. large number of
Kohonen units) are known to perform mappings that preserve the topology of the
original data, i.e. neighboring data points in input space will also be
represented in adjacent locations on the SOM.

In this example the SOM will map a number of colors into a rectangular area.
"""

import pylab as P

from mvpa import cfg
from mvpa.datasets import Dataset
from mvpa.mappers.som import SimpleSOMMapper

"""
First, we define some colors as RGB values from the interval (0,1), i.e. with
white being (1, 1, 1) and black being (0, 0, 0).
"""

colors = [[0., 0., 0.],    # black
          [0., 0., 1.],    # blue
          [0., 1., 0.],    # green
          [1., 0., 0.],    # red
          [0., 1., 1.],    # cyan
          [1., 0., 1.],    # violet
          [1., 1., 0.],    # yellow
          [1., 1., 1.],    # white
          [.33, .33, .33], # darkgrey
          [.5, .5, .5],    # mediumgrey
          [.66, .66, .66]] # lightgrey

"""
Since we are going to use a mapper, we will put the color vectors into a
dataset. To be able to do this, we will assign an arbitrary label, although
it will not be used at all, since this SOM mapper uses an unsupervised training
algorithm.
"""

ds = Dataset(samples=colors, labels=1)

"""
Now we can instanciate the mapper. It will internally use a so-called Kohonen
layer to map the data onto. We tell the mapper to use a rectangular layer with
30 x 20 units. This will be the output space of the mapper. Additionally, we
tell it to train the network using 400 iterations and to use some learning rate.
"""

som = SimpleSOMMapper(30, 20, 400, learning_rate=0.05)

"""
Finally, we train the mapper with the previously defined 'color' dataset.
"""

som.train(ds)

"""
Each unit in the Kohonen layer can be treated as a pointer into the
high-dimensional input space, that can be queried to inspect which
input subspaces the SOM maps into certain sections of its 2D output space.
The color-mapping generated by this example's SOM can be shown with a single
matplotlib call:
"""

P.imshow(som.units)

if cfg.getboolean('examples', 'interactive', True):
    P.show()
