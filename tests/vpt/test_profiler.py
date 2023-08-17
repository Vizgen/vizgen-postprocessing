from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tests.vpt import OUTPUT_FOLDER
import vpt.profiler as profiler


@pytest.fixture
def profile_file() -> Path:
    with TemporaryDirectory(dir=OUTPUT_FOLDER) as td:
        yield Path(td) / "profile.prof"


def test_normal(profile_file: Path) -> None:
    profiler.initialize_profiler(str(profile_file))
    profiler.enable()
    profiler.disable()
    profiler.append_with_file("non-existent.prof")
    profiler.export_data()
    assert profile_file.exists()
