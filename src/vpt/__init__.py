import os
import dask
import dask.distributed

dask.config.set(
    {
        "distributed.scheduler.active-memory-manager.measure": "managed",
        "distributed.worker.memory.rebalance.measure": "managed",
        "distributed.worker.memory.spill": False,
        "distributed.worker.memory.pause": False,
        "distributed.worker.memory.terminate": False,
        "distributed.scheduler.worker-ttl": None,
        "logging.distributed": "critical",
    }
)

os.environ["USE_PYGEOS"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

IS_VPT_EXPERIMENTAL_VAR = "VPT_EXPERIMENTAL"
