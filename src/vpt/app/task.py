from dataclasses import dataclass
from typing import Any, Iterable

from vpt.cmd_args import get_cmd_entrypoint


@dataclass
class Task:
    proc: callable
    args: Any


def pipeline_to_tasks(pipeline_name, args: Iterable) -> Iterable[Task]:
    for arg in args:
        yield Task(get_cmd_entrypoint(pipeline_name), arg)
