"""Knowledge-base tests: every rule-card quote must occur verbatim in the stored act text;
every card must point at an existing act and clause; the mapping type_id -> card is deterministic."""

import json
from pathlib import Path

import pytest

from forte_ai.kb import KnowledgeBase, normalize_quote_text

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "kb"


@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    return KnowledgeBase(KB_DIR)


def test_kb_files_exist():
    assert (KB_DIR / "rule_cards.json").exists()
    assert list((KB_DIR / "laws").glob("*.json")), "kb/laws/*.json missing — run scripts/kb_build.py"


def test_every_card_has_required_fields(kb: KnowledgeBase):
    required = {"type_id", "name_ru", "document", "doc_id", "clause", "clause_num", "quote", "url", "observed_as_ru"}
    raw = json.loads((KB_DIR / "rule_cards.json").read_text(encoding="utf-8"))
    for c in raw["cards"]:
        missing = required - set(c)
        assert not missing, f"{c.get('type_id')}: missing {missing}"
        assert c["url"].startswith("https://adilet.zan.kz/rus/docs/"), c["type_id"]
        assert c["name_ru"].strip(), c["type_id"]
        assert any("Ѐ" <= ch <= "ӿ" for ch in c["name_ru"]), f"{c['type_id']}: name must be Russian"


def test_every_card_points_to_a_stored_act_and_clause(kb: KnowledgeBase):
    for card in kb.cards.values():
        assert card.doc_id in kb.laws, f"{card.type_id}: unknown act {card.doc_id}"
        doc = kb.laws[card.doc_id]
        assert any(e["clause"] == card.clause_num for e in doc["clauses"].values()), (
            f"{card.type_id}: clause {card.clause_num} not found in {card.doc_id}"
        )
        if card.subclause_num:
            ok = any(
                e["clause"] == card.clause_num and card.subclause_num in e["subclauses"] for e in doc["clauses"].values()
            )
            assert ok, f"{card.type_id}: subclause {card.subclause_num} not found in п.{card.clause_num}"


def test_every_quote_is_verbatim(kb: KnowledgeBase):
    problems = kb.verify_all()
    assert not problems, "\n".join(problems)


def test_quote_check_is_whitespace_tolerant_but_not_fuzzy(kb: KnowledgeBase):
    card = next(iter(kb.cards.values()))
    spaced = card.quote.replace(" ", "  ")
    assert kb.verify_quote(card.doc_id, spaced, clause_num=card.clause_num)
    assert not kb.verify_quote(card.doc_id, card.quote + " выдуманное слово", clause_num=card.clause_num)
    assert not kb.verify_quote(card.doc_id, "этой фразы нет в тексте акта", clause_num=card.clause_num)


def test_normalize_quote_text():
    assert normalize_quote_text("  a  b\n c ") == "a b c"


def test_each_type_has_exactly_one_card(kb: KnowledgeBase):
    raw = json.loads((KB_DIR / "rule_cards.json").read_text(encoding="utf-8"))
    ids = [c["type_id"] for c in raw["cards"]]
    assert len(ids) == len(set(ids))
    assert "protocol_deviation_other" in ids, "catch-all type must have a card"


def test_unverified_seeds_are_flagged(kb: KnowledgeBase):
    # If any act could not be fetched, its cards must say so explicitly (SOURCES.md documents it).
    for card in kb.cards.values():
        doc = kb.laws[card.doc_id]
        if card.verified_by_agent:
            assert doc.get("source_sha256"), f"{card.type_id}: verified card but act has no fetched source hash"


def test_act_json_structure(kb: KnowledgeBase):
    for sid, doc in kb.laws.items():
        for key in ("doc_id", "title", "canonical_url", "items", "clauses", "fetched_at"):
            assert key in doc, f"{sid}: missing {key}"
        assert doc["items"], sid
        for it in doc["items"]:
            assert it["text"].strip(), f"{sid}: empty item"
