import numpy as np


def extend_with_u32(a: bytearray, x) -> None:
    a.extend(np.uint32(x).tobytes())


def extend_with_i32(a: bytearray, x) -> None:
    a.extend(np.int32(x).tobytes())


def extend_with_i16(a: bytearray, x) -> None:
    a.extend(np.int16(x).tobytes())


def extend_with_f32(a: bytearray, x) -> None:
    a.extend(np.float32(x).tobytes())
