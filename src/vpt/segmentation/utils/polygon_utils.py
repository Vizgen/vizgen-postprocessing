from dataclasses import dataclass
from typing import Dict

import cv2
import numpy as np
from shapely import geometry
from shapely.validation import make_valid
import vpt.log as log
from vpt.segmentation.utils.seg_result import SegmentationResult


@dataclass(frozen=True)
class PolygonCreationParameters:
    simplification_tol: int
    smoothing_radius: int
    minimum_final_area: int


def generate_polygons_from_mask(mask: np.ndarray, polygon_parameters: Dict) -> SegmentationResult:
    log.info("generate_polygons_from_mask")
    parameters = PolygonCreationParameters(**polygon_parameters)
    seg_result = get_polygons_from_mask(mask, parameters.smoothing_radius, parameters.simplification_tol)
    seg_result.remove_polys(lambda poly: poly.area < parameters.minimum_final_area)
    return seg_result


def make_polygons_from_label_matrix(entity_id, label_matrix):
    '''
    Creates a list of Polygon objects from a label matrix
    '''
    contours, _ = cv2.findContours((label_matrix == entity_id).astype("uint8"), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for c in contours:
        if c.shape[0] < 4:
            continue

        # Create a valid polygon object
        p = geometry.Polygon(c[:, 0, :]).buffer(0)
        p = largest_geometry(p)
        if p.is_empty:
            continue
        polys.append(p)

    return polys


def get_polygons_from_mask(mask: np.ndarray, smoothing_radius, simplification_tolerance) -> SegmentationResult:
    '''
    Accepts either a 2D or 3D numpy array label matrix, returns a SegmentationResult of
    MultiPolygons surrounding each label/mask. Performs smoothing and simplification of
    Polygons before returning.
    '''

    # If passed 2D data, expand axes so that z-level indexing will work
    if len(mask.shape) == 2:
        mask = np.expand_dims(mask, axis=0)

    polys_data = []
    for z in range(mask.shape[0]):
        list_of_mask_ids = np.unique(mask[z, :, :])
        log.info(f"get_polygons_from_mask: z={z}, labels:{len(list_of_mask_ids)}")
        for idx, mask_id in enumerate(list_of_mask_ids):
            # Value of zero is background, skip
            if mask_id == 0:
                continue

            try:
                # Convert each region of the entity into a polygon
                raw_polys = make_polygons_from_label_matrix(mask_id, mask[z, :, :])

                polys = [smooth_and_simplify(raw_poly, smoothing_radius, simplification_tolerance) for raw_poly in raw_polys]
                polys = [poly for poly in polys if not poly.is_empty]

                # If smoothing and simplifying eliminated all polygons, don't add them to the output
                if len(polys) == 0:
                    continue

                # Transform the list of 1 or more mask polygons into a multipolygon
                multi_poly = convert_to_multipoly(make_valid(geometry.MultiPolygon(polys)))
                polys_data.append(
                    {
                        SegmentationResult.detection_id_field: idx + 1,
                        SegmentationResult.cell_id_field: mask_id,
                        SegmentationResult.z_index_field: z,
                        SegmentationResult.geometry_field: multi_poly
                    }
                )
            except ValueError:
                # If the MultiPolygon is not created properly, it is probably because the
                # geometry is low quality or otherwise strange. In that situation, it's ok
                # to discard the geometry by catching the exception and not appending the
                # geometry to the output.
                log.info(f"Mask id {mask_id} could not be converted to a polygon.")

    return SegmentationResult(list_data=polys_data)


def get_upscale_matrix(scale_x: int, scale_y: int) -> np.ndarray:
    return np.array([[scale_x, 0, 0], [0, scale_y, 0], [0, 0, 1]])


def smooth_and_simplify(poly, radius, tol):
    if isinstance(poly, geometry.MultiPolygon):
        buffered_shapes = (p.buffer(-radius).buffer(radius * 2).buffer(-radius) for p in poly.geoms)
        buffered_multipolygons = (p if type(p) is geometry.MultiPolygon else geometry.MultiPolygon([p]) for p in
                                  buffered_shapes)
        buffered_polygons = (p for mp in buffered_multipolygons for p in mp.geoms)
        poly = geometry.MultiPolygon(buffered_polygons)
    elif isinstance(poly, geometry.Polygon):
        poly = poly.buffer(-radius).buffer(radius * 2).buffer(-radius)
    return largest_geometry(poly.simplify(tolerance=tol))


def largest_geometry(shape):
    '''
    If passed a Polygon, returns the Polygon.
    If passed a MultiPolygon, returns the largest Polygon region.
    Else throws TypeError
    '''
    if type(shape) is geometry.Polygon:
        return shape
    elif type(shape) is geometry.MultiPolygon:
        sizes = np.array([(idx, g.area) for idx, g in enumerate(shape.geoms)])
        idx_largest = sizes[sizes[:, 1].argmax(), 0]
        return shape.geoms[int(idx_largest)]
    else:
        raise TypeError(f"Objects of type {type(shape)} are not supported")


def convert_to_multipoly(shape):
    if type(shape) is geometry.Polygon:
        return geometry.multipolygon.MultiPolygon([shape])
    elif type(shape) is geometry.MultiPolygon:
        return shape
    else:
        # If type is not Polygon or Multipolygon, the shape
        # is strange / small and should be rejected
        return geometry.MultiPolygon()
