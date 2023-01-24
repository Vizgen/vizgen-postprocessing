import json
import re
from dataclasses import dataclass
from typing import Dict, Any, List

from vpt import log
from vpt.filesystem import vzg_open


@dataclass(frozen=True)
class AlgorithmParameters:
    template_name: str
    template_parameters: Dict[str, Any]
    custom_parameters: Dict[str, Any]


def read_parameters_json(path: str):
    with vzg_open(path, 'r') as f:
        data = json.load(f)

    algorithm_params = data['parameters']['algorithm']
    template_name = algorithm_params['name']
    template_parameters = algorithm_params['arguments']
    algorithm_params.pop('name')
    algorithm_params.pop('arguments')
    return AlgorithmParameters(template_name, template_parameters, algorithm_params)


def fill_template_json(path: str, parameters: AlgorithmParameters):
    with vzg_open(path, 'r') as f:
        data = json.load(f)
    data = insert_template_values(data, parameters.template_parameters)
    data = fill_parameters(data, parameters.custom_parameters)
    return data


def insert_template_values(data, template_parameters: Dict):
    if isinstance(data, Dict):
        to_iter = data.items()
    elif isinstance(data, List):
        to_iter = enumerate(data)
    else:
        return data
    for key, val in to_iter:
        if isinstance(val, Dict) or isinstance(val, List):
            data[key] = insert_template_values(val, template_parameters)
        elif isinstance(val, str):
            matched = re.findall(r'{{\s*\w+\s*}}', val)
            if len(matched) > 1:
                raise ValueError('Invalid template')
            if len(matched) == 1:
                parameter = matched[0][2:-2].strip()
                if template_parameters.get(parameter) is None:
                    raise ValueError(f'Invalid analysis parameters json: template parameter {parameter} is not set')
                data[key] = template_parameters.get(parameter)
    return data


def fill_parameters(data: Dict, parameters: Dict[str, Any]):
    for key, val in parameters.items():
        err = f'Invalid analysis json: custom parameter {key} is incorrect'
        path = key.split('.')
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
            if path_key == '*':
                for j in range(len(cur_data)):
                    cur_data[j] = insert_param(cur_data[j], path[i+1:], err_message, inserting_val)
                return data
            elif not path_key.isdigit():
                return warning_exit(f'{err_message} - key for list is not integer')
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
