import json
import os
from pathlib import Path
from typing import Union

import pandas


def analysis_result_path(resultName: str, resultPath: Union[str, os.PathLike], fileExtension: str):
    return os.sep.join([str(resultPath), f"{resultName}{fileExtension}"])


def save_json_analysis_result(analysisResult: Union[dict, list], resultName: str, resultPath: str):
    savePath = analysis_result_path(resultName, resultPath, ".json")
    Path(resultPath).mkdir(parents=True, exist_ok=True)
    with open(savePath, "w", encoding="utf-8") as f:
        json.dump(analysisResult, f, indent=4)


def save_parquet_analysis_result(
    analysisResult: pandas.DataFrame, resultName: str, resultPath: Union[str, os.PathLike], **kwargs
):
    savePath = analysis_result_path(resultName, resultPath, ".parquet")
    Path(resultPath).mkdir(parents=True, exist_ok=True)

    analysisResult.to_parquet(savePath, compression="gzip", **kwargs)


def load_binary_analysis_result(resultName: str, resultPath: Union[str, os.PathLike]):
    savePath = analysis_result_path(resultName, resultPath, ".bin")
    if not os.path.isfile(savePath):
        return None

    with open(savePath, "rb") as f:
        bytesData = bytes(f.read())

    return bytesData
