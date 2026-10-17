"""Knowledge base: verified normative sources and deterministic type_id -> rule card mapping.

No model ever generates a citation. Code attaches the rule card to a detected violation type.
"""

from .loader import KnowledgeBase, RuleCard, find_kb_dir, normalize_quote_text  # noqa: F401
