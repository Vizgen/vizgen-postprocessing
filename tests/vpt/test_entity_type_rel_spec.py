import numpy as np
import pytest

from tests.vpt import IMAGES_ROOT, OUTPUT_FOLDER, TEST_DATA_ROOT
from vpt.entity.relationships import relationships_from_dict
from vpt.prepare_segmentation.input_tools import read_json
from vpt.prepare_segmentation.main import get_segmentation_spec
from vpt.utils.seg_spec_utils import dict_to_segmentation_specification


def test_initialization() -> None:
    raw = read_json(str(TEST_DATA_ROOT / "relationships.json"))
    result = relationships_from_dict(raw)
    assert result.parent_type == "parent"
    assert result.child_type == "child"
    assert len(result.constraints) == 3
    raw["constraints"][0]["resolution"] = "invalid-value"
    with pytest.raises(ValueError):
        relationships_from_dict(raw)
    raw["constraints"] = raw["constraints"][1:]
    raw["constraints"][0]["value"] = "invalid-value"
    with pytest.raises(ValueError):
        relationships_from_dict(raw)


def test_no_relations() -> None:
    alg = read_json(str(TEST_DATA_ROOT / "watershed_sd.json"))
    m = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    spec = dict_to_segmentation_specification(
        get_segmentation_spec(alg, str(IMAGES_ROOT), m, 256, 56, "", "", str(OUTPUT_FOLDER))
    )
    assert spec.entity_type_relationships is None


def test_prepare() -> None:
    alg = read_json(str(TEST_DATA_ROOT / "test_algorithm.json"))
    m = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    spec = dict_to_segmentation_specification(
        get_segmentation_spec(alg, str(IMAGES_ROOT), m, 256, 56, "", "", str(OUTPUT_FOLDER))
    )
    assert spec.entity_type_relationships is not None
    assert spec.entity_type_relationships.parent_type == "et1"
    assert spec.entity_type_relationships.child_type == "et2"
    assert len(spec.entity_type_relationships.constraints) == 5


def test_default_relations() -> None:
    alg = read_json(str(TEST_DATA_ROOT / "test_default_entities_algorithm.json"))
    spec = dict_to_segmentation_specification(
        get_segmentation_spec(alg, str(IMAGES_ROOT), np.array([]), 1000, 1, "", "", "")
    )
    assert spec.entity_type_relationships is not None
    assert spec.entity_type_relationships.parent_type == "cell"
    assert spec.entity_type_relationships.child_type == "nuclei"
    assert len(spec.entity_type_relationships.constraints) == 5
