"""Readiness: fixed criteria, decided by rules, never by the model.

Gemma only highlights quotes. A criterion counts only when its quote really
appears in the founder's text (or comes from an uploaded slide) AND passes the
criterion's hard rule. Everything here is what the founder states; nothing is
verified. No percentages, no success prediction.
"""
import re

MONTHS = r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"

CRITERIA = [
    {"id": "problem", "area": "Market demand",
     "question": "Is a specific customer problem described?",
     "counts": "A concrete pain for a specific group, e.g. \"shop owners only notice empty shelves after customers ask\"",
     "not_counts": "Vague claims like \"people struggle\" or \"it's inefficient\""},
    {"id": "customer", "area": "Market demand",
     "question": "Is a target customer segment named?",
     "counts": "A named group, e.g. \"independent clinics with 1 to 5 doctors\"",
     "not_counts": "\"Everyone\", \"all businesses\", \"the mass market\""},
    {"id": "demand_evidence", "area": "Market demand",
     "question": "Is there evidence customers want it?",
     "counts": "Interviews, waitlist, pilot, letters of intent or sales, with a number",
     "not_counts": "\"Everyone needs this\", \"huge market\", \"people will love it\"",
     "rule": "must contain a number"},
    {"id": "solution", "area": "Feasibility",
     "question": "Is the solution described concretely?",
     "counts": "What the product does and how, e.g. \"owner sends a shelf photo, we create a reorder list\"",
     "not_counts": "\"An AI platform\", \"an app like Grab for X\" with no detail"},
    {"id": "prototype", "area": "Feasibility",
     "question": "Is there a prototype, MVP or working product?",
     "counts": "Something that exists now, e.g. \"working MVP used by 3 clinics\"",
     "not_counts": "Plans: \"we will build\", \"we plan to launch\"",
     "rule": "must describe something that exists, not a plan"},
    {"id": "risks", "area": "Feasibility",
     "question": "Are key technical, regulatory or operational risks identified?",
     "counts": "A named risk, e.g. \"sensor battery life in heavy rain\"",
     "not_counts": "\"No risks\", \"low risk\""},
    {"id": "team", "area": "Execution",
     "question": "Is the team and their relevant experience described?",
     "counts": "Roles or experience, e.g. \"a former clinic manager and a software engineer\"",
     "not_counts": "\"Passionate team\", \"hardworking founders\"",
     "rule": "must mention a role or experience"},
    {"id": "business_model", "area": "Execution",
     "question": "Is it stated how the startup makes money?",
     "counts": "Who pays and how, e.g. \"RM30 per sensor per month\"",
     "not_counts": "\"We will monetise later\", \"ads maybe\"",
     "rule": "must mention a price, fee or who pays"},
    {"id": "next_milestone", "area": "Execution",
     "question": "Is a next milestone with a date or timeframe stated?",
     "counts": "A target with a date, e.g. \"50 paying farms by June 2027\"",
     "not_counts": "\"Grow fast\", \"scale across ASEAN\"",
     "rule": "must contain a date or timeframe"},
]

AREAS = ["Market demand", "Feasibility", "Execution"]

EVIDENCED = "Evidence stated"
NOT_ACHIEVED = "Explicitly not achieved"
UNVERIFIED = "Quote not found in text"
FAILS_RULE = "Fails rule"
MISSING = "Missing"

SOURCE_LABEL = {"text": "Founder said", "slide": "From uploaded slide"}

ROLE_WORDS = (r"engineer|developer|designer|manager|former|ex-|years|experience|"
              r"\bcto\b|\bceo\b|\bcoo\b|analyst|scientist|doctor|nurse|teacher|"
              r"accountant|lawyer|agronomist|sales|marketer|marketing|researcher|"
              r"phd|operations|consultant|rep\b|worked|founded")
MONEY_WORDS = (r"\brm\s?\d|\$|\brp\b|usd|sgd|thb|php|vnd|idr|per month|per year|"
               r"per order|per user|subscription|commission|\bfee\b|charge|"
               r"\bpays?\b|pricing|price|licen[cs]e|revenue")


