from typing import Dict, List, Tuple

import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from skimage import measure
from skimage.segmentation import watershed

from vpt.run_segmentation_on_tile.image import ImageSet
from vpt.segmentation.entity import Entity
from vpt.segmentation.stardist.seeds import StardistSeedsExtractor, StardistResult
from vpt.segmentation.utils.polygon_utils import generate_polygons_from_mask, smooth_and_simplify, \
    PolygonCreationParameters
from vpt.segmentation.utils.seg_result import SegmentationResult
from vpt.segmentation.watershed import key_stardist_model, key_seed_channel, key_entity_fill_channel
from vpt.segmentation.watershed.seeds import prepare_watershed_images, separate_merged_seeds
import vpt.log as log

import warnings


def to_sd_extractor_params(params: Dict) -> Dict:
    return {
        'normalization_range': params.get('normalization_range', (1, 99.8)),
        'min_size': params.get('min_diameter', 16),
        'max_size': params.get('max_diameter', 256)
    }


def get_watershed_seeds(
    images: ImageSet,
    segmentation_parameters: Dict,
    entity: Entity
):
    # Load the seed image
    seeds = np.array(images.as_list(segmentation_parameters.get(key_seed_channel, "")))
    if seeds.size == 0:
        raise AttributeError(
            f'{key_seed_channel} and {key_entity_fill_channel} must be specified in segmentation_parameters')

    log.info("stardist initialization")
    extractor = StardistSeedsExtractor(
        segmentation_parameters[key_stardist_model],
        **to_sd_extractor_params(segmentation_parameters)
    )

    log.info("extracting seeds")
    nuclei, seeds = extractor.extract_seeds(seeds, entity)
    log.info(f"detected seeds on each level: {str(',').join((str(len(x)) for x in nuclei))}")

    log.info("separate_merged_seeds")
    morph_r = segmentation_parameters.get('morphology_r', 20)
    seeds = separate_merged_seeds(seeds, morph_r)
    seeds = measure.label(seeds)

    return nuclei, seeds


def run_watershed(
        images: ImageSet,
        segmentation_parameters: Dict,
        entity: Entity) -> Tuple[List[StardistResult], np.ndarray]:
    warnings.filterwarnings('ignore', message='.*deprecated and will be removed in Pillow 10.*')  # shapely
    warnings.filterwarnings('ignore', message='.*the `scipy.ndimage.morphology` namespace is deprecated.*')
    warnings.filterwarnings('ignore', message='.*the `scipy.ndimage.measurements` namespace is deprecated.*')

    # Use the nuclear channel to derive the seeds for watershed
    nuclei, seeds = get_watershed_seeds(images, segmentation_parameters, entity)

    # If exporting nuceli, return early with the nuclear output
    if entity & Entity.Nucleus:
        result = np.zeros(seeds.shape, dtype=np.uint8)
        return nuclei, result

    # Load the cyto images
    cyto_images = np.array(images.as_list(segmentation_parameters.get(key_entity_fill_channel, "")))

    if key_entity_fill_channel in segmentation_parameters and cyto_images.size == 0:
        raise ValueError('Unable to find images in task data for the specified fill channel')

    # If no cyto images, return early with an empty result
    if cyto_images.size == 0:
        result = np.zeros(seeds.shape, dtype=np.uint8)
        return nuclei, result

    # Preprocess cyto channel to dmap and mask images
    log.info("prepare_watershed_images")
    dmap, watershed_mask = prepare_watershed_images(cyto_images)
    seeds[np.invert(watershed_mask)] = 0

    # Run 3D watershed
    log.info("watershed")
    result = watershed(
        dmap,
        seeds,
        mask=watershed_mask,
        connectivity=np.ones((3, 3, 3)),
        watershed_line=True
    )

    log.info("watershed finished")

    return nuclei, result


def polygons_from_stardist(sd_results: List[StardistResult], polygon_parameters: Dict) -> SegmentationResult:
    polys_data = []
    for z in range(len(sd_results)):
        for idx, star in enumerate(sd_results[z]):
            p = Polygon(np.fliplr(np.swapaxes(star.points, 0, 1)))
            polys_data.append(
                {
                    SegmentationResult.detection_id_field: idx + 1,
                    SegmentationResult.cell_id_field: idx,
                    SegmentationResult.z_index_field: z,
                    SegmentationResult.geometry_field: MultiPolygon([p])
                }
            )

    seg_result = SegmentationResult(list_data=polys_data)
    parameters = PolygonCreationParameters(**polygon_parameters)
    seg_result.update_geometry(smooth_and_simplify, radius=parameters.smoothing_radius,
                               tol=parameters.simplification_tol)
    seg_result.remove_polys(lambda poly: poly.area < parameters.minimum_final_area)
    return seg_result


# todo: return multiple results, 1 for each entity
def run_segmentation(images: ImageSet, segmentation_properties: Dict,
                     segmentation_parameters: Dict, polygon_parameters: Dict,
                     entity: Entity) -> SegmentationResult:

    if entity & Entity.Nucleus:
        nucleus, _ = run_watershed(images, segmentation_parameters, entity)
        return polygons_from_stardist(nucleus, polygon_parameters)

    if entity & Entity.Cells:
        _, cells = run_watershed(images, segmentation_parameters, entity)
        return generate_polygons_from_mask(cells, polygon_parameters)

    return SegmentationResult()
