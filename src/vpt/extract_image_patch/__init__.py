import argparse

import vpt.extract_image_patch.cmd_args as cmd_args

get_parser = cmd_args.get_parser
clahe_params = {"clip_limit": 0.01, "kernel_size": [100, 100]}


def run(args: argparse.Namespace):
    from vpt.extract_image_patch.main import extract_image_patch

    extract_image_patch(args)
