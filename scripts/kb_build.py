"""Build kb/laws/*.json from saved HTML pages of the acts (zakon.uchet.kz mirror of adilet.zan.kz).

The mirror renders every paragraph of an act as `<p id="zNNN">...</p>` (headings as `<h3>`), editorial
notes as `<span class="note">Сноска. ...</span>` and suspension notices ("Примечание ИЗПИ! Действие пункта N
приостановлено до DD.MM.YYYY ... действует в следующей редакции:") as red `<font>` lines followed by the
wording that is in force. We split the text into ordered items (part / chapter / article / clause /
subclause / paragraph / note / attention) and keep the verbatim text of every paragraph, so that
rule-card quotes can be checked verbatim.

A document may contain several numbered parts (the resolution body, the Rules themselves, appendices);
clause numbers restart in each part. The part with the most clauses is the "main" part (the Rules) and
`clauses` is built from it; the other parts are kept under `other_parts`.

Usage:
  python scripts/kb_build.py --html data/laws_raw --out kb/laws
  python scripts/kb_build.py --fetch --out kb/laws        # downloads the pages first (network!)
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html as htmlmod
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCS = {
    "V1900019680": {
        "short_id": "nbrk_231_2019",
        "structure": "clauses",
        "kind": "Постановление Правления Национального Банка Республики Казахстан",
        "number": "№ 231",
        "date": "2019-11-29",
        "date_ru": "29 ноября 2019 года",
        "registration": "Зарегистрировано в Министерстве юстиции Республики Казахстан 3 декабря 2019 года № 19680",
        "canonical_url": "https://adilet.zan.kz/rus/docs/V1900019680",
        "mirror_url": "https://zakon.uchet.kz/rus/docs/V1900019680",
    },
    "V2000020075": {
        "short_id": "nbrk_14_2020",
        "structure": "clauses",
        "kind": "Постановление Правления Национального Банка Республики Казахстан",
        "number": "№ 14",
        "date": "2020-02-24",
        "date_ru": "24 февраля 2020 года",
        "registration": "Зарегистрировано в Министерстве юстиции Республики Казахстан 27 февраля 2020 года № 20075",
        "canonical_url": "https://adilet.zan.kz/rus/docs/V2000020075",
        "mirror_url": "https://zakon.uchet.kz/rus/docs/V2000020075",
    },
    "Z090000191_": {
        "short_id": "law_191_iv_2009",
        "structure": "articles",
        "kind": "Закон Республики Казахстан",
        "number": "№ 191-IV",
        "date": "2009-08-28",
        "date_ru": "28 августа 2009 года",
        "registration": "",
        "canonical_url": "https://adilet.zan.kz/rus/docs/Z090000191_",
        "mirror_url": "https://zakon.uchet.kz/rus/docs/Z090000191_",
    },
    "V2400035552": {
        "short_id": "nbrk_88_2024",
        "structure": "clauses",
        "kind": "Постановление Правления Национального Банка Республики Казахстан",
        "number": "№ 88",
        "date": "2024-12-24",
        "date_ru": "24 декабря 2024 года",
        "registration": "",
        "canonical_url": "https://adilet.zan.kz/rus/docs/V2400035552",
        "mirror_url": "https://zakon.uchet.kz/rus/docs/V2400035552",
    },
}

_BLOCK_RE = re.compile(r"<(p|span|h[1-6]|font)\b([^>]*)>(.*?)</\1>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_CLAUSE_RE = re.compile(r"^\"?(\d+)(?:-(\d+))?\.\s+(.*)$", re.S)
_SUB_RE = re.compile(r"^\"?(\d+(?:-\d+)?)\)\s+(.*)$", re.S)
_CHAPTER_RE = re.compile(r"^(Глава|Параграф|Раздел)\s+(\d+)", re.I)
_ARTICLE_RE = re.compile(r"^Статья\s+(\d+(?:-\d+)?)\.\s*(.*)$", re.S)
_ATT_CLAUSE_RE = re.compile(r"Действие\s+пункта\s+(\d+(?:-\d+)?)\s+приостановлено\s+до\s+(\d{2}\.\d{2}\.\d{4})", re.I)
_ATT_SUB_RE = re.compile(r"Действие\s+подпункта\s+(\d+(?:-\d+)?)\)\s+приостановлено\s+до\s+(\d{2}\.\d{2}\.\d{4})", re.I)
_ATT_OTHER_RE = re.compile(r"приостановлен[оа]?\s+до\s+(\d{2}\.\d{2}\.\d{4})", re.I)


def clean_text(fragment: str) -> str:
    t = _TAG_RE.sub(" ", fragment)
    t = htmlmod.unescape(t).replace(" ", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_main(raw: str) -> str:
    i = raw.find('class="document-detail-wrapper-main"')
    j = raw.find('id="document-detail-wrapper-slave"')
    if i < 0:
        return raw
    return raw[i : j if j > i else len(raw)]


def iter_blocks(main: str):
    """Yield (tag, attrs, text, html_id) for every text block in document order (no nesting)."""
    pos = 0
    while True:
        m = _BLOCK_RE.search(main, pos)
        if not m:
            break
        tag, attrs, inner = m.group(1).lower(), m.group(2), m.group(3)
        # a <p> may wrap other blocks (tables) — fine, we only need text; but a <font> or <span>
        # may contain nested <p>; take the outer text and skip the inner blocks.
        text = clean_text(inner)
        hid = re.search(r'id="([^"]+)"', attrs)
        yield tag, attrs, text, (hid.group(1) if hid else "")
        pos = m.end()


def parse_document(raw: str, structure: str) -> tuple[list[dict], str]:
    """Return (ordered list of items, title)."""
    main = extract_main(raw)
    title_m = re.search(r"<title>(.*?)</title>", raw, re.S)
    items: list[dict] = []
    part = 0
    part_max_clause = 0  # highest clause number seen in the current part
    cur_clause: str | None = None
    cur_sub: str | None = None
    cur_article: str | None = None
    pending: dict | None = None  # suspension notice waiting for its clause/subclause
    temp_open: dict | None = None  # temporary wording currently being read

    def new_item(typ: str, text: str, hid: str) -> dict:
        return {
            "type": typ,
            "part": part,
            "article": cur_article,
            "clause": cur_clause,
            "subclause": None,
            "text": text,
            "html_id": hid,
        }

    for tag, attrs, text, hid in iter_blocks(main):
        if not text:
            continue
        if tag == "span" and "note" not in attrs:
            continue
        # ---- notes and suspension notices ----
        if text.startswith("Сноска.") or (tag == "span" and "note" in attrs):
            items.append(new_item("note", text, hid))
            continue
        am, asub = _ATT_CLAUSE_RE.search(text), _ATT_SUB_RE.search(text)
        if am or asub or text.startswith("Внимание!") or text.startswith("Примечание ИЗПИ"):
            it = new_item("attention", text, hid)
            if am:
                pending = {"clause": am.group(1), "sub": None, "until": am.group(2)}
                it["suspends"] = {"clause": am.group(1), "until": am.group(2)}
            elif asub:
                pending = {"clause": cur_clause, "sub": asub.group(1), "until": asub.group(2)}
                it["suspends"] = {"clause": cur_clause, "subclause": asub.group(1), "until": asub.group(2)}
            items.append(it)
            continue
        if tag == "font":  # other red editorial lines
            items.append(new_item("note", text, hid))
            continue
        # ---- structure ----
        if tag.startswith("h") and not _CHAPTER_RE.match(text) and not _ARTICLE_RE.match(text):
            # a document/appendix heading: starts a new part if we already have clauses in this part
            if part_max_clause > 0:
                part += 1
                part_max_clause = 0
                cur_clause, cur_sub = None, None
            items.append(new_item("heading", text, hid))
            continue
        if _CHAPTER_RE.match(text):
            items.append(new_item("chapter", text, hid))
            continue
        art = _ARTICLE_RE.match(text)
        if art and structure == "articles":
            cur_article, cur_clause, cur_sub = art.group(1), None, None
            it = new_item("article", text, hid)
            items.append(it)
            continue
        cm = _CLAUSE_RE.match(text)
        if cm:
            n = int(cm.group(1))
            num = cm.group(1) + (f"-{cm.group(2)}" if cm.group(2) else "")
            if structure == "clauses" and n == 1 and part_max_clause >= 2 and not cm.group(2):
                part += 1  # numbering restarted -> a new part (appendix)
                part_max_clause = 0
            part_max_clause = max(part_max_clause, n)
            cur_clause, cur_sub = num, None
            it = new_item("clause", text, hid)
            if pending and pending["sub"] is None and pending["clause"] == num:
                it["variant"] = "temporary"
                it["in_force_until"] = pending["until"]
                temp_open = {"clause": num, "until": pending["until"], "part": part}
                pending = None
            else:
                temp_open = None
                if pending and pending["sub"] is None:
                    pending = None
            items.append(it)
            continue
        sm = _SUB_RE.match(text)
        if sm:
            cur_sub = sm.group(1)
            it = new_item("subclause", text, hid)
            it["subclause"] = cur_sub
            if temp_open and temp_open["clause"] == cur_clause:
                it["variant"] = "temporary"
                it["in_force_until"] = temp_open["until"]
            elif pending and pending["sub"] == cur_sub and pending["clause"] == cur_clause:
                it["variant"] = "temporary"
                it["in_force_until"] = pending["until"]
                pending = None
            items.append(it)
            continue
        # ---- plain paragraph continuing the current clause / subclause ----
        it = new_item("paragraph", text, hid)
        it["subclause"] = cur_sub
        if temp_open and temp_open["clause"] == cur_clause:
            it["variant"] = "temporary"
            it["in_force_until"] = temp_open["until"]
        items.append(it)
    return items, (clean_text(title_m.group(1)) if title_m else "")


def _index_part(items: list[dict], structure: str) -> dict:
    """clause (or article) number -> {text, subclauses{}, notes[], variant}"""
    idx: dict[str, dict] = {}
    last_key: dict[str, str] = {}
    for it in items:
        if structure == "articles":
            c = it.get("article")
            if c is None or it["type"] in ("chapter", "heading"):
                continue
            ent = idx.setdefault(c, {"clause": c, "variant": "current", "paragraphs": [], "subclauses": {}, "notes": [], "html_ids": []})
            if it["type"] in ("note", "attention"):
                ent["notes"].append(it["text"])
                continue
            ent["paragraphs"].append(it["text"])
            ent["html_ids"].append(it.get("html_id", ""))
            if it["type"] == "clause" and it.get("clause"):
                ent["subclauses"].setdefault(it["clause"], []).append(it["text"])
            elif it.get("clause"):
                ent["subclauses"].setdefault(it["clause"], []).append(it["text"])
            continue
        c = it.get("clause")
        if c is None or it["type"] in ("chapter", "heading"):
            continue
        variant = it.get("variant", "current")
        key = c if variant == "current" else f"{c}@{variant}"
        if it["type"] in ("note", "attention"):
            # notes follow the wording they describe: attach to the latest entry of this clause
            key = last_key.get(c, key)
            ent = idx.setdefault(key, {"clause": c, "variant": variant, "paragraphs": [], "subclauses": {}, "notes": [], "html_ids": []})
            ent["notes"].append(it["text"])
            continue
        ent = idx.setdefault(key, {"clause": c, "variant": variant, "paragraphs": [], "subclauses": {}, "notes": [], "html_ids": []})
        last_key[c] = key
        ent["paragraphs"].append(it["text"])
        ent["html_ids"].append(it.get("html_id", ""))
        if it.get("subclause"):
            ent["subclauses"].setdefault(it["subclause"], []).append(it["text"])
        if it.get("in_force_until"):
            ent["in_force_until"] = it["in_force_until"]
    for ent in idx.values():
        ent["text"] = " ".join(ent["paragraphs"])
        ent["subclauses"] = {k: " ".join(v) for k, v in ent["subclauses"].items()}
        ent.pop("paragraphs", None)
    return idx


def build_indexes(items: list[dict], structure: str) -> tuple[dict, int, list[dict]]:
    parts = sorted({it["part"] for it in items})
    per_part = {p: [it for it in items if it["part"] == p] for p in parts}
    if structure == "articles":
        return _index_part(items, structure), 0, []
    counts = {p: sum(1 for it in its if it["type"] == "clause") for p, its in per_part.items()}
    main_part = max(counts, key=lambda p: counts[p]) if counts else 0
    others = []
    for p, its in per_part.items():
        if p == main_part:
            continue
        heading = next((it["text"] for it in its if it["type"] == "heading"), "")
        others.append({"part": p, "heading": heading, "n_clauses": counts[p], "clauses": _index_part(its, structure)})
    return _index_part(per_part[main_part], structure), main_part, others


def build_one(doc_id: str, html_path: Path, out_dir: Path) -> Path:
    meta = DOCS[doc_id]
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    items, title = parse_document(raw, meta["structure"])
    clauses, main_part, others = build_indexes(items, meta["structure"])
    main_heading = next((it["text"] for it in items if it["part"] == main_part and it["type"] == "heading"), "")
    doc = {
        "doc_id": doc_id,
        "short_id": meta["short_id"],
        "structure": meta["structure"],
        "title": title,
        "main_part_heading": main_heading,
        "kind": meta["kind"],
        "number": meta["number"],
        "date": meta["date"],
        "date_ru": meta["date_ru"],
        "registration": meta["registration"],
        "canonical_url": meta["canonical_url"],
        "mirror_url": meta["mirror_url"],
        "fetched_from": meta["mirror_url"],
        "fetched_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_sha256": hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest(),
        "n_items": len(items),
        "n_parts": len({it["part"] for it in items}),
        "main_part": main_part,
        "n_clauses": len(clauses),
        "suspended": [it["suspends"] for it in items if it.get("suspends")],
        "clauses": clauses,
        "other_parts": others,
        "items": items,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{meta['short_id']}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def fetch(doc_id: str, dest: Path) -> Path:
    import urllib.request

    url = DOCS[doc_id]["mirror_url"]
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    dest.mkdir(parents=True, exist_ok=True)
    p = dest / f"uchet_{doc_id}.html"
    p.write_bytes(data)
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "data" / "laws_raw"), help="dir with uchet_<ID>.html files")
    ap.add_argument("--out", default=str(ROOT / "kb" / "laws"))
    ap.add_argument("--fetch", action="store_true", help="download the pages into --html first")
    ap.add_argument("--docs", nargs="*", default=list(DOCS))
    a = ap.parse_args()
    html_dir = Path(a.html)
    for doc_id in a.docs:
        p = html_dir / f"uchet_{doc_id}.html"
        if a.fetch or not p.exists():
            print(f"fetching {doc_id} ...")
            p = fetch(doc_id, html_dir)
        out = build_one(doc_id, p, Path(a.out))
        d = json.loads(out.read_text(encoding="utf-8"))
        print(
            f"{doc_id}: {d['n_items']} items, {d['n_parts']} parts (main={d['main_part']}), "
            f"{d['n_clauses']} clauses in main part, suspended={d['suspended']} -> {out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
