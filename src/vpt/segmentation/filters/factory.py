from typing import List, Dict, Callable
import numpy as np
import cv2
from skimage import exposure

from vpt.segmentation.filters.description import Header, Filter


def normalization_clahe(image: np.ndarray, clahe_params: dict) -> np.ndarray:
    """
    Normalizes contrast using a CLAHE filter, scales dynamic range, and returns uint8 image
    """
    if image.std() < 0.1:
        return image.astype(np.uint8)
    normalized = exposure.equalize_adapthist(image, **clahe_params)
    subtract = normalized - normalized.min()
    return np.array((subtract / subtract.max()) * 255, dtype=np.uint8) if subtract.max() != 0 \
        else np.zeros(image.shape, dtype=np.uint8)


def normalize(image: np.ndarray) -> np.ndarray:
    return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)


def create_normalization_filter(p: dict) -> Filter:
    norm_type = p.get('type', 'default')
    if norm_type == 'CLAHE':
        args = {
            'clip_limit': p.get('clip_limit', 0.01),
            'kernel_size': np.array(p.get('filter_size', [100, 100]))
        }
        return lambda img: normalization_clahe(img, args)
    elif norm_type == 'default':
        return normalize
    raise TypeError(f'unsupported normalization type {norm_type}')


def create_blur_filter(p: dict) -> Filter:
    sz = p.get('size', 5)
    blur_type = p.get('type', 'average')
    if blur_type == 'median':
        return lambda image: cv2.medianBlur(image, ksize=sz)
    elif blur_type == 'gaussian':
        return lambda image: cv2.GaussianBlur(image, (sz, sz), 0)
    elif blur_type == 'average':
        return lambda image: cv2.blur(image, (sz, sz))
    raise TypeError(f'unsupported blur type {blur_type}')


def create_downsample_filter(p: dict) -> Filter:
    scale = p.get('scale', 2)
    return lambda image: cv2.resize(image, (0, 0), fx=1 / scale, fy=1 / scale)


def _filter_from_merlin(sImage: np.ndarray, thr: int) -> np.ndarray:
    ret = sImage
    if sImage.dtype == np.uint16:
        ret = cv2.convertScaleAbs(sImage, alpha=(255.0 / 65535.0))
    ret = cv2.adaptiveThreshold(ret, 1, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, thr, -1)
    ret = ret * sImage
    return ret


def create_merlin_watershed_filter(p: dict) -> Filter:
    threshold = int(255 * p.get('threshold', 0.5))
    return lambda image: _filter_from_merlin(image, threshold)


factory_map: Dict[str, Callable[[dict], Filter]] = {
    'normalize': create_normalization_filter,
    'blur': create_blur_filter,
    'downsample': create_downsample_filter,
    'merlin-ws': create_merlin_watershed_filter
}


def create_filter(h: Header) -> Filter:
    if h.name in factory_map:
        return factory_map[h.name](h.parameters)
    else:
        raise NameError(f'invalid filter name {h.name}')


def apply_sequence(image: np.ndarray, filters: List[Filter]) -> np.ndarray:
    for f in filters:
        if f is not None:
            image = f(image)
    return image


def create_filter_by_sequence(headers: List[Header]) -> Filter:
    filters = [create_filter(h) for h in headers] if headers else []
    return lambda image: apply_sequence(image, filters)
