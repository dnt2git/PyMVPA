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

This is a demonstration of how a self-organizing map (SOM) can be used
to map high-dimensional data into a two-dimensional representation. For the sake
of an easy visualization 'high-dimensional' in this case is 3D.

In general SOMs might be useful for visualizing high-dimensional data in terms
of its similarity structure. Especially large SOMs (i.e. large number of
Kohonen units) are known to perform mappings that preserve the topology of the
original data, i.e. neighboring data points in input space will also be
represented in adjacent locations on the SOM.

In this example the SOM will map a number of colors into a rectangular area.
"""

from mvpa.suite import *

"""
First, we define some colors as RGB values from the interval (0,1), i.e. with
white being (1, 1, 1) and black being (0, 0, 0).
"""

colors = [[0., 0., 0.],
          [0., 0., 1.],
          [0., 1., 0.],
          [1., 0., 0.],
          [0., 1., 1.],
          [1., 0., 1.],
          [1., 1., 0.],
          [1., 1., 1.],
          [.33, .33, .33],
          [.5, .5, .5],
          [.66, .66, .66]]

# store the names of the colors for visualization later on
color_names = \
        ['black', 'blue', 'green', 'red', 'cyan',
         'violet', 'yellow', 'white', 'darkgrey',
         'mediumgrey', 'lightgrey']

"""
Since we are going to use a mapper, we will put the color vectors into a
dataset. To be able to do this, we will assign an arbitrary label, although
it will not be used at all, since this SOM mapper uses an unsupervised training
algorithm.
"""

ds = Dataset(samples=colors, labels=1)

"""
Now we can instantiate the mapper. It will internally use a so-called Kohonen
layer to map the data onto. We tell the mapper to use a rectangular layer with
30 x 20 units. This will be the output space of the mapper. Additionally, we
tell it to train the network using 400 iterations and to use custom learning
rate.
"""

som = SimpleSOMMapper((30, 20), 400, learning_rate=0.05)

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

P.imshow(som.K, origin='lower')

"""
And now, let's take a look onto which coordinates the initial training
prototypes were mapped to. The get those coordinates we can simply feed
the training data to the mapper and plot the output.
"""

mapped = som(colors)

P.title('Color SOM')
# SOM's kshape is (rows x columns), while matplotlib wants (X x Y)
for i, m in enumerate(mapped):
    P.text(m[1], m[0], color_names[i], ha='center', va='center',
           bbox=dict(facecolor='white', alpha=0.5, lw=0))


"""
But now, let's do something more interesting and take a look at similarity
structures in fMRI data. This example makes use of the small dataset shipped
with the source distribution of PyMVPA. First, we loaded the full dataset,
while preserving the literal labels of each sample ...
"""

attr = SampleAttributes('data/attributes_literal.txt', literallabels=True)
ds = NiftiDataset(samples='data/bold.nii.gz',
                  labels=attr.labels,
                  chunks=attr.chunks,
                  mask='data/mask.nii.gz',
                  labels_map=True)

"""
... detrend the whole timeseries ...
"""

detrend(ds, perchunk=True, model='linear')

"""
... and finally select four of the included stimulus conditions for this
example: faces, houses, shoes and chairs.
"""

ds = ds.select(labels=[ds.labels_map[i] for i in ['face', 'house', 'shoe', 'chair']])

"""
For a significant speed-up of the procedure, we simply use the 5% of the voxels
with the highest ANOVA F-scores.
"""

fs = SensitivityBasedFeatureSelection(
        OneWayAnova(),
        FractionTailSelector(0.05,
                             tail='upper',
                             mode='select'))
ds = fs(ds)[0]

"""
The last preprocessing step is a simple normalization of all thresholded
features.
"""

zscore(ds, perchunk=True, targetdtype='float32')

"""
More or less identical to the previous example we train a SOM on this new fMRI
dataset. The only difference is a slightly larger Kohonen layer and an adjusted
initial learning rate. Due to the size of the dataset and the larger network
the SOM training will take one or two minutes, therefore we enable some debug
output to entertain ourselves while waiting...
"""

if __debug__:
  debug.active += ['SOM']


som = SimpleSOMMapper((40, 40), 400, learning_rate=0.001)
som.train(ds)

"""
After the training has been completed, we can now take a look at the data
structure by simply mapping the whole dataset using the SOM and plot the
resulting 2D vectors.
"""

mapped = som(ds.samples)

# start new figure
P.figure()
P.title('Object category fMRI SOM')

# we need a reversed labels map for the figure legend
rlm = dict([(v, k) for k, v in ds.labels_map.iteritems()])

# define arbitrary colors for each stimulus condition
pcolors = ['red', 'blue', 'yellow', 'black']

# To render legend appropriately on older version of matplotlib
# we need to store all the plots and generate legend manually
splots, labels = [], []
for l,color in zip(ds.uniquelabels, colors):
    labels += [str(rlm[l])]
    splots.append(P.scatter(mapped[ds.labels==l, 0],
                            mapped[ds.labels==l, 1],
                            color=color, label=labels[-1]))
# generate legend
P.legend(splots, labels)

# show the figure
if cfg.getboolean('examples', 'interactive', True):
    P.show()
