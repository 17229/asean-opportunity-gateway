"""Readiness: fixed criteria, decided by rules, never by the model.

The model only finds quotes. A criterion counts as evidenced only when its
quote really appears in the founder's text (or comes from an uploaded slide).
No percentages, no success prediction.
"""
import re

CRITERIA = [
    {"id": "problem", "area": "Market demand",
     "question": "Is a specific customer problem described?"},
    {"id": "customer", "area": "Market demand",
     "question": "Is a target customer segment named?"},
    {"id": "demand_evidence", "area": "Market demand",
     "question": "Is there evidence customers want it (interviews, waitlist, pilots, letters of intent, sales)?"},
    {"id": "solution", "area": "Feasibility",
     "question": "Is the solution described concretely?"},
    {"id": "prototype", "area": "Feasibility",
     "question": "Is there a prototype, MVP or working product?"},
    {"id": "risks", "area": "Feasibility",
     "question": "Are key technical, regulatory or operational risks identified?"},
    {"id": "team", "area": "Execution",
     "question": "Is the team and their relevant experience described?"},
    {"id": "business_model", "area": "Execution",
     "question": "Is it stated how the startup makes money?"},
    {"id": "next_milestone", "area": "Execution",
     "question": "Is a next milestone with a date or timeframe stated?"},
]

AREAS = ["Market demand", "Feasibility", "Execution"]

EVIDENCED = "Evidenced"
UNVERIFIED = "Quote not found in text"
MISSING = "Missing"


def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def assess(evidence, submission_text):
    """evidence: {criterion_id: {"quote": str, "source": "text" | "slide"}}."""
    text = _norm(submission_text)
    results = []
    for c in CRITERIA:
        item = evidence.get(c["id"]) or {}
        quote = (item.get("quote") or "").strip()
        source = item.get("source") or "text"
        if not quote:
            status = MISSING
        elif source == "slide":
            status = EVIDENCED
        elif _norm(quote) in text:
            status = EVIDENCED
        else:
            status = UNVERIFIED
        results.append({**c, "status": status, "quote": quote, "source": source})
    return results


def area_summary(results):
    summary = {}
    for area in AREAS:
        items = [r for r in results if r["area"] == area]
        met = sum(r["status"] == EVIDENCED for r in items)
        if met == len(items):
            level = "Complete"
        elif met == 0:
            level = "No evidence"
        else:
            level = "Partial"
        summary[area] = {"level": level, "met": met, "total": len(items)}
    return summary


def gaps(results):
    return [r for r in results if r["status"] != EVIDENCED]


def changes(old, new):
    """Criteria that became evidenced, or stopped being evidenced, between runs."""
    before = {r["id"]: r["status"] for r in old}
    gained = [r for r in new if r["status"] == EVIDENCED and before.get(r["id"]) != EVIDENCED]
    lost = [r for r in new if r["status"] != EVIDENCED and before.get(r["id"]) == EVIDENCED]
    return gained, lost
