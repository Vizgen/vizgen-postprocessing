from vpt.filesystem import vzg_open
from vpt.utils.regex_tools import parse_regex


def _copy_between_filesystems(input_path: str, output_path: str):
    with vzg_open(input_path, 'rb') as i:
        with vzg_open(output_path, 'wb') as o:
            data = i.read()
            o.write(data)


def _copy_regex_images(input_regex_path, output_dir, output_separator):
    images = parse_regex(input_regex_path)
    images = images.images
    for im in images:
        stain, z, img_path = im.channel, im.z_layer, im.full_path
        _copy_between_filesystems(img_path, output_separator.join([output_dir, f'mosaic_{stain}_z{z}.tif']))
