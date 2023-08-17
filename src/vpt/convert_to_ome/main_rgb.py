import argparse
import contextlib
import os
from typing import List, Optional

import pyvips  # noqa
from vpt_core.io.vzgfs import initialize_filesystem

from vpt.convert_to_ome.rgb_cmd_args import ConvertToRGBOmeArgs, get_parser, validate_args
from vpt.convert_to_ome.tiffutils import (
    add_ome_metadata,
    extract_channel_from_filename,
    read_image,
    save_as_pyramidal_image,
)

env_path_list = os.environ["PATH"].split(";")
vips = [x for x in env_path_list if os.path.exists(os.path.join(x, "vips.exe"))]
if len(vips) > 0:
    os.environ["PATH"] = vips[0] + ";" + os.environ["PATH"]


def convert_to_ome_rgb(args: argparse.Namespace) -> None:
    convert_args = ConvertToRGBOmeArgs(
        args.input_image_red, args.input_image_green, args.input_image_blue, args.output_image, args.overwrite
    )
    validate_args(convert_args)

    inputs: List = []
    channel_names: List[Optional[str]] = []

    with contextlib.ExitStack() as stack:
        images = []
        for input_path in convert_args.input_path_red, convert_args.input_path_green, convert_args.input_path_blue:
            if input_path is None:
                inputs.append(None)
                channel_names.append(None)
            else:
                images.append(stack.enter_context(read_image(input_path)))
                image = pyvips.Image.arrayjoin(images[-1].bandsplit(), across=1)
                inputs.append(image)

                channel_names.append(extract_channel_from_filename(input_path))

        # Find a non-none channel image
        img = next(inp for inp in inputs if inp is not None)
        image_type = img.format
        image_width, image_height = img.width, img.height

        for i in range(len(inputs)):
            if inputs[i] is None:
                inputs[i] = pyvips.Image.black(image_width, image_height)

        rgb = pyvips.Image.arrayjoin(inputs, across=1)

        add_ome_metadata(rgb, image_width, image_height, image_type, 3, channel_names)

        save_as_pyramidal_image(rgb, convert_args.output_path)


if __name__ == "__main__":
    initialize_filesystem()
    convert_to_ome_rgb(get_parser().parse_args())
