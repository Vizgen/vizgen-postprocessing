import tempfile

import pytest

from vpt.utils import validate


def test_validate_does_not_exist_error():
    with tempfile.NamedTemporaryFile() as tf:
        tf.write(b"Contents go here")
        tf.seek(0)

        with pytest.raises(ValueError):
            validate.validate_does_not_exist(tf.name)


def test_validate_exists_error():
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(ValueError):
            validate.validate_exists(f"{td}/fake_file.txt")


def test_validate_empty_directory_error():
    with tempfile.TemporaryDirectory() as td:
        file_name = f"{td}/fake_file.txt"
        with open(file_name, "w") as f:
            f.write("Contents go here")

        with pytest.raises(ValueError):
            validate.validate_directory_empty(td)
