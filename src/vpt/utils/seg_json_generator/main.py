import json
import os.path
from dataclasses import asdict
from typing import Dict, Optional

from vpt_core.io.vzgfs import io_with_retries

from vpt.utils.seg_json_generator.cmd_args import GenerateJsonArgs, parse_args
from vpt.utils.seg_json_generator.input_utils import AlgorithmParameters, fill_template_json, read_parameters_json
from vpt.utils.validate import validate_exists


def run_generator(args):
    args = GenerateJsonArgs(**vars(args))
    algorithm_params = read_parameters_json(args.input_analysis_spec)
    data = generate_segmentation_spec(**asdict(algorithm_params))
    io_with_retries(args.output_path, "w", lambda f: json.dump(data, f))


def generate_segmentation_spec(
    template_name: str, template_parameters: Dict, custom_parameters: Optional[Dict] = None
) -> Dict:
    path = f"{os.path.dirname(os.path.abspath(__file__))}/templates/{template_name}.json"
    validate_exists(path)
    # update default arguments
    if custom_parameters is None:
        custom_parameters = {}
    template_parameters = template_parameters.copy()
    if "all_z" not in template_parameters:
        template_parameters["all_z"] = [0, 1, 2, 3, 4, 5, 6]
    if "z_um" not in template_parameters:
        template_parameters["z_um"] = [(x + 1) * 1.5 for x in template_parameters["all_z"]]

    return fill_template_json(path, AlgorithmParameters(template_name, template_parameters, custom_parameters))


if __name__ == "__main__":
    run_generator(parse_args())
