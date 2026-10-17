"""Result-contract tests (ТЗ §10 JSON schema + verdict/violations semantics + evidence frames)."""

import base64
import copy

import numpy as np
import pytest

from forte_ai.schema import assert_valid, validate_result
from forte_ai.video import encode_jpeg_base64


def _jpeg_b64() -> str:
    img = np.zeros((48, 64, 3), np.uint8)
    img[:, :, 1] = 200
    return encode_jpeg_base64(img, quality=85, max_width=1280)


@pytest.fixture
def good_result():
    return {
        "job_id": "3f2a9c1e",
        "status": "done",
        "verdict": "violation",
        "violations": [
            {
                "type": "Выдача наличных без пересчёта в присутствии клиента",
                "timecode_sec": 44.2,
                "description": "На 44,2 с кассир передаёт клиенту наличные; в предшествующие 15 с не зафиксировано пересчёта.",
                "evidence_frames": [
                    {"timestamp_sec": 44.2, "image_base64": _jpeg_b64()},
                    {"timestamp_sec": 45.2, "image_base64": _jpeg_b64()},
                ],
                "type_id": "issue_without_count",
                "confidence": 0.8,
                "rule": {
                    "document": "Постановление Правления НБ РК от 29.11.2019 № 231",
                    "clause": "п. 31 пп. 4",
                    "quote": "пересчитывает подготовленные к выдаче наличные деньги в присутствии клиента",
                    "url": "https://adilet.zan.kz/rus/docs/V1900019680",
                },
                "facts": ["handover cashier->client at 44.2"],
            }
        ],
        "engine_version": "0.1.0",
        "stage_timings": {"decode": 1.2},
    }


def test_good_result_valid(good_result):
    assert validate_result(good_result) == []
    assert_valid(good_result)


def test_no_violation_requires_empty_list(good_result):
    r = copy.deepcopy(good_result)
    r["verdict"] = "no_violation"
    assert validate_result(r), "no_violation with violations must fail"
    r["violations"] = []
    assert validate_result(r) == []


def test_violation_requires_at_least_one(good_result):
    r = copy.deepcopy(good_result)
    r["violations"] = []
    assert validate_result(r)


def test_evidence_frame_count_1_to_3(good_result):
    r = copy.deepcopy(good_result)
    r["violations"][0]["evidence_frames"] = []
    assert validate_result(r)
    r["violations"][0]["evidence_frames"] = [{"timestamp_sec": 44.2, "image_base64": _jpeg_b64()}] * 4
    assert validate_result(r)


def test_evidence_must_be_near_timecode(good_result):
    r = copy.deepcopy(good_result)
    for f in r["violations"][0]["evidence_frames"]:
        f["timestamp_sec"] = 10.0
    assert any("within" in p for p in validate_result(r))


def test_evidence_must_be_jpeg_without_data_uri(good_result):
    r = copy.deepcopy(good_result)
    r["violations"][0]["evidence_frames"][0]["image_base64"] = base64.b64encode(b"\x89PNG" + b"x" * 200).decode()
    assert any("not a JPEG" in p for p in validate_result(r))


def test_russian_strings_required(good_result):
    r = copy.deepcopy(good_result)
    r["violations"][0]["type"] = "issue_without_count"
    assert any("Russian" in p for p in validate_result(r))


def test_rule_url_must_be_adilet(good_result):
    r = copy.deepcopy(good_result)
    r["violations"][0]["rule"]["url"] = "https://example.com/x"
    assert validate_result(r)


def test_missing_required_key(good_result):
    r = copy.deepcopy(good_result)
    del r["verdict"]
    assert validate_result(r)
