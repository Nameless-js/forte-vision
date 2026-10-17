"""Unit tests for label parsing (video ids, free-text timestamps, label words, LOVO groups)."""

from pathlib import Path

import pytest

from forte_ai.labels import (
    LABEL_CLEAN,
    LABEL_VIOLATION,
    LabelRow,
    build_label_rows,
    lovo_groups,
    normalize_label,
    parse_timestamp,
    parse_video_id,
)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("X-1", 1),
        ("X-2", 2),
        ("Х-3", 3),  # Cyrillic Х (U+0425)
        ("Х-10", 10),
        ("Х-47.mov", 47),
        ("public/Х-48.mov", 48),
        ("C:/videos/X-12.MOV", 12),
        ("video_017.mov", 17),
        ("  Х-5  ", 5),
        ("noid.mov", None),
    ],
)
def test_parse_video_id(name, expected):
    assert parse_video_id(name) == expected


def test_latin_and_cyrillic_x_map_to_same_id():
    assert parse_video_id("X-7") == parse_video_id("Х-7") == 7
    assert "X" != "Х"  # sanity: they really are different code points


@pytest.mark.parametrize(
    "text,expected",
    [
        ("22 секунда", 22.0),
        ("10 секунда", 10.0),
        ("57 секунда", 57.0),
        ("5 секунда", 5.0),
        ("1минута 8 секунда", 68.0),
        ("1 минута 8 секунда", 68.0),
        ("1 мин 8 сек", 68.0),
        ("2 минуты 5 секунд", 125.0),
        ("1 мин", 60.0),
        ("1:08", 68.0),
        ("01:02:03", 3723.0),
        ("68", 68.0),
        ("68.5", 68.5),
        ("68,5", 68.5),
        ("11-я секунда", 11.0),
        ("на 22 секунде", 22.0),
        ("22 сек.", 22.0),
        ("22s", 22.0),
        ("1m 8s", 68.0),
        (44.2, 44.2),
        (7, 7.0),
        ("", None),
        (None, None),
    ],
)
def test_parse_timestamp(text, expected):
    assert parse_timestamp(text) == expected


def test_parse_timestamp_rejects_text_without_number():
    with pytest.raises(ValueError):
        parse_timestamp("нет данных")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("нарушение", LABEL_VIOLATION),
        ("Нарушение ", LABEL_VIOLATION),
        ("без нарушения", LABEL_CLEAN),
        ("Без нарушения", LABEL_CLEAN),
        ("нет нарушения", LABEL_CLEAN),
    ],
)
def test_normalize_label(text, expected):
    assert normalize_label(text) == expected


def test_normalize_label_rejects_unknown():
    with pytest.raises(ValueError):
        normalize_label("unclear")


def test_build_label_rows_joins_by_id_and_adds_unlabeled(tmp_path: Path):
    vids = {}
    for name in ["X-1.mov", "Х-2.mov", "Х-6.mov"]:
        p = tmp_path / name
        p.write_bytes(name.encode("utf-8"))
        vids[parse_video_id(name)] = p
    raw = [
        {"raw_name": "X-1", "raw_timestamp": "22 секунда", "raw_label": "нарушение"},
        {"raw_name": "Х-2", "raw_timestamp": "", "raw_label": "без нарушения"},
        {"raw_name": "Х-3", "raw_timestamp": "5 секунда", "raw_label": "нарушение"},  # no file
    ]
    rows = build_label_rows(raw, vids, tmp_path, with_md5=True)
    by_id = {r.video_id: r for r in rows}
    assert by_id[1].label == LABEL_VIOLATION and by_id[1].t_sec == 22.0 and by_id[1].path == "X-1.mov"
    assert by_id[2].label == LABEL_CLEAN and by_id[2].t_sec is None
    assert by_id[3].path == "" and by_id[3].split == "labeled"
    assert by_id[6].split == "unlabeled" and by_id[6].label == ""
    assert len(by_id[1].content_md5) == 32


def test_build_label_rows_violation_without_timestamp_fails(tmp_path: Path):
    with pytest.raises(ValueError):
        build_label_rows(
            [{"raw_name": "X-1", "raw_timestamp": "", "raw_label": "нарушение"}], {}, tmp_path, with_md5=False
        )


def test_lovo_groups_merge_duplicate_content():
    rows = [
        LabelRow(4, "a", LABEL_VIOLATION, 57.0, "labeled", "same"),
        LabelRow(47, "b", LABEL_VIOLATION, 68.0, "labeled", "same"),
        LabelRow(5, "c", LABEL_CLEAN, None, "labeled", "other"),
        LabelRow(9, "d", "", None, "unlabeled", "zzz"),
    ]
    g = lovo_groups(rows)
    assert g == {"same": [4, 47], "other": [5]}
