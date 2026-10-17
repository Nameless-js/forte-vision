"""Result-contract validation (ТЗ §10) used by tests, the CLI, the server and `make verify`."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent / "result_schema.json"
_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA)


def schema() -> dict:
    return _SCHEMA


def validate_result(result: dict[str, Any], check_images: bool = True, evidence_tolerance_s: float = 1.0) -> list[str]:
    """Return a list of problems (empty = valid). Checks the JSON schema plus semantic rules:
    verdict/violations consistency, JPEG magic bytes, one evidence frame within ±tolerance of the timecode."""
    problems = [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in _VALIDATOR.iter_errors(result)]
    if problems:
        return problems
    if result["verdict"] == "no_violation" and result["violations"]:
        problems.append("verdict no_violation but violations is not empty")
    if result["verdict"] == "violation" and result["status"] == "done" and not result["violations"]:
        problems.append("verdict violation but violations is empty")
    for i, v in enumerate(result.get("violations", [])):
        t = float(v["timecode_sec"])
        ts = [float(f["timestamp_sec"]) for f in v["evidence_frames"]]
        if not any(abs(x - t) <= evidence_tolerance_s for x in ts):
            problems.append(f"violations[{i}]: no evidence frame within ±{evidence_tolerance_s}s of timecode {t}")
        if check_images:
            for j, f in enumerate(v["evidence_frames"]):
                try:
                    raw = base64.b64decode(f["image_base64"], validate=True)
                except Exception as e:  # noqa: BLE001
                    problems.append(f"violations[{i}].evidence_frames[{j}]: bad base64 ({e})")
                    continue
                if raw[:3] != b"\xff\xd8\xff":
                    problems.append(f"violations[{i}].evidence_frames[{j}]: not a JPEG")
                if f["image_base64"].startswith("data:"):
                    problems.append(f"violations[{i}].evidence_frames[{j}]: data-URI prefix is not allowed")
        if not any("Ѐ" <= ch <= "ӿ" for ch in v["type"]):
            problems.append(f"violations[{i}]: type must be in Russian")
        if not any("Ѐ" <= ch <= "ӿ" for ch in v["description"]):
            problems.append(f"violations[{i}]: description must be in Russian")
    return problems


def assert_valid(result: dict[str, Any], **kw) -> None:
    problems = validate_result(result, **kw)
    if problems:
        raise ValueError("invalid result:\n  " + "\n  ".join(problems))
