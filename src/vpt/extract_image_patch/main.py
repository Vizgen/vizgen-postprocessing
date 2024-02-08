import argparse

from PIL import Image
from vpt.extract_image_patch.cmd_args import ExtractImagePatchArgs, get_parser, validate_args
from vpt.utils.process_patch import load_paths_args, make_png, process_patch
from vpt_core import log
from vpt_core.io.vzgfs import initialize_filesystem, io_with_retries


def extract_image_patch(args: argparse.Namespace):
    extract_args = ExtractImagePatchArgs(**vars(args))
    validate_args(extract_args)
    log.info("Extract image patch started")
    updated_args = load_paths_args(extract_args)
    patch = process_patch(updated_args)
    image = Image.fromarray(patch)
    io_with_retries(
        make_png(extract_args.output_patch),
        "wb",
        lambda f: image.save(f, format="PNG"),
    )
    log.info("Extract image patch finished")


if __name__ == "__main__":
    initialize_filesystem()
    extract_image_patch(get_parser().parse_args())
