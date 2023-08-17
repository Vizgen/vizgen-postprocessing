import json
from typing import List, Optional

import pytest

from vpt.entity import Constraint, Strategy
from vpt_core.utils.base_case import BaseCase

from tests.vpt import TEST_DATA_ROOT
from vpt.prepare_segmentation.input_tools import AlgInfo
from vpt.prepare_segmentation.validate import validate_alg_info
from vpt.entity.relationships import EntityRelationships


class AlgSpecCase(BaseCase):
    def __init__(
        self,
        name: str,
        tasks_entity_types: List[List[str]],
        output_entities_sets: List[List[str]],
        entities_task_fusion: int,
        valid: bool,
        entity_relationships: Optional[EntityRelationships] = None,
    ):
        super(AlgSpecCase, self).__init__(name)
        self.tasks_entity_types = tasks_entity_types
        self.output_entities_sets = output_entities_sets
        self.entities_task_fusion = entities_task_fusion
        self.entity_relationships = entity_relationships
        self.valid = valid

    def construct_alg_spec(self) -> dict:
        with open(TEST_DATA_ROOT / "watershed_sd.json", "r") as f:
            data = json.load(f)
        for i, task in enumerate(data["segmentation_tasks"]):
            data["segmentation_tasks"][i]["entity_types_detected"] = self.tasks_entity_types[i]

        output_folders = data["output_files"][0]
        data["output_files"] = []
        for i in range(len(self.output_entities_sets)):
            data["output_files"].append(dict(output_folders))
            data["output_files"][i]["entity_types_output"] = self.output_entities_sets[i]

        fusion_params = data["segmentation_task_fusion"]
        data["segmentation_task_fusion"] = []
        for i in range(self.entities_task_fusion):
            data["segmentation_task_fusion"].append(fusion_params)
        if self.entity_relationships is not None:
            data["entity_type_relationships"] = {
                "parent_type": self.entity_relationships.parent_type,
                "child_type": self.entity_relationships.child_type,
                "child_coverage_threshold": self.entity_relationships.child_coverage_threshold,
                "constraints": [
                    {"constraint": cnt.constraint, "value": cnt.value, "resolution": cnt.resolution.value}
                    for cnt in self.entity_relationships.constraints
                ],
            }
        return data


ALG_SPEC_CASES = [
    AlgSpecCase(
        "valid",
        tasks_entity_types=[["cell", "nuclei"], ["cell"], ["nuclei"]],
        output_entities_sets=[["cell"], ["nuclei"]],
        entities_task_fusion=2,
        valid=True,
    ),
    AlgSpecCase(
        "duplicated_entities",
        tasks_entity_types=[["cell", "nuclei", "cell"], ["nuclei"]],
        output_entities_sets=[["cell", "nuclei"]],
        entities_task_fusion=2,
        valid=False,
    ),
    AlgSpecCase(
        "wrong_fusion_type",
        tasks_entity_types=[["cell"], ["cell"]],
        output_entities_sets=[["cell"]],
        entities_task_fusion=2,
        valid=False,
    ),
    AlgSpecCase(
        "duplicated_output_entities",
        tasks_entity_types=[["cell", "nuclei"], ["nuclei"]],
        output_entities_sets=[["cell", "nuclei"], ["cell"]],
        entities_task_fusion=2,
        valid=False,
    ),
    AlgSpecCase(
        "valid relationships",
        tasks_entity_types=[["own"], ["nuclei"]],
        output_entities_sets=[["own", "nuclei"]],
        entities_task_fusion=2,
        valid=True,
        entity_relationships=EntityRelationships(
            "own", "nuclei", 0.4, [Constraint("child_must_have_parent", None, Strategy.CreateParent)]
        ),
    ),
    AlgSpecCase(
        "invalid relationships",
        tasks_entity_types=[["own"], ["nuclei"]],
        output_entities_sets=[["own", "nuclei"]],
        entities_task_fusion=2,
        valid=False,
        entity_relationships=EntityRelationships(
            "own", "nuclei", 0.4, [Constraint("unknown", None, Strategy.CreateParent)]
        ),
    ),
]


@pytest.mark.parametrize("case", ALG_SPEC_CASES, ids=str)
def test_alg_spec_validation(case: AlgSpecCase):
    alg_info = AlgInfo(case.construct_alg_spec(), {}, {}, [])
    try:
        validate_alg_info(alg_info, output_path="", overwrite=True)
    except ValueError:
        assert not case.valid
        return
    assert case.valid
