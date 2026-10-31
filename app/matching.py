"""Programme eligibility: published requirements checked by rules.

Unknown profile facts never count as a pass or a fail. They make the
result Unclear, with the single question that would settle it.
"""
import json
from pathlib import Path

from app.readiness import CRITERIA, EVIDENCED

ASEAN = ["Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia", "Myanmar",
         "Philippines", "Singapore", "Thailand", "Timor-Leste", "Vietnam"]
STAGES = ["idea", "prototype", "early revenue", "growth"]
SECTORS = ["agritech", "cleantech", "edtech", "fintech", "healthtech",
           "logistics", "retail", "deeptech", "other"]

ELIGIBLE = "Eligible"
NOT_ELIGIBLE = "Not eligible"
UNCLEAR = "Unclear"

DATA = Path(__file__).resolve().parent.parent / "data" / "programmes.json"


def load_programmes(path=DATA):
    return json.loads(Path(path).read_text())


def check(profile, programme, readiness_results):
    fails, unknown = [], []

    countries = programme.get("countries", ["ANY_ASEAN"])
    country = profile.get("country")
    if countries == ["ANY"]:
        pass
    elif countries != ["ANY_ASEAN"]:
        if not country:
            unknown.append("Which country is the startup based in?")
        elif country not in countries:
            fails.append(f"Based in {country}; programme accepts {', '.join(countries)}")
    elif country and country not in ASEAN:
        fails.append(f"Based in {country}, outside ASEAN")

    stage = profile.get("stage")
    if not stage:
        unknown.append("What stage is the startup at (idea, prototype, early revenue, growth)?")
    elif stage not in programme.get("stages", STAGES):
        fails.append(f"Stage is {stage}; programme takes {', '.join(programme['stages'])}")

    sectors = programme.get("sectors", ["ANY"])
    sector = profile.get("sector")
    if sectors != ["ANY"]:
        if not sector:
            unknown.append("Which sector is the startup in?")
        elif sector not in sectors:
            fails.append(f"Sector is {sector}; programme focuses on {', '.join(sectors)}")

    if programme.get("incorporated_required"):
        inc = profile.get("incorporated")
        if inc is None:
            unknown.append("Is the startup a registered company?")
        elif inc is False:
            fails.append("Programme requires a registered company")

    min_unreg = programme.get("min_team_size_if_unregistered") or 0
    if min_unreg:
        inc, size = profile.get("incorporated"), profile.get("team_size")
        if inc is True:
            pass
        elif inc is False and size is not None and size < min_unreg:
            fails.append(f"Not registered and team of {size}; programme needs a registered company "
                         f"or at least {min_unreg} people")
        elif inc is False and size is None:
            unknown.append("How many people are on the founding team?")
        elif inc is None and (size is None or size < min_unreg):
            unknown.append("Is the startup a registered company?")

    min_team = programme.get("min_team_size") or 0
    if min_team:
        size = profile.get("team_size")
        if size is None:
            unknown.append("How many people are on the founding team?")
        elif size < min_team:
            fails.append(f"Team of {size}; programme needs at least {min_team}")

    status = {r["id"]: r["status"] for r in readiness_results}
    names = {c["id"]: c["question"] for c in CRITERIA}
    outstanding = [names[cid] for cid in programme.get("required_evidence", [])
                   if status.get(cid) != EVIDENCED]

    if fails:
        verdict, reasons, confirm = NOT_ELIGIBLE, fails, None
    elif unknown:
        verdict, reasons, confirm = UNCLEAR, ["Missing profile facts"], unknown[0]
    else:
        verdict, reasons, confirm = ELIGIBLE, ["Meets the requirements this app checks"], None

    return {"programme": programme, "verdict": verdict, "reasons": reasons,
            "confirm": confirm, "outstanding": outstanding}


def match_all(profile, programmes, readiness_results):
    order = {ELIGIBLE: 0, UNCLEAR: 1, NOT_ELIGIBLE: 2}
    results = [check(profile, p, readiness_results) for p in programmes]
    return sorted(results, key=lambda r: (order[r["verdict"]], len(r["outstanding"])))
