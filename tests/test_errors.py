"""The exceptions of the SDK: what they carry, and that they survive pickling and copying (an error raised in a worker
process — Celery, multiprocessing — travels back to the caller)."""

from __future__ import annotations

import copy
import pickle

from bitgen import BitgenError, UnexpectedAnswerError
from bitgen._http.transport import TransportError
from bitgen.errors import MAX_CODE_LENGTH


def test_bitgen_error_carries_status_and_code() -> None:
    error = BitgenError(416, "invalid_amount")
    assert (error.status, error.code) == (416, "invalid_amount")
    assert str(error) == "invalid_amount (HTTP 416)"
    assert error.args == ("invalid_amount (HTTP 416)",)
    assert isinstance(error, Exception)
    assert BitgenError(400, "x" * 300).code == "x" * MAX_CODE_LENGTH


def test_errors_survive_pickling_and_copying() -> None:
    for original in [BitgenError(416, "invalid_amount"), BitgenError(0, "network_error")]:
        for clone in (pickle.loads(pickle.dumps(original)), copy.copy(original), copy.deepcopy(original)):
            assert isinstance(clone, BitgenError)
            assert (clone.status, clone.code, str(clone)) == (original.status, original.code, str(original))
    tagged = BitgenError(404, "unknown_asset")
    tagged.request_id = "req-42"  # type: ignore[attr-defined]
    assert pickle.loads(pickle.dumps(tagged)).request_id == "req-42"
    transport = TransportError("request_timeout", "TimeoutError: timed out")
    clone = pickle.loads(pickle.dumps(transport))
    assert isinstance(clone, TransportError)
    assert (clone.code, str(clone)) == ("request_timeout", "TimeoutError: timed out")
    unexpected = pickle.loads(pickle.dumps(UnexpectedAnswerError("the API answered a page whose items are not a list")))
    assert isinstance(unexpected, UnexpectedAnswerError)
    assert str(unexpected) == "the API answered a page whose items are not a list"
