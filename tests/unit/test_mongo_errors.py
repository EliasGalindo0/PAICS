"""Erros de cota Atlas e ObjectId inválido."""
import pytest
from bson.errors import InvalidId


@pytest.mark.unit
def test_is_storage_quota_error():
    from utils.mongo_errors import is_storage_quota_error

    class FakeOp(Exception):
        def __init__(self):
            super().__init__("you are over your space quota, using 512 MB of 512 MB")
            self.code = 8000

    assert is_storage_quota_error(FakeOp())
    assert is_storage_quota_error(Exception("Writes are blocked on your cluster"))
    assert not is_storage_quota_error(Exception("timeout"))


@pytest.mark.unit
def test_json_status_for_unhandled_invalid_id():
    from utils.mongo_errors import json_status_for_unhandled

    status, detail = json_status_for_unhandled(InvalidId("'undefined' is not a valid ObjectId"))
    assert status == 400
    assert "inválido" in detail.lower()


@pytest.mark.unit
def test_json_status_for_unhandled_quota():
    from utils.mongo_errors import QUOTA_DETAIL, json_status_for_unhandled

    class FakeOp(Exception):
        def __init__(self):
            super().__init__("over your space quota")
            self.code = 8000

    status, detail = json_status_for_unhandled(FakeOp())
    assert status == 507
    assert detail == QUOTA_DETAIL


@pytest.mark.unit
def test_requisicao_find_by_id_undefined_nao_quebra(clean_db):
    """GET /exames/undefined não deve estourar InvalidId."""
    from database.models import Requisicao

    req_model = Requisicao(clean_db.requisicoes)
    assert req_model.find_by_id("undefined") is None
    assert req_model.find_by_id("") is None
    assert req_model.find_by_id("x") is None
    assert req_model.delete("undefined") is False
