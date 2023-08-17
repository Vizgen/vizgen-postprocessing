import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Iterable

from vpt_core import log
from vpt_core.io.vzgfs import io_with_retries


@dataclass(frozen=True)
class AlgorithmParameters:
    template_name: str
    template_parameters: Dict[str, Any]
    custom_parameters: Dict[str, Any]


def read_parameters_json(path: str):
    data = io_with_retries(path, "r", json.load)

    algorithm_params = data["parameters"]["algorithm"]
    template_name = algorithm_params["name"]
    template_parameters = algorithm_params["arguments"]
    algorithm_params.pop("name")
    algorithm_params.pop("arguments")
    return AlgorithmParameters(template_name, template_parameters, algorithm_params)


def fill_template_json(path: str, parameters: AlgorithmParameters):
    data = io_with_retries(path, "r", json.load)
    data = insert_template_values(data, parameters.template_parameters)
    data = fill_parameters(data, parameters.custom_parameters)
    return data


def update_str_with_template(s: str, template_parameters: Dict) -> str:
    matched = re.findall(r"{{\s*\w+\s*}}", s)
    if len(matched) > 1:
        raise ValueError("Invalid template")
    if len(matched) == 1:
        parameter = matched[0][2:-2].strip()
        result = template_parameters.get(parameter)
        if result is None:
            raise ValueError(f"Invalid analysis parameters json: template parameter {parameter} is not set")
        else:
            return result
    return s


def walk(x) -> Iterable:
    if isinstance(x, Dict):
        for key, value in x.items():
            yield key, value
    elif isinstance(x, List):
        for ind, value in enumerate(x):
            yield ind, value


def insert_template_values(data, template_parameters: Dict):
    if not isinstance(data, Dict) and not isinstance(data, List):
        return data
    for key, val in walk(data):
        if isinstance(val, Dict) or isinstance(val, List):
            data[key] = insert_template_values(val, template_parameters)
        elif isinstance(val, str):
            data[key] = update_str_with_template(val, template_parameters)
    return data


def fill_parameters(data: Dict, parameters: Dict[str, Any]):
    for key, val in parameters.items():
        err = f"Invalid analysis json: custom parameter {key} is incorrect"
        path = key.split(".")
        data = insert_param(data, path, err, val)
    return data


def insert_param(data: Dict, path: List[str], err_message: str, inserting_val):
    def warning_exit(err: str = err_message):
        log.warning(err)
        return data

    cur_data = data
    for i, path_key in enumerate(path):
        if isinstance(cur_data, Dict):
            if cur_data.get(path_key) is None:
                return warning_exit()
            k = path_key

        elif isinstance(cur_data, List):
            if path_key == "*":
                for j in range(len(cur_data)):
                    cur_data[j] = insert_param(cur_data[j], path[i + 1 :], err_message, inserting_val)
                return data
            elif not path_key.isdigit():
                return warning_exit(f"{err_message} - key for list is not integer")
            else:
                k = int(path_key)
                if len(cur_data) <= k:
                    return warning_exit()
        else:
            return warning_exit()

        if i == len(path) - 1:
            cur_data[k] = inserting_val
        else:
            cur_data = cur_data[k]
    return data
