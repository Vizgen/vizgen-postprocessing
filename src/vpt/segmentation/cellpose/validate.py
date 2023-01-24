from typing import Dict


def validate_task(task: Dict) -> Dict:
    nuclear_channel = task['segmentation_parameters'].get('nuclear_channel', None)
    fill_channel = task['segmentation_parameters'].get('entity_fill_channel', None)

    channels = [input_data['image_channel'] for input_data in task['task_input_data']]

    if nuclear_channel and nuclear_channel not in channels:
        raise ValueError(f'{nuclear_channel} is not in input channels')

    if fill_channel and fill_channel not in channels:
        raise ValueError(f'{fill_channel} is not in input channels')

    return task
