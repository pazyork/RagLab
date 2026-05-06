import pytest
from raglab.storage.db import Database


def test_delete_case_cascades():
    db = Database(":memory:")
    db.add_provider("p", "key")
    cid = db.add_case("c1", "desc")
    db.add_chunks(cid, ["chunk a", "chunk b"])
    rid = db.add_run(cid, "run1", "model1")
    db.add_scores(rid, [(0, 0.9, 1), (1, 0.8, 2)])

    db.delete_case(cid)

    assert db.get_case(cid) is None
    assert db.get_chunks(cid) == []
    assert db.list_runs(cid) == []
