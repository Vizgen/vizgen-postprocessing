import re
import sys
from importlib.metadata import version, PackageNotFoundError, distributions
from typing import Dict


from vpt_core import log


def get_vpt_version():
    try:
        res = version("vpt")
    except PackageNotFoundError:
        res = ""
        log.warning("Unable to identify vpt version")
    return res


def get_installed_versions() -> Dict[str, str]:
    optional_modules = ["cellpose", "stardist"]
    required_modules = ["geopandas", "shapely", "s3fs", "gcsfs", "rasterio"]
    vpt_modules = ["vpt_core"]
    plugins_re = re.compile("vpt[_-]plugin[_-].*")
    vpt_modules.extend([*set(filter(plugins_re.match, [d.metadata["Name"] for d in distributions()]))])

    result = {"python": sys.version}
    vpt_version = get_vpt_version()
    if vpt_version:
        result["vpt"] = vpt_version

    for module_name in vpt_modules:
        try:
            result[module_name] = version(module_name)
        except PackageNotFoundError:
            pass
    for module_name in required_modules:
        result[module_name] = version(module_name)
    for module_name in optional_modules:
        try:
            result[module_name] = version(module_name)
        except PackageNotFoundError:
            result[module_name] = "Not Installed"

    return result
