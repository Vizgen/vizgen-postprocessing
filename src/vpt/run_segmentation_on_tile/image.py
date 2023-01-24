from typing import Tuple, List, Dict, Set

import numpy as np
import rasterio

from vpt.filesystem.vzgfs import get_rasterio_environment, rasterio_open
from vpt.run_segmentation_on_tile.input_utils import ImageInfo
from vpt.segmentation.filters.factory import create_filter_by_sequence
from vpt.segmentation.types import SegTask


class ImageSet(Dict[str, Dict[int, np.ndarray]]):
    def z_levels(self) -> Set[int]:
        return set().union(*self.values())

    def as_list(self, key: str) -> List[np.ndarray]:
        return list(self.get(key, {}).values())

    def as_stack(self, order: List[str] = None):
        if not order:
            return np.array([np.stack([z_stack[z] for z_stack in self.values()], axis=-1) for z in self.z_levels()])
        return np.array([np.stack([self[k][z] for k in order], axis=-1) for z in self.z_levels()])


def read_tile(window: Tuple[int, int, int, int], path: str,
              num_tries: int = 5) -> np.ndarray:
    num_retries = num_tries - 1

    for try_number in range(1, num_tries + 1):
        try:
            with get_rasterio_environment(path):
                with rasterio_open(path) as file:
                    image = file.read(1, window=rasterio.windows.Window(window[0], window[1],
                                                                        window[2], window[3]))
        except OSError:
            if try_number + 1 <= num_tries:
                print(f'Failed to read {path} at {window}. Retrying {try_number}/{num_retries}.')
            continue
        break
    else:
        raise IOError(f'Failed to read {path} at {window}')

    return np.squeeze(image)


def get_segmentation_images(images_info: List[ImageInfo],
                            window_info: Tuple[int, int, int]) -> ImageSet:
    images = ImageSet()
    for image_info in images_info:
        if not images.get(image_info.channel):
            images[image_info.channel] = {}
        images[image_info.channel][image_info.z_layer] = read_tile(window_info, image_info.full_path)
    return images


def get_prepared_images(task: SegTask, images: ImageSet) -> Tuple[ImageSet, Tuple[int, int]]:
    cur_images = ImageSet()
    result_shape, scale = None, (1, 1)
    for input_info in task.task_input_data:
        cur_images[input_info.image_channel] = {}
        image_filter = create_filter_by_sequence(input_info.image_preprocessing)
        for z, im in images[input_info.image_channel].items():
            if z not in task.z_layers:
                continue

            cur_im = image_filter(im)
            if result_shape is None:
                result_shape = cur_im.shape[:2]
                scale = (im.shape[0] / cur_im.shape[0], im.shape[1] / cur_im.shape[1])
            elif result_shape[:2] != cur_im.shape[:2]:
                raise ValueError('Invalid preprocessing scale: input images for segmentation after postprocessing '
                                 'should have same sizes')
            cur_images[input_info.image_channel][z] = cur_im

    return cur_images, scale
