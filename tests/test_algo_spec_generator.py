import json
import os.path

import pytest

from vpt.utils.seg_json_generator.main import generate_segmentation_spec


def test_template_whitespaces() -> None:
    template_name = 'cellpose_default'
    template_parameters = {"entity_types_detected": "cell",
                           "seg_model": "cyto2",
                           "entity_fill_channel": "Cellbound2",
                           "nuclear_channel": "DAPI"}
    seg_spec = generate_segmentation_spec(template_name, template_parameters, {})
    with open(f'{os.path.dirname(__file__)}/data/cellpose_2.json', 'r') as f:
        ground_truth = json.load(f)
    assert seg_spec == ground_truth


def test_custom_parameters() -> None:
    template_name = 'cellpose_default'
    template_parameters = {"entity_types_detected": "cell",
                           "seg_model": "cyto2",
                           "entity_fill_channel": "Cellbound2",
                           "nuclear_channel": "DAPI"}
    blur_filter = {"name": "blur",
                   "parameters": {"size": 6}
                   }
    custom_parameters = {"segmentation_tasks.0.z_layers": [1, 3, 5],
                         "segmentation_tasks.0.task_input_data.1.image_preprocessing.0": blur_filter}

    with open(f'{os.path.dirname(__file__)}/data/cellpose_2.json', 'r') as f:
        ground_truth = json.load(f)
    ground_truth['segmentation_tasks'][0]['z_layers'] = [1, 3, 5]
    ground_truth['segmentation_tasks'][0]['task_input_data'][1]['image_preprocessing'][0] = blur_filter
    seg_spec = generate_segmentation_spec(template_name, template_parameters, custom_parameters)
    assert seg_spec == ground_truth


def test_invalid_template_parameters() -> None:
    template_name = 'cellpose_default'
    template_parameters = {"entity_types": "cell",
                           "seg_model": "cyto2",
                           "nuclear_channel": "DAPI"}
    with pytest.raises(ValueError):
        generate_segmentation_spec(template_name, template_parameters, {})


def test_invalid_custom_parameters() -> None:
    template_name = 'cellpose_default'
    template_parameters = {"entity_types_detected": "cell",
                           "seg_model": "cyto",
                           "entity_fill_channel": "Cellbound3",
                           "nuclear_channel": "DAPI"}
    custom_parameters = {"segmentation_tasks.2.task_input_data.1.image_preprocessing.0": {}}
    seg_spec = generate_segmentation_spec(template_name, template_parameters, custom_parameters)
    gt = generate_segmentation_spec(template_name, template_parameters, {})
    assert gt == seg_spec


def test_list_iterating() -> None:
    template_name = 'cellpose_default'
    template_parameters = {"entity_types_detected": "cell",
                           "seg_model": "cyto2",
                           "entity_fill_channel": "Cellbound2",
                           "nuclear_channel": "DAPI"}
    custom_parameters = {"segmentation_tasks.*.z_layers": [1, 2]}
    with open(f'{os.path.dirname(__file__)}/data/cellpose_2.json', 'r') as f:
        ground_truth = json.load(f)
    ground_truth['segmentation_tasks'][0]['z_layers'] = [1, 2]
    ground_truth['segmentation_tasks'][1]['z_layers'] = [1, 2]
    seg_spec = generate_segmentation_spec(template_name, template_parameters, custom_parameters)
    assert seg_spec == ground_truth


def test_nested_list_iterating() -> None:
    template_name = 'cellpose_default'
    template_parameters = {"entity_types_detected": "cell",
                           "seg_model": "cyto2",
                           "entity_fill_channel": "Cellbound2",
                           "nuclear_channel": "DAPI"}
    custom_parameters = {
        "segmentation_tasks.*.task_input_data.*.image_preprocessing.*.parameters.filter_size": [50, 50]}
    with open(f'{os.path.dirname(__file__)}/data/cellpose_2.json', 'r') as f:
        ground_truth = json.load(f)
    for i in [0, 1]:
        for j in range(2 - i):
            ground_truth['segmentation_tasks'][i]['task_input_data'][j]['image_preprocessing'][0]['parameters'][
                'filter_size'] = [50, 50]
    seg_spec = generate_segmentation_spec(template_name, template_parameters, custom_parameters)
    assert seg_spec == ground_truth


def test_set_z_levels() -> None:
    cp_template_parameters = {"entity_types_detected": "cell",
                              "seg_model": "cyto2",
                              "entity_fill_channel": "X",
                              "nuclear_channel": "Y",
                              "all_z": [0, 1, 2],
                              }
    result1 = {
        "all_z_indexes": [0, 1, 2],
        "z_positions_um": [1.5, 3.0, 4.5]
    }
    seg_spec = generate_segmentation_spec('cellpose_default', cp_template_parameters)
    assert seg_spec["experiment_properties"] == result1
    for task in seg_spec["segmentation_tasks"]:
        assert task["z_layers"] == result1["all_z_indexes"]
    result2 = {
        "all_z_indexes": [0, 2, 4, 6],
        "z_positions_um": [1, 2, 3, 4]
    }
    ws_template_parameters = {"entity_types_detected": "cell",
                              "stardist_model": "SDM",
                              "entity_fill_channel": "X",
                              "seed_channel": "Y",
                              "all_z": [0, 2, 4, 6],
                              "z_um": [1, 2, 3, 4]}

    seg_spec = generate_segmentation_spec('watershed_default', ws_template_parameters)
    assert seg_spec["experiment_properties"] == result2
    for task in seg_spec["segmentation_tasks"]:
        assert task["z_layers"] == result2["all_z_indexes"]
