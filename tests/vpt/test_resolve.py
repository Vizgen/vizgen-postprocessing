from typing import Optional, List, Type

import pytest
from geopandas import GeoDataFrame

from vpt.entity.segmentation_results_worker import create_segmentation_results_relation
from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.segmentation.segmentation_item import SegmentationItem
from vpt_core.utils.base_case import BaseCase
from vpt_core.utils.segmentation_utils import Square, from_shapes, from_shapes_3d, assert_seg_equals, Rect

from vpt.entity import Constraint, Strategy
from vpt.entity.factory import get_constraint_resolver
from vpt.entity.resolver_base import StorageWorkerBase, RelatedSegmentationResults, ChildInfo
from vpt.entity.relationships import create_entity_relationships, EntityRelationships


def with_parent(seg: SegmentationItem, parent_id: int, parent_type: str) -> SegmentationItem:
    seg.set_parent(parent_type, parent_id)
    return seg


class DummyWorker(StorageWorkerBase):
    def __init__(self):
        self.actions: List = []

    def update(self, item: SegmentationItem, parent: Optional[SegmentationItem] = None) -> None:
        parent_id, parent_entity = None, None
        if parent is not None:
            parent_id = parent.get_entity_id()
            parent_entity = parent.get_entity_type()
        item.set_parent(parent_entity, parent_id)
        self.actions.append(("update", item))

    def create(self, item: SegmentationItem, parent: Optional[SegmentationItem] = None) -> SegmentationItem:
        parent_id, parent_entity = None, None
        if parent is not None:
            parent_id = parent.get_entity_id()
            parent_entity = parent.get_entity_type()
        item.set_parent(parent_entity, parent_id)
        item.set_entity_type("cell")
        self.actions.append(("create", item))
        return item

    def remove(self, item_id: int) -> None:
        self.actions.append(("remove", item_id))
        if hasattr(self, "on_remove"):
            self.on_remove(item_id)

    def parent_removed(self, parent_id: int) -> GeoDataFrame:
        self.actions.append(("parent_removed", parent_id))
        return GeoDataFrame()


class DummyParentWorker(DummyWorker):
    def create(self, item: SegmentationItem, parent: Optional[SegmentationItem] = None) -> SegmentationItem:
        item.set_parent(None, None)
        item.set_entity_type("type")
        self.actions.append(("create", item))
        return item


class TestResolveCase(BaseCase):
    def __init__(
        self,
        name: str,
        constraint: Constraint,
        parent: Optional[SegmentationItem],
        children: List[SegmentationItem],
        parent_result: List,
        children_result: List,
        exception: Optional[Type] = None,
        conflicts: List[List[SegmentationItem]] = [],
    ):
        super(TestResolveCase, self).__init__(name)
        parent_worker, child_worker = DummyParentWorker(), DummyWorker()
        setattr(parent_worker, "on_remove", lambda x: child_worker.parent_removed(x))
        self.handler = RelatedSegmentationResults(parent_worker, child_worker)
        self.constraint = constraint
        self.parent = parent
        if len(conflicts) == 0 and len(children) > 0:
            conflicts = [[] for _ in children]
        self.child_infos = [ChildInfo(x, 0.9, a) for (x, a) in zip(children, conflicts)]
        self.parent_result = parent_result
        self.children_result = children_result
        self.exception = exception

    def test_entry(self) -> None:
        if self.exception:
            with pytest.raises(self.exception):
                self._run_and_check()
        else:
            self._run_and_check()

    @staticmethod
    def cmp(result: List, dummy: DummyWorker):
        assert len(result) == len(dummy.actions)
        for i in range(len(result)):
            k1, v1 = result[i]
            k2, v2 = dummy.actions[i]
            assert k1 == k2
            if k1 in ["remove", "parent_removed"]:
                assert v1 == v2
            else:
                assert_seg_equals(v1, v2)

    def _run_and_check(self) -> None:
        resolver = get_constraint_resolver(self.constraint, None)
        resolver.resolve(self.handler, self.parent, self.child_infos)
        TestResolveCase.cmp(self.parent_result, self.handler.parents)
        TestResolveCase.cmp(self.children_result, self.handler.children)


