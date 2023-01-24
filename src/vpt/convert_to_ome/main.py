import argparse

from vpt.convert_to_ome.cmd_args import get_parser, ConvertToOmeArgs, validate_args
from vpt.convert_to_ome.tiffutils import add_ome_metadata, read_image, save_as_pyramidal_image, \
    extract_channel_from_filename
from vpt.filesystem import initialize_filesystem, filesystem_path_split
import vpt.log as log


def convert_file(input_path: str, output_path: str) -> None:
    log.info(f'processing file:{input_path}')
    with read_image(input_path) as im:
        channel_name = extract_channel_from_filename(input_path)

        add_ome_metadata(im, im.width, im.height, im.format, 1, [channel_name])

        save_as_pyramidal_image(im, output_path)


def convert_dir(input_path: str, output_path: str) -> None:
    input_fs, input_path_inside_fs = filesystem_path_split(input_path)
    output_fs, output_path_inside_fs = filesystem_path_split(output_path)
    log.info(f'processing dir:{input_path}')

    for input_image_path in input_fs.glob(input_fs.sep.join([input_path_inside_fs, '*.tif'])):
        filename = input_image_path.split(input_fs.sep)[-1]
        stem = filename.split('.')[0]
        output_image_path = output_fs.sep.join([output_path_inside_fs, f'{stem}.ome.tif'])

        convert_file(input_image_path, output_image_path)


def convert_to_ome(args: argparse.Namespace):
    args = ConvertToOmeArgs(args.input_image, args.output_image, args.overwrite)
    validate_args(args)
    log.info("convert to ome started")

    input_fs, input_path_inside_fs = filesystem_path_split(args.input_path)

    if input_fs.isfile(input_path_inside_fs):
        convert_file(args.input_path, args.output_path)
    else:
        convert_dir(args.input_path, args.output_path)
    log.info("convert to ome finished")


if __name__ == '__main__':
    initialize_filesystem()
    convert_to_ome(get_parser().parse_args())
