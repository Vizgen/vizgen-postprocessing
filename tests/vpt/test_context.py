from vpt_core import log

from tests.vpt import OUTPUT_FOLDER
from vpt.app.context import Context, current_context
from vpt.app.task import Task


def test_context() -> None:
    assert current_context() is None
    with Context() as c1:
        with Context(dask_args={"workers": 3}) as c3:

            def proc_x2(a) -> int:
                return a["x"] * a["x"]

            def proc_y2(a) -> int:
                return a["y"] * a["y"]

            def proc_xy(a) -> int:
                return 2 * a["x"] * a["y"]

            assert current_context() == c3

            args = {"x": 2, "y": 3}

            tasks = [Task(proc_x2, args), Task(proc_xy, args), Task(proc_y2, args)]

            assert c1.parallel_run(tasks) == [4, 12, 9]
            assert c3.parallel_run(tasks) == [4, 12, 9]

        assert current_context() == c1

    assert current_context() is None


def test_log() -> None:
    test_file = OUTPUT_FOLDER / "test_log.txt"
    test_file.unlink(missing_ok=True)
    test_strings = ["_t1_", "_t2_", "_t3_"]
    with Context(dask_args={"workers": 2}, log_args={"fname": str(test_file)}) as c:

        def write(s):
            log.info(s)
            return s

        c.parallel_run([Task(write, x) for x in test_strings])
    text = test_file.read_text()
    for x in test_strings:
        assert x in text
