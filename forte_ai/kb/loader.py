"""Load kb/rule_cards.json and kb/laws/*.json; verify quotes verbatim against the stored act text."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_WS_RE = re.compile(r"\s+")


def normalize_quote_text(s: str) -> str:
    """Whitespace-only normalization used for the verbatim check (NBSP -> space, collapse runs)."""
    return _WS_RE.sub(" ", (s or "").replace(" ", " ")).strip()


def find_kb_dir() -> Path:
    """Locate the `kb/` directory: $FORTE_KB_DIR, then repo root, then next to the package."""
    env = os.environ.get("FORTE_KB_DIR")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    candidates = [here.parents[2] / "kb", here.parents[1] / "kb_data", Path.cwd() / "kb"]
    for c in candidates:
        if (c / "rule_cards.json").exists():
            return c
    raise FileNotFoundError("kb/rule_cards.json not found; set FORTE_KB_DIR")


@dataclass
class RuleCard:
    type_id: str
    name_ru: str
    document: str  # full document title with number and date
    doc_id: str  # short id of the act json (e.g. nbrk_231_2019)
    clause: str  # e.g. "п. 31 пп. 4"
    clause_num: str  # "31"
    subclause_num: Optional[str]  # "4" or None
    quote: str  # verbatim quote from the act
    url: str  # canonical adilet URL
    observed_as_ru: str  # how it is observed on video (for descriptions)
    verified_by_agent: bool
    secondary: list[dict] = field(default_factory=list)
    mapping_note_ru: str = ""  # non-empty when the mapping is approximate
    timecode_policy: str = ""

    def as_rule_dict(self) -> dict:
        return {
            "document": self.document,
            "clause": self.clause,
            "quote": self.quote,
            "url": self.url,
            "doc_id": self.doc_id,
            "verified_by_agent": self.verified_by_agent,
        }


class KnowledgeBase:
    def __init__(self, kb_dir: Optional[Path] = None):
        self.kb_dir = Path(kb_dir) if kb_dir else find_kb_dir()
        self.laws: dict[str, dict] = {}
        for p in sorted((self.kb_dir / "laws").glob("*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            self.laws[d["short_id"]] = d
        raw = json.loads((self.kb_dir / "rule_cards.json").read_text(encoding="utf-8"))
        self.meta = {k: v for k, v in raw.items() if k != "cards"}
        self.cards: dict[str, RuleCard] = {}
        for c in raw["cards"]:
            card = RuleCard(
                type_id=c["type_id"],
                name_ru=c["name_ru"],
                document=c["document"],
                doc_id=c["doc_id"],
                clause=c["clause"],
                clause_num=str(c["clause_num"]),
                subclause_num=(str(c["subclause_num"]) if c.get("subclause_num") not in (None, "") else None),
                quote=c["quote"],
                url=c["url"],
                observed_as_ru=c.get("observed_as_ru", ""),
                verified_by_agent=bool(c.get("verified_by_agent", False)),
                secondary=c.get("secondary", []),
                mapping_note_ru=c.get("mapping_note_ru", ""),
                timecode_policy=c.get("timecode_policy", ""),
            )
            if card.type_id in self.cards:
                raise ValueError(f"duplicate rule card for type_id {card.type_id}")
            self.cards[card.type_id] = card

    # ----- lookup -----
    def get(self, type_id: str) -> RuleCard:
        if type_id not in self.cards:
            raise KeyError(f"no rule card for type_id {type_id!r}")
        return self.cards[type_id]

    def type_ids(self) -> list[str]:
        return list(self.cards)

    def clause_text(self, doc_id: str, clause_num: str, subclause_num: Optional[str] = None, variant: str = "current") -> str:
        doc = self.laws[doc_id]
        key = clause_num if variant == "current" else f"{clause_num}@{variant}"
        ent = doc["clauses"].get(key)
        if ent is None or not ent.get("text"):
            # fall back to whichever variant carries the text (e.g. the temporary wording in force)
            cands = [e for e in doc["clauses"].values() if e["clause"] == str(clause_num) and e.get("text")]
            if not cands:
                raise KeyError(f"{doc_id}: clause {clause_num} not found")
            ent = cands[0]
        if subclause_num:
            return ent["subclauses"][str(subclause_num)]
        return ent["text"]

    def article_text(self, doc_id: str, article: str) -> str:
        doc = self.laws[doc_id]
        return " ".join(it["text"] for it in doc["items"] if it.get("article") == str(article))

    # ----- verification -----
    def verify_quote(self, doc_id: str, quote: str, clause_num: Optional[str] = None, article: Optional[str] = None) -> bool:
        """True iff `quote` occurs verbatim (modulo whitespace) in the stored text of the act.

        If clause_num is given the quote must occur inside that clause (any variant); if article is
        given it must occur inside that article; otherwise anywhere in the document.
        """
        q = normalize_quote_text(quote)
        if not q:
            return False
        doc = self.laws[doc_id]
        if clause_num is not None:
            hay = " ".join(
                normalize_quote_text(e["text"]) for k, e in doc["clauses"].items() if e["clause"] == str(clause_num)
            )
        elif article is not None:
            hay = normalize_quote_text(self.article_text(doc_id, article))
        else:
            hay = " ".join(normalize_quote_text(it["text"]) for it in doc["items"])
        return q in hay

    def verify_all(self) -> list[str]:
        """Return a list of human-readable problems (empty when every quote is verbatim)."""
        problems = []
        for card in self.cards.values():
            if card.doc_id not in self.laws:
                problems.append(f"{card.type_id}: unknown doc_id {card.doc_id}")
                continue
            if not self.verify_quote(card.doc_id, card.quote, clause_num=card.clause_num):
                problems.append(f"{card.type_id}: quote not verbatim in {card.doc_id} п.{card.clause_num}: {card.quote[:80]!r}")
            for s in card.secondary:
                if s.get("doc_id") not in self.laws:
                    problems.append(f"{card.type_id}/secondary: unknown doc_id {s.get('doc_id')}")
                    continue
                ok = self.verify_quote(s["doc_id"], s["quote"], clause_num=s.get("clause_num"), article=s.get("article"))
                if not ok:
                    problems.append(f"{card.type_id}/secondary: quote not verbatim in {s['doc_id']}: {s['quote'][:80]!r}")
        return problems
