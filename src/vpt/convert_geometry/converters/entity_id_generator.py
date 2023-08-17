from datetime import datetime

import numpy as np
from vpt_core.io.output_tools import format_experiment_timestamp

counter_digits_num = 8
counter = 0
process_id = ""


def get_id() -> np.int64:
    global counter
    next_id = np.int64(f"{process_id}{str(counter).zfill(counter_digits_num)}")
    counter += 1
    return next_id


def set_process_id():
    global process_id, counter_digits_num
    if not process_id:
        process_id = format_experiment_timestamp(datetime.utcnow().timestamp())
        counter_digits_num = 19 - len(process_id)
