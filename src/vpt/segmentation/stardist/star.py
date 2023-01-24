from dataclasses import dataclass

import numpy as np


@dataclass
class StarPolygon:
    center: np.ndarray
    points: np.ndarray