TEST_CASES: List[TestResolveCase] = [
    TestResolveCase(
        "empty",
        Constraint("empty", None, Strategy.Unknown),
        from_shapes([Square(0, 0, 100)], entity_type="type").item(0),
        [from_shapes([Square(10, 10, 20)]).item(0), from_shapes([Square(50, 50, 20)], [1]).item(1)],
        [],
        [],
    ),
    TestResolveCase(
        "mcc invalid strategy",
        Constraint("maximum_child_count", 1, Strategy.ShrinkChild),
        None,
        [],
        [],
        [],
        ValueError,
    ),
    TestResolveCase(
        "mcc invalid value",
        Constraint("maximum_child_count", 2, Strategy.CreateChild),
        None,
        [],
        [],
        [],
        ValueError,
    ),
    TestResolveCase(
        "mcc invalid count",
        Constraint("maximum_child_count", None, Strategy.ShrinkChild),
        None,
        [],
        [],
        [],
        ValueError,
    ),
    TestResolveCase(
        "mincc cc",
        Constraint("minimum_child_count", 1, Strategy.CreateChild),
        from_shapes([Square(0, 0, 100)], entity_type="type").item(0),
        [],
        [],
        [("create", with_parent(from_shapes([Square(0, 0, 100)]).item(0), 0, "type"))],
    ),
    TestResolveCase(
        "mincc rp",
        Constraint("minimum_child_count", 1, Strategy.RemoveParent),
        from_shapes([Square(0, 0, 100)], entity_type="type").item(0),
        [],
        [("remove", 0)],
        [("parent_removed", 0)],
    ),
    TestResolveCase(
        "mcc rc",
        Constraint("maximum_child_count", 1, Strategy.RemoveChild),
        from_shapes([Square(0, 0, 100)], entity_type="type").item(0),
        [from_shapes([Square(10, 10, 20)]).item(0), from_shapes([Square(50, 50, 21)], [1]).item(1)],
        [],
        [("remove", 0)],
    ),
    TestResolveCase(
        "maxcc remove parent",
        Constraint("maximum_child_count", 1, Strategy.RemoveParent),
        from_shapes([Square(0, 0, 100)], entity_type="type").item(0),
        [from_shapes([Square(10, 10, 20)]).item(0), from_shapes([Square(50, 50, 21)], [1]).item(1)],
        [("remove", 0)],
        [
            ("parent_removed", 0),
            ("update", with_parent(from_shapes([Square(10, 10, 20)]).item(0), None, None)),
            ("update", with_parent(from_shapes([Square(50, 50, 21)], [1]).item(1), None, None)),
        ],
    ),
    TestResolveCase(
        "cmhp invalid strategy",
        Constraint("child_must_have_parent", None, Strategy.ShrinkChild),
        None,
        [],
        [],
        [],
        ValueError,
    ),
    TestResolveCase(
        "cmhp create parent",
        Constraint("child_must_have_parent", None, Strategy.CreateParent),
        None,
        [from_shapes([Square(10, 10, 20)]).item(0)],
        [("create", from_shapes([Square(10, 10, 20)], entity_type="type").item(0))],
        [("update", with_parent(from_shapes([Square(10, 10, 20)]).item(0), 0, "type"))],
    ),
    TestResolveCase(
        "cmhp create parent remove intersected parent",
        Constraint("child_must_have_parent", None, Strategy.CreateParent),
        None,
        [from_shapes([Square(10, 10, 20)]).item(0)],
        [("create", from_shapes([Square(10, 10, 20)], entity_type="type").item(0)), ("remove", 1)],
        [("update", with_parent(from_shapes([Square(10, 10, 20)]).item(0), 0, "type")), ("parent_removed", 1)],
        conflicts=[[from_shapes([Square(15, 15, 10)], [1]).item(1)]],
    ),
    TestResolveCase(
        "cmhp remove child",
        Constraint("child_must_have_parent", None, Strategy.RemoveChild),
        None,
        [from_shapes([Square(10, 10, 20)]).item(0), from_shapes([Square(100, 100, 25)], [1]).item(1)],
        [],
        [("remove", 0), ("remove", 1)],
    ),
    TestResolveCase(
        "ciop invalid strategy",
        Constraint("child_intersect_one_parent", None, Strategy.RemoveParent),
        None,
        [],
        [],
        [],
        ValueError,
    ),
    TestResolveCase(
        "ciop shrink child",
        Constraint("child_intersect_one_parent", None, Strategy.ShrinkChild),
        from_shapes([Square(10, 10, 20)], entity_type="type").item(0),
        [from_shapes([Square(20, 10, 20)]).item(0), from_shapes([Square(100, 100, 25)], [1]).item(1)],
        [],
        [
            ("update", with_parent(from_shapes([Rect(30, 10, 10, 20)]).item(0), 0, "type")),
            ("update", with_parent(from_shapes([Rect(100, 100, 20, 25)], [1]).item(1), 0, "type")),
        ],
        conflicts=[[from_shapes([Square(0, 0, 30)]).item(0)], [from_shapes([Square(120, 100, 100)]).item(0)]],
    ),
    TestResolveCase(
        "ciop remove child",
        Constraint("child_intersect_one_parent", None, Strategy.RemoveChild),
        from_shapes([Square(10, 10, 20)], entity_type="type").item(0),
        [from_shapes([Square(10, 10, 20)]).item(0), from_shapes([Square(100, 100, 25)], [1]).item(1)],
        [],
        [("remove", 0), ("remove", 1)],
        conflicts=[[from_shapes([Square(0, 0, 30)]).item(0)], [from_shapes([Square(120, 100, 100)]).item(0)]],
    ),
    TestResolveCase(
        "ciop remove child no parent",
        Constraint("child_intersect_one_parent", None, Strategy.RemoveChild),
        None,
        [from_shapes([Square(10, 10, 20)]).item(0), from_shapes([Square(100, 100, 25)], [1]).item(1)],
        [],
        [("remove", 1)],
        conflicts=[[], [from_shapes([Square(0, 0, 30)]).item(0), from_shapes([Square(120, 100, 100)]).item(0)]],
    ),
    TestResolveCase(
        "ciop remove after difference",
        Constraint("child_intersect_one_parent", None, Strategy.ShrinkChild),
        from_shapes([Square(10, 10, 20)], entity_type="type").item(0),
        [from_shapes([Square(20, 10, 20)]).item(0), from_shapes([Square(100, 100, 25)], [1]).item(1)],
        [],
        [("update", with_parent(from_shapes([Rect(30, 10, 10, 20)]).item(0), 0, "type")), ("remove", 1)],
        conflicts=[[from_shapes([Square(0, 0, 30)]).item(0)], [from_shapes([Square(100, 100, 100)]).item(0)]],
    ),
    TestResolveCase(
        "pmcc invalid strategy",
        Constraint("parent_must_cover_child", None, Strategy.RemoveParent),
        None,
        [],
        [],
        [],
        ValueError,
    ),
    TestResolveCase(
        "pmcc remove child",
        Constraint("parent_must_cover_child", None, Strategy.RemoveChild),
        from_shapes([Square(10, 10, 20)], entity_type="type").item(0),
        [from_shapes([Square(10, 10, 20)]).item(0), from_shapes([Square(100, 100, 25)], [1]).item(1)],
        [],
        [("remove", 0), ("remove", 1)],
    ),
    TestResolveCase(
        "pmcc shrink child",
        Constraint("parent_must_cover_child", None, Strategy.ShrinkChild),
        from_shapes([Square(0, 0, 50)], entity_type="type").item(0),
        [from_shapes([Square(30, 30, 30)]).item(0)],
        [],
        [("update", with_parent(from_shapes([Square(30, 30, 20)]).item(0), 0, "type"))],
    ),
]


