import os.path
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import pytest
import cv2

from vpt.filesystem import initialize_filesystem
from vpt.utils.regex_tools import RegexInfo, parse_regex, ImagePath
from tests.base_case import BaseCase


class RegexPathCase(BaseCase):

    def __init__(self, name: str, regex_path: str, image_sizes: List[Tuple[int, int]],
                 z: List[int], stains: List[str], result: Optional[RegexInfo]):
        super(RegexPathCase, self).__init__(name)
        self.regex_path = regex_path
        self.image_sizes = image_sizes
        self.z = z
        self.stains = stains
        self._save_dir = ''

        self.result = result

    def generate_dataset(self, save_dir='./tiles'):
        if not os.path.exists(save_dir):
            os.mkdir(save_dir)
            self._save_dir = save_dir
        for size, z, stain in zip(self.image_sizes, self.z, self.stains):
            cv2.imwrite(f'{save_dir}/tile_{stain}_z{z}.tif', np.zeros(size))

    def clean(self):
        if self._save_dir and os.path.exists(self._save_dir):
            shutil.rmtree(self._save_dir)


REGEX_PATH_CASES = [
    RegexPathCase(
        name='same_sizes',
        image_sizes=[(200, 100)] * 10,
        z=[1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
        stains=['CB3', 'CB2', 'CB3', 'CB2', 'CB3', 'DApI', 'CB3', 'DApI', 'CB1', 'CB5'],
        regex_path=r'tiles/tile_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif',
        result=RegexInfo(100, 200, {
            ImagePath(z_layer=1, channel='CB3', full_path=Path('tiles/tile_CB3_z1.tif').absolute().as_posix()),
            ImagePath(z_layer=1, channel='CB2', full_path=Path('tiles/tile_CB2_z1.tif').absolute().as_posix()),
            ImagePath(z_layer=2, channel='CB3', full_path=Path('tiles/tile_CB3_z2.tif').absolute().as_posix()),
            ImagePath(z_layer=2, channel='CB2', full_path=Path('tiles/tile_CB2_z2.tif').absolute().as_posix()),
            ImagePath(z_layer=3, channel='CB3', full_path=Path('tiles/tile_CB3_z3.tif').absolute().as_posix()),
            ImagePath(z_layer=3, channel='DApI', full_path=Path('tiles/tile_DApI_z3.tif').absolute().as_posix()),
            ImagePath(z_layer=4, channel='CB3', full_path=Path('tiles/tile_CB3_z4.tif').absolute().as_posix()),
            ImagePath(z_layer=4, channel='DApI', full_path=Path('tiles/tile_DApI_z4.tif').absolute().as_posix()),
            ImagePath(z_layer=5, channel='CB1', full_path=Path('tiles/tile_CB1_z5.tif').absolute().as_posix()),
            ImagePath(z_layer=5, channel='CB5', full_path=Path('tiles/tile_CB5_z5.tif').absolute().as_posix())
        })
    ),
    RegexPathCase(
        name='absolute_path',
        image_sizes=[(200, 100)] * 10,
        z=[1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
        stains=['CB3', 'CB2', 'CB3', 'CB2', 'CB3', 'DApI', 'CB3', 'DApI', 'CB1', 'CB5'],
        regex_path=Path('./tiles').absolute().as_posix() + r'/tile_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif',
        result=RegexInfo(100, 200,
                         {ImagePath(z_layer=1, channel='CB3',
                                    full_path=(Path('tiles').absolute() / 'tile_CB3_z1.tif').as_posix()),
                          ImagePath(z_layer=1, channel='CB2',
                                    full_path=(Path('tiles').absolute() / 'tile_CB2_z1.tif').as_posix()),
                          ImagePath(z_layer=2, channel='CB3',
                                    full_path=(Path('tiles').absolute() / 'tile_CB3_z2.tif').as_posix()),
                          ImagePath(z_layer=2, channel='CB2',
                                    full_path=(Path('tiles').absolute() / 'tile_CB2_z2.tif').as_posix()),
                          ImagePath(z_layer=3, channel='CB3',
                                    full_path=(Path('tiles').absolute() / 'tile_CB3_z3.tif').as_posix()),
                          ImagePath(z_layer=3, channel='DApI',
                                    full_path=(Path('tiles').absolute() / 'tile_DApI_z3.tif').as_posix()),
                          ImagePath(z_layer=4, channel='CB3',
                                    full_path=(Path('tiles').absolute() / 'tile_CB3_z4.tif').as_posix()),
                          ImagePath(z_layer=4, channel='DApI',
                                    full_path=(Path('tiles').absolute() / 'tile_DApI_z4.tif').as_posix()),
                          ImagePath(z_layer=5, channel='CB1',
                                    full_path=(Path('tiles').absolute() / 'tile_CB1_z5.tif').as_posix()),
                          ImagePath(z_layer=5, channel='CB5',
                                    full_path=(Path('tiles').absolute() / 'tile_CB5_z5.tif').as_posix())})
    ),
    RegexPathCase(
        name='diff_sizes',
        image_sizes=[(100, 200)] * 4 + [(100, 100)] + [(200, 100)] * 3,
        z=[1, 1, 2, 2, 3, 3, 4, 4],
        stains=['CB3', 'CB2', 'CB3', 'CB2', 'CB3', 'DApI', 'CB3', 'DApI'],
        regex_path=r'tiles/tile_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif',
        result=None
    )
]

initialize_filesystem()


@pytest.mark.parametrize('case', REGEX_PATH_CASES, ids=str)
def test_parse_regex(case: RegexPathCase) -> None:
    case.generate_dataset()
    try:
        result = parse_regex(case.regex_path)
        assert result == case.result
    except ValueError:
        assert case.result is None
    finally:
        case.clean()
