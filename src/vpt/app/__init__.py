import dask

worker_memory_usage_target = 0.9

dask.config.set(
    {
        "distributed.worker.memory.target": worker_memory_usage_target,
        "distributed.worker.memory.spill": worker_memory_usage_target,
        "distributed.worker.memory.pause": worker_memory_usage_target,
        "distributed.worker.memory.terminate": 0.95,
    }
)
