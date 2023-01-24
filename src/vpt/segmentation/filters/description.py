from dataclasses import dataclass
from typing import Callable
import numpy as np

Filter = Callable[[np.ndarray], np.ndarray]


@dataclass
class Header:
    name: str
    parameters: dict

    def __init__(self, name: str, parameters=None):
        if parameters is None:
            parameters = {}
        self.name = name
        self.parameters = parameters
