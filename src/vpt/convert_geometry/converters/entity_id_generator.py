from datetime import datetime

import numpy as np

COUNTER_DIGITS_NUM = 8
counter = 0
process_id = ""


def get_id() -> np.int64:
    global counter
    id = str(counter).zfill(COUNTER_DIGITS_NUM)
    id = np.int64(f'{process_id}{id}')
    counter += 1
    return id


def set_process_id():
    global process_id
    if not process_id:
        process_id = datetime.utcnow().strftime('%m%d%H%M%S')