NEGATION = (r"\b(haven't|have not|hasn't|has not|hadn't|had not|not yet|yet to|don't|do not|"
            r"doesn't|does not|didn't|did not|never|without|zero|none|nobody|no one|0 \w+|"
            r"no (customers?|users?|sales|revenue|pilots?|prototype|product|mvp|plan|team|"
            r"interviews?|money|income|date|timeline|milestones?))\b")
NEGATION_CHECKED = {"demand_evidence", "prototype", "team", "business_model", "next_milestone"}


def _norm(s):
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def hard_rule(cid, quote):
    """Return why the quote fails the criterion's rule, or None if it passes."""
    q = _norm(quote)
    if cid in NEGATION_CHECKED and re.search(NEGATION, q):
        return "Says this does not exist yet (negation), so it is not evidence"
    if cid == "demand_evidence" and not re.search(r"\d", q):
        return "No number found (how many interviews, users, pilots or sales?)"
    if cid == "next_milestone" and not re.search(
            rf"\b20\d\d\b|\b({MONTHS})[a-z]*\b|\bq[1-4]\b|\bwithin\b|\d+\s*(day|week|month|year)s?", q):
        return "No date or timeframe found"
    if cid == "team" and not re.search(ROLE_WORDS, q):
        return "No role or experience mentioned"
    if cid == "business_model" and not re.search(MONEY_WORDS, q):
        return "No price, fee or payer mentioned"
    if cid == "prototype":
        plan = re.search(r"\b(will|plan(ning)? to|going to|want to|aim to|intend to)\b", q)
        exists = re.search(r"\b(have|has|had|built|launched|used|uses|live|running|tested|piloted|working)\b", q)
        if plan and not exists:
            return "Describes a plan, not something that exists"
    return None


def _negative(quote, source, text):
    """A quote in which the founder says this is not done yet."""
    return bool(quote) and (source == "slide" or _norm(quote) in text) and re.search(NEGATION, _norm(quote))


def assess(evidence, submission_text):
    """evidence: {criterion_id: {"quote": str, "source": "text" | "slide",
                                 "negative_quote": str}}."""
    text = _norm(submission_text)
    results = []
    for c in CRITERIA:
        item = evidence.get(c["id"]) or {}
        quote = (item.get("quote") or "").strip()
        negative = (item.get("negative_quote") or "").strip()
        source = item.get("source") or "text"
        reason = None
        if quote and source != "slide" and _norm(quote) not in text:
            status = UNVERIFIED
        elif quote:
            reason = hard_rule(c["id"], quote)
            status = FAILS_RULE if reason else EVIDENCED
            if reason and _negative(quote, source, text):
                status, reason = NOT_ACHIEVED, "Founder states this has not been done"
        else:
            status = MISSING
        if status != EVIDENCED and _negative(negative, source, text):
            status, reason, quote = NOT_ACHIEVED, "Founder states this has not been done", negative
        results.append({**c, "status": status, "quote": quote, "source": source,
                        "source_label": SOURCE_LABEL.get(source, "Unknown"), "reason": reason})
    return results


def area_summary(results):
    summary = {}
    for area in AREAS:
        items = [r for r in results if r["area"] == area]
        met = sum(r["status"] == EVIDENCED for r in items)
        if met == len(items):
            level = "All addressed"
        elif met == 0:
            level = "None addressed"
        else:
            level = "Partly addressed"
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


CONTRADICTED = "Contradicted in submission"


def apply_conflicts(results, conflicts):
    """A quote that sits inside a self-contradicting claim never counts as evidence."""
    claims = [_norm(x) for c in conflicts for x in (c["first"], c["second"])]
    for r in results:
        q = _norm(r["quote"])
        if r["status"] == EVIDENCED and q and any(q in c or c in q for c in claims):
            r["status"], r["reason"] = CONTRADICTED, "The submission contradicts this claim"
    return results
