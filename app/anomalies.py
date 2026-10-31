"""Instruction-like text in a submission is flagged, never obeyed, never hidden."""
import re

PATTERNS = [
    r"\bignore\b.{0,40}\b(instruction|rule|prompt|above|previous|criteria)",
    r"\bdisregard\b",
    r"\b(mark|rate|score|grade|give)\b.{0,30}\b(everything|all|every|full|perfect|100|10/10|complete|✅|eligible|approved?)\b",
    r"\byou are now\b",
    r"\b(system|developer) prompt\b",
    r"\bas an ai\b",
    r"\bnew instructions?\b",
    r"\boverride\b",
    r"\bpretend\b",
]


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def detect(text, model_flags=()):
    """Rule-based flags, plus any Gemma flagged that really appear in the text."""
    found = []
    for s in _sentences(text):
        if any(re.search(p, s, re.I) for p in PATTERNS):
            found.append({"text": s, "flagged_by": "Rule"})
    norm = re.sub(r"\s+", " ", text or "").lower()
    seen = {f["text"].lower() for f in found}
    for q in model_flags or []:
        q = (q or "").strip()
        if q and q.lower() not in seen and re.sub(r"\s+", " ", q).lower() in norm:
            found.append({"text": q, "flagged_by": "Gemma"})
    return found
