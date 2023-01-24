import re
from dataclasses import dataclass
from typing import Set, List

from vpt import log
from vpt.filesystem.vzgfs import protocol_path_split, filesystem_for_protocol, \
    prefix_for_protocol, get_rasterio_environment, rasterio_open


@dataclass(frozen=True)
class ImagePath:
    channel: str
    z_layer: int
    full_path: str


@dataclass(frozen=True)
class RegexInfo:
    image_width: int
    image_height: int
    images: Set[ImagePath]


def get_paths_by_regex(regex: str) -> List[str]:
    protocol, regex = protocol_path_split(regex)
    fs = filesystem_for_protocol(protocol)
    parts = regex.split(fs.sep)

    for i in range(len(parts)):
        if '?' in parts[i]:
            break

    root = fs.sep.join(parts[:i])
    parts = parts[i:]

    def walk_req(rootdir, path_regex):
        if len(path_regex) == 0:
            return [rootdir]
        res = []

        try:
            _, dirs, files = next(fs.walk(rootdir, maxdepth=1))
        except StopIteration:
            return res

        if len(path_regex) == 1:
            for filename in files:
                if re.match(path_regex[0], filename):
                    res.append(filename)
            return res

        for dirname in dirs:
            if re.match(path_regex[0], dirname):
                walk_res = walk_req(fs.sep.join([rootdir, dirname]), path_regex[1:])
                for p in walk_res:
                    res.append(fs.sep.join([dirname, p]))

        return res

    paths = [fs.sep.join([root, path]) if root else path for path in walk_req(root, parts)]
    return [path for path in paths if fs.isfile(path)]


def parse_regex(regex: str) -> RegexInfo:
    width, height = 0, 0
    images = set()

    if '?P<stain>' not in regex or '?P<z>' not in regex:
        raise ValueError('Bad regular expression: named group "z" or "stain" is missed')

    paths = get_paths_by_regex(regex)
    protocol, regex = protocol_path_split(regex)
    fs = filesystem_for_protocol(protocol)

    for path in paths:
        match = re.match(regex, path)
        try:
            z = int(match.group('z'))
            stain = match.group('stain')
        except IndexError:
            log.warning(f'Regular expression should contain groups "z" and "stain". Path {path} has not that groups '
                        f'and will be skipped.')
            continue

        full_path = prefix_for_protocol(protocol) + fs.info(path)['name']

        with get_rasterio_environment(full_path):
            with rasterio_open(full_path) as tif:
                im_height, im_width = tif.height, tif.width
                if width and height and (im_width != width or im_height != height):
                    raise ValueError('Images sizes are not equal')
                width = im_width
                height = im_height

        images.add(ImagePath(stain, z, full_path))
    return RegexInfo(width, height, images)
