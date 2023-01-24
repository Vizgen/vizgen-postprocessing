from pathlib import Path
from typing import List, Callable, Dict, Iterable, Optional

import vpt.log as log
from vpt.app.empty import Empty
from vpt.app.task import Task
from vpt.filesystem import initialize_filesystem
from vpt import profiler
import copy

_contexts = []


class Context:
    name: str
    dask_args: Dict
    fs_args: Dict
    log_args: Dict
    prof_args: Dict

    def __init__(self,
                 name: str = None,
                 dask_args: Dict = None,
                 fs_args: Dict = None,
                 log_args: Dict = None,
                 prof_args: Dict = None):
        self.name = name if name else '.'
        self.dask_args = dask_args
        self.fs_args = fs_args
        self.prof_args = prof_args
        self.log_args = log_args

    def __enter__(self):
        log.set_process_name(self.name)
        if self.log_args:
            log.initialize_logger(**self.log_args)
        if self.fs_args:
            initialize_filesystem(**self.fs_args)
        else:
            initialize_filesystem()

        if self.prof_args:
            profiler.initialize_profiler(**self.prof_args)
            profiler.enable()
        _contexts.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            log.exception(f"exception of type {exc_type} thrown: {exc_val}")

        log.release_logger()
        profiler.disable()
        profiler.export_data()
        _contexts.pop()

    def update_with_children(self, ctx_args: Iterable[Dict]):
        # append profiler results
        for child in ctx_args:
            sub_prof = self._get_profile_name(child)
            if sub_prof:
                profiler.append_with_file(sub_prof)

    def arguments(self) -> Dict:
        return {'name': self.name,
                'dask_args': self.dask_args,
                'fs_args': self.fs_args,
                'log_args': self.log_args,
                'prof_args': self.prof_args}

    @staticmethod
    def _get_profile_name(args: Dict) -> Optional[str]:
        pa = args.get('prof_args', None)
        return pa['profile_file'] if pa else None

    @staticmethod
    def _set_profile_name(args: Dict, name: str):
        args['prof_args']['profile_file'] = name

    @staticmethod
    def modify_context_as_sub(cnt_args: Dict, ind: int) -> Dict:
        ret = copy.deepcopy(cnt_args)
        pname = Context._get_profile_name(ret)
        ret["name"] = f"{cnt_args['name']}/task-{ind}"
        if pname:
            parent = Path(pname)
            Context._set_profile_name(ret, str(parent.with_stem(f"{parent.stem}_{ind}")))
        return ret

    def is_distributed(self) -> bool:
        return self.dask_args is not None and self.dask_args.get('address', None)

    def dask_client(self):
        from dask.distributed import Client
        return Client(self.dask_args['address'])

    def run(self, proc: Callable, *args):

        if not self.is_distributed():
            proc(*args)
        else:
            def remote_run(ctx: Dict, proc: Callable, *args):
                with Context(**ctx):
                    proc(*args)

            with self.dask_client() as c:
                _ = c.submit(remote_run, self.arguments(), proc, *args).result()
                log.info("contex.run.distributed finished!")

    def get_workers_count(self) -> int:
        if self.dask_args is not None:
            if self.dask_args.get('address', None):
                return len(self.dask_client().scheduler_info()['workers'])
            else:
                return self.dask_args.get('workers', 1)
        else:
            return 1

    def get_cluster(self):
        if self.is_distributed():
            return Empty()
        else:
            from dask.distributed import LocalCluster
            return LocalCluster(
                n_workers=self.get_workers_count(),
                threads_per_worker=1,
                dashboard_address=None)

    def get_client(self, cluster):
        if self.is_distributed():
            return self.dask_client()
        from dask.distributed import Client
        return Client(cluster)

    def parallel_run(self, tasks: Iterable[Task]) -> List:
        if self.get_workers_count() == 1:
            return [t.proc(t.args) for t in tasks]
        else:
            import dask.bag as db
            from dask.distributed import progress

            # Initializes a Dask local cluster with the correct number of workers
            with self.get_cluster() as cluster:
                with self.get_client(cluster):
                    cnt_args = self.arguments()
                    children = [{'task': t,
                                 'cnt_args': Context.modify_context_as_sub(cnt_args, i)
                                 } for i, t in enumerate(tasks)]
                    mp_bag = db.from_sequence(children)

                    def _context_wrapper(task: Task, cnt_args):
                        with Context(**cnt_args):
                            return task.proc(task.args)

                    # Runs processing using the Dask local cluster initialized above
                    mp_bag = mp_bag.map(lambda b: _context_wrapper(**b))
                    if log.is_verbose():
                        progress(mp_bag)
                    result = mp_bag.compute()
                    self.update_with_children([x['cnt_args'] for x in children])

                    return result


def current_context() -> Context:
    return _contexts[-1] if len(_contexts) > 0 else None


def parallel_run(tasks: Iterable[Task]) -> List:
    if current_context():
        return current_context().parallel_run(tasks)
    else:
        return [t.proc(t.args) for t in tasks]
