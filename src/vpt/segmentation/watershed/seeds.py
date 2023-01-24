from typing import Tuple

import numpy as np
from pyclustering.cluster import kmedoids
from scipy import ndimage
from skimage import filters
from skimage import morphology, measure

"""
This module contains utility functions for preparing images for
watershed segmentation.
"""


def separate_merged_seeds(seedsIn: np.ndarray, morph_r: int = 20) -> np.ndarray:
    """Separate seeds that are merged in 3 dimensions but are separated
    in some 2 dimensional slices.

    Args:
        seedsIn: a 3 dimensional binary numpy array arranged as (z,x,y) where
            True indicates the pixel corresponds with a seed.
    Returns: a 3 dimensional binary numpy array of the same size as seedsIn
        indicating the positions of seeds after processing.
    """

    def create_region_image(shape, c):
        region = np.zeros(shape, dtype=np.uint8)
        for x in c.coords:
            region[x[0], x[1], x[2]] = 1
        return region

    diskStruct = morphology.disk(morph_r)

    components = measure.regionprops(measure.label(seedsIn))
    seeds = np.zeros(seedsIn.shape, dtype=np.uint8)
    for c in components:
        seedImage = create_region_image(seeds.shape, c)
        localProps = [measure.regionprops(measure.label(x)) for x in seedImage]
        seedCounts = [len(x) for x in localProps]

        if all([x < 2 for x in seedCounts]):
            goodFrames = [i for i, x in enumerate(seedCounts) if x == 1]
            goodProperties = [y for x in goodFrames for y in localProps[x]]
            seedPositions = np.round([np.median(
                [x.centroid for x in goodProperties], axis=0)]).astype(int)
        else:
            goodFrames = [i for i, x in enumerate(seedCounts) if x > 1]
            goodProperties = [y for x in goodFrames for y in localProps[x]]
            goodCentroids = [x.centroid for x in goodProperties]
            km = kmedoids.kmedoids(
                goodCentroids,
                np.random.choice(np.arange(len(goodCentroids)),
                                 size=np.max(seedCounts)))
            km.process()
            seedPositions = np.round(
                [goodCentroids[x] for x in km.get_medoids()]).astype(int)

        for s in seedPositions:
            for f in goodFrames:
                seeds[f, s[0], s[1]] = 1

    seeds = ndimage.binary_dilation(
        seeds, structure=ndimage.generate_binary_structure(3, 1))
    seeds = np.array([ndimage.binary_dilation(
        x, structure=diskStruct) for x in seeds])

    return seeds


def prepare_watershed_images(watershedImageStack: np.ndarray
                             ) -> Tuple[np.ndarray, np.ndarray]:
    """Prepare the given images as the input image for watershedding.

    A watershed mask is determined using an adaptive threshold and the watershed
    images are inverted so the largest values in the watershed images become
    minima and then the image stack is normalized to have values between 0
    and 1.

    Args:
        watershedImageStack: a 3 dimensional numpy array containing the images
            arranged as (z, x, y).
    Returns: a tuple containing the normalized watershed images and the
        calculated watershed mask
    """
    filterSize = int(2 * np.floor(watershedImageStack.shape[1] / 16) + 1)

    watershedMask = np.array(
        [
            ndimage.binary_fill_holes(x > filters.threshold_local(x, filterSize, method='mean', mode='wrap'))
            for x in watershedImageStack
        ]
    )

    img_min, img_max = np.min(watershedImageStack), np.max(watershedImageStack)

    if img_max > img_min:
        normalizedWatershed = 1 - (watershedImageStack - img_min) / (img_max - img_min)
    else:
        normalizedWatershed = 1 - watershedImageStack

    normalizedWatershed[np.invert(watershedMask)] = 1

    return normalizedWatershed, watershedMask
