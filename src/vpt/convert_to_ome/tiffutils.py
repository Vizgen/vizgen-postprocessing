import contextlib
import os
import re
import tempfile
from typing import List

import numpy as np

from vpt.filesystem.vzgfs import protocol_path_split, Protocol, filesystem_for_protocol, filesystem_path_split

env_path_list = os.environ['PATH'].split(';')
vips = [x for x in env_path_list if os.path.exists(os.path.join(x, 'vips.exe'))]
if len(vips) > 0:
    os.environ['PATH'] = vips[0] + ";" + os.environ['PATH']

import pyvips # noqa

format_to_dtype = {
    'uchar': np.uint8,
    'char': np.int8,
    'ushort': np.uint16,
    'short': np.int16,
    'uint': np.uint32,
    'int': np.int32,
    'float': np.float32,
    'double': np.float64,
    'complex': np.complex64,
    'dpcomplex': np.complex128,
}


def add_ome_metadata(im: pyvips.Image, image_width: int, image_height: int,
                     image_type: str, num_channels: int, channel_names: List) -> None:
    channel_name_attribs = ['' if name is None else f' Name="{name}"' for name in channel_names]
    channel_tags = '\n'.join(f'<Channel ID="Channel:0:{i}" SamplesPerPixel="1"{channel_name_attribs[i]}/>'
                             for i in range(num_channels))
    tiffdata_tags = f'<TiffData IFD="0" PlaneCount="{num_channels}"/>'

    im.set_type(pyvips.GValue.gint_type, "page-height", image_height)
    im.set_type(pyvips.GValue.gstr_type, "image-description",
                f"""<?xml version="1.0" encoding="UTF-8"?>
    <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2016-06 \
        http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd">
        <Image ID="Image:0">
            <Pixels DimensionOrder="XYCZT"
                    ID="Pixels:0"
                    SizeC="{num_channels}"
                    SizeT="1"
                    SizeX="{image_width}"
                    SizeY="{image_height}"
                    SizeZ="1"
                    Type="{np.dtype(format_to_dtype[image_type]).name}">
                    {channel_tags}
                    {tiffdata_tags}
            </Pixels>
        </Image>
    </OME>""")


def extract_channel_from_filename(path):
    fs, path_inside_fs = filesystem_path_split(path)
    match = re.match('mosaic_(?P<name>.+?)_z[0-9]+', path_inside_fs.split(fs.sep)[-1].rsplit('.')[0])
    try:
        channel_name = match.group('name')
    except (IndexError, AttributeError):
        channel_name = None
    return channel_name


@contextlib.contextmanager
def read_image(path: str, **kwargs) -> pyvips.Image:
    kwargs.pop('access', None)

    protocol, path_inside_fs = protocol_path_split(path)

    if protocol == Protocol.LOCAL:
        im = pyvips.Image.new_from_file(path, access='sequential', **kwargs)
        yield im.copy()
    else:
        tempdir = tempfile.mkdtemp()
        fs = filesystem_for_protocol(protocol)
        filename = path_inside_fs.split(fs.sep)[-1]

        local_path = os.path.join(tempdir, filename)

        fs.get_file(path_inside_fs, local_path)

        im = pyvips.Image.new_from_file(local_path, access='sequential', **kwargs)

        yield im.copy()

        os.unlink(local_path)


def write_to_local_file(im: pyvips.Image, path: str):
    im.write_to_file(path, pyramid=True, tile=True, subifd=True, compression='deflate', bigtiff=True)


def save_as_pyramidal_image(im: pyvips.Image, path: str) -> None:
    protocol, path_inside_fs = protocol_path_split(path)
    fs = filesystem_for_protocol(protocol)

    parent_dir = fs.sep.join(path_inside_fs.split(fs.sep)[:-1])
    fs.mkdirs(parent_dir, exist_ok=True)

    if protocol == Protocol.LOCAL:
        write_to_local_file(im, path)
    else:
        tempdir = tempfile.mkdtemp()
        filename = path_inside_fs.split(fs.sep)[-1]

        local_path = os.path.join(tempdir, filename)

        write_to_local_file(im, local_path)

        fs.put_file(local_path, path_inside_fs)

        os.unlink(local_path)