@pytest.mark.parametrize("case", TEST_CASES, ids=str)
def test_alg_spec_validation(case: TestResolveCase):
    case.test_entry()


def test_resolving_relationships() -> None:
    child = from_shapes_3d([[Square(30, 30, 30), Square(50, 50, 30), Square(100, 50, 30)]], cids=[10, 11, 12])
    parent = from_shapes_3d([[Square(30, 30, 60), Square(50, 50, 60), Square(110, 50, 60)]], cids=[20, 21, 22])
    parent.set_entity_type("nuclei")
    parent.set_column(parent.entity_name_field, "nuclei")
    cnt = Constraint(constraint="empty", value=None, resolution="nothing")
    relationships = EntityRelationships("nuclei", "cell", 0.5, [cnt])

    child_res, parent_res = create_entity_relationships([child, parent], relationships)
    assert all(child_res.df == child.df)
    assert all(parent_res.df == parent.df)

    res = create_entity_relationships([child], None)
    assert len(res) == 1
    assert all(res[0].df == child.df)


def test_relationships_unmatched_entities() -> None:
    child = SegmentationResult(entity="cell")
    parent = SegmentationResult(entity="own")
    relationships = EntityRelationships("nuclei", "cell", 0.5, [])
    with pytest.raises(ValueError):
        create_entity_relationships([child, parent], relationships)

    with pytest.raises(ValueError):
        create_entity_relationships([child, parent], None)


def test_resolving_constraint() -> None:
    child = from_shapes_3d([[Square(30, 30, 30), Square(50, 50, 30), Square(100, 50, 30)]], cids=[10, 11, 12])
    parent = from_shapes_3d(
        [[Square(30, 30, 60), Square(50, 50, 60), Square(110, 50, 60)]], cids=[20, 21, 22], entity_type="nuc"
    )
    target = create_segmentation_results_relation(parent, child)
    get_constraint_resolver(Constraint("parent_must_cover_child", None, Strategy.RemoveChild), None).resolve(
        target, parent.item(20), [ChildInfo(child.item(11), 0.5, [])]
    )
    with pytest.raises(KeyError):
        target.children.data.item(11)
    assert len(target.children.data.df) == 2
    assert len(target.parents.data.df) == 3

    get_constraint_resolver(Constraint("maximum_child_count", 1, Strategy.RemoveParent), None).resolve(
        target, parent.item(20), [ChildInfo(child.item(10), 0.5, []), ChildInfo(child.item(12), 0.7, [])]
    )
    with pytest.raises(KeyError):
        target.parents.data.item(20)
    assert len(target.children.data.df) == 2
    assert len(target.parents.data.df) == 2

    get_constraint_resolver(Constraint("minimum_child_count", 1, Strategy.CreateChild), None).resolve(
        target, parent.item(21), []
    )
    assert len(target.children.data.df) == 3
    assert any(target.children.data.df[SegmentationItem.parent_id_field] == 21)
