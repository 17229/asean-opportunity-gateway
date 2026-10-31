from app.gemma import parse_json
from app.matching import ELIGIBLE, NOT_ELIGIBLE, UNCLEAR, check
from app.readiness import EVIDENCED, MISSING, UNVERIFIED, area_summary, assess, changes

TEXT = "We interviewed 25 shop owners.  We have a working prototype."


def test_quote_must_appear_in_text():
    r = {x["id"]: x for x in assess({
        "demand_evidence": {"quote": "we interviewed 25 shop owners.", "source": "text"},
        "prototype": {"quote": "We have 1000 paying users", "source": "text"},
    }, TEXT)}
    assert r["demand_evidence"]["status"] == EVIDENCED
    assert r["prototype"]["status"] == UNVERIFIED
    assert r["team"]["status"] == MISSING


def test_slide_quotes_count():
    r = {x["id"]: x for x in assess({"team": {"quote": "3 founders", "source": "slide"}}, TEXT)}
    assert r["team"]["status"] == EVIDENCED


def test_area_levels_have_no_percentages():
    results = assess({"problem": {"quote": "We interviewed 25 shop owners."}}, TEXT)
    s = area_summary(results)
    assert s["Market demand"] == {"level": "Partial", "met": 1, "total": 3}
    assert s["Execution"]["level"] == "No evidence"


def test_changes_between_versions():
    old = assess({}, TEXT)
    new = assess({"prototype": {"quote": "We have a working prototype."}}, TEXT)
    gained, lost = changes(old, new)
    assert [g["id"] for g in gained] == ["prototype"] and lost == []


PROG = {"id": "p", "name": "P", "countries": ["Malaysia"], "stages": ["prototype"],
        "sectors": ["ANY"], "incorporated_required": True, "min_team_size": 2,
        "required_evidence": ["prototype"]}


def profile(**kw):
    base = {"country": "Malaysia", "stage": "prototype", "sector": "retail",
            "incorporated": True, "team_size": 3}
    return {**base, **kw}


def test_eligible_with_outstanding_evidence():
    m = check(profile(), PROG, assess({}, TEXT))
    assert m["verdict"] == ELIGIBLE
    assert m["outstanding"] == ["Is there a prototype, MVP or working product?"]


def test_failed_requirement_wins():
    m = check(profile(incorporated=False, team_size=None), PROG, [])
    assert m["verdict"] == NOT_ELIGIBLE


def test_unknown_gives_one_question():
    m = check(profile(incorporated=None), PROG, [])
    assert m["verdict"] == UNCLEAR
    assert m["confirm"] == "Is the startup a registered company?"


def test_parse_json_handles_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
