from typing import Tuple, List

import numpy as np
import os
import cv2

from vpt.filesystem import filesystem_path_split
from vpt.segmentation.entity import Entity

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
from vpt.segmentation.stardist.star import StarPolygon  # noqa
from vpt.utils.output_tools import suppress_output  # noqa


def normalize(image: np.ndarray, pmin: float, pmax: float):
    if image[image > 0].size > 0:
        [mi, ma] = np.percentile(image[image > 0], [pmin, pmax], axis=None)
        return (image.astype(np.float32) - mi) / (ma - mi + 1e-20)
    else:
        return image.astype(np.float32)


StardistResult = List[StarPolygon]


class StardistSeedsExtractor:

    def __init__(self, model_path: str,
                 normalization_range: Tuple[float, float] = (1, 99.8),
                 min_size: int = 16,
                 max_size: int = 256):

        with suppress_output():
            from stardist.models import StarDist2D

            fs, path = filesystem_path_split(model_path)
            assert fs.protocol == 'file'  # Stardist only supports local filesystem
            path_parts = path.split(fs.sep)
            parent_path, model_name = fs.sep.join(path_parts[:-1]), path_parts[-1]

            self.model = StarDist2D(None, model_name, parent_path)
            if not self.model:
                raise ValueError("Invalid stardist model")

        self.min_size = min_size
        self.max_size = max_size
        self.nrm_range = normalization_range
        self.stars = None

    def run_prediction(self, image) -> StardistResult:
        normalized_image = normalize(image, self.nrm_range[0], self.nrm_range[1])
        with suppress_output():
            n_tiles = None if image.shape[0] < 1024 else (2, 2)
            _, details = self.model.predict_instances(normalized_image, n_tiles=n_tiles)
        points, center = details['coord'], details['points']
        result: List[StarPolygon] = []
        # filter results
        for i in range(len(center)):
            box = [[np.min(points[i][0]), np.max(points[i][0])], [np.min(points[i][1]), np.max(points[i][1])]]
            h = box[0][1] - box[0][0]
            w = box[1][1] - box[1][0]
            if h > image.shape[0] or w > image.shape[1]:
                # invalid image, return nothing
                return []

            # filter by bbox size
            if h > self.min_size and h < self.max_size and w > self.min_size and w < self.max_size:
                result.append(StarPolygon(center=center[i], points=points[i]))

        return result

    @staticmethod
    def result_to_mask(shape, results: StardistResult, star_scale: float = 0.6):
        target = np.zeros(shape, dtype=np.uint8)

        for star in results:
            triangles = []
            center = star.center
            points = star.points

            c = np.array([center[1], center[0]])
            for j in range(len(points[0]) >> 1):  # half number of points, for speed
                i1 = j + j
                i2 = (i1 + 2) % len(points[0])
                p1 = np.array([points[1][i1], points[0][i1]]) - c
                p2 = np.array([points[1][i2], points[0][i2]]) - c
                triangles.append([p1 * star_scale + c, p2 * star_scale + c, c])
            cv2.fillPoly(target, np.array(triangles, dtype=np.int32), (255, 255, 255))
        return target != 0

    def extract_seeds(self, seed_images: np.ndarray, entity: Entity) -> Tuple[List[StardistResult], np.ndarray]:
        vector = [self.run_prediction(x) for x in seed_images]
        shape = seed_images[0].shape
        rastr = np.array([StardistSeedsExtractor.result_to_mask(shape, x) for x in vector])

        # If the nuclear polygons are not needed, clear the data
        # A dummy array is created for logging
        if entity & Entity.Cells:
            vector = [[StarPolygon] * len(x) for x in vector]

        return vector, rastr
