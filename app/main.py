"""ASEAN Opportunity Gateway: submit, assess, match, track, improve."""
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

from app import gemma
from app.matching import ELIGIBLE, NOT_ELIGIBLE, UNCLEAR, load_programmes, match_all
from app.readiness import AREAS, EVIDENCED, area_summary, assess, changes, gaps

load_dotenv()
try:
    for k in ("GEMINI_API_KEY", "GEMMA_MODEL"):
        if k in st.secrets:
            os.environ.setdefault(k, st.secrets[k])
except Exception:
    pass

st.set_page_config(page_title="ASEAN Opportunity Gateway", page_icon="🌏", layout="wide")
ss = st.session_state
ss.setdefault("history", [])   # past assessments, newest last
ss.setdefault("tracker", [])   # applications the founder is tracking

TRACK_STATES = ["Interested", "Preparing", "Submitted", "Interview", "Accepted", "Rejected"]
SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_submission.txt"
LEVEL_ICON = {"Complete": "🟢", "Partial": "🟡", "No evidence": "🔴"}
VERDICT_ICON = {ELIGIBLE: "✅", UNCLEAR: "❔", NOT_ELIGIBLE: "⛔"}

st.title("🌏 ASEAN Opportunity Gateway")
st.caption("Submit an idea → check readiness against fixed criteria → find ASEAN programmes "
           "you qualify for → track applications. We assess evidence; we never predict success.")

submit_tab, match_tab, track_tab = st.tabs(["1. Submit & assess", "2. Programmes", "3. Tracker"])

with submit_tab:
    ss.setdefault("idea_text", "")
    if st.button("Load sample submission"):
        ss.idea_text = SAMPLE.read_text()
    text = st.text_area("Describe your startup idea", height=260, key="idea_text",
                        placeholder="Problem, customers, solution, traction, team, business model, next milestone…")
    slides = st.file_uploader("Pitch deck pages (optional, images)", type=["png", "jpg", "jpeg"],
                              accept_multiple_files=True)

    if st.button("Assess readiness", type="primary", disabled=not text.strip()):
        with st.spinner(f"Gemma ({gemma.model_name()}) is reading your submission…"):
            try:
                data = gemma.extract(text, [(f.getvalue(), f.type) for f in slides or []])
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                st.stop()
        results = assess(data.get("evidence", {}), text)
        ss.history.append({"text": text, "data": data, "results": results,
                           "when": date.today().isoformat()})

    if ss.history:
        run = ss.history[-1]
        data, results = run["data"], run["results"]

        if len(ss.history) > 1:
            gained, lost = changes(ss.history[-2]["results"], results)
            if gained or lost:
                st.info("**Since your last version:** "
                        + "; ".join([f"now evidenced: {g['question']}" for g in gained]
                                    + [f"no longer evidenced: {l['question']}" for l in lost]))

        st.subheader("What Gemma extracted")
        s = data.get("summary", {})
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Problem**\n\n{s.get('problem') or '_not stated_'}")
        c2.markdown(f"**Solution**\n\n{s.get('solution') or '_not stated_'}")
        c3.markdown(f"**Target market**\n\n{s.get('target_market') or '_not stated_'}")

        st.subheader("Readiness (rules, not AI judgment)")
        cols = st.columns(3)
        for col, (area, v) in zip(cols, area_summary(results).items()):
            col.metric(area, f"{LEVEL_ICON[v['level']]} {v['level']}", f"{v['met']} of {v['total']} criteria",
                       delta_color="off")

        for area in AREAS:
            with st.expander(area, expanded=True):
                for r in [r for r in results if r["area"] == area]:
                    icon = "✅" if r["status"] == EVIDENCED else "⚠️"
                    line = f"{icon} **{r['question']}** — {r['status']}"
                    if r["quote"]:
                        line += f"\n\n> “{r['quote']}” _({r['source']})_"
                    st.markdown(line)

        g = gaps(results)
        if g:
            st.subheader("Gaps to close")
            for r in g:
                st.markdown(f"- {r['question']}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Strengths** _(AI observation, not scored)_")
            for x in data.get("strengths", []):
                st.markdown(f"- {x}")
        with c2:
            st.markdown("**Unproven assumptions** _(AI observation, not scored)_")
            for x in data.get("assumptions", []):
                st.markdown(f"- {x}")

        st.caption("To improve: edit your description with new evidence and assess again. "
                   "Changes since the last version are shown at the top.")

with match_tab:
    if not ss.history:
        st.info("Assess an idea first.")
    else:
        run = ss.history[-1]
        profile = dict(run["data"].get("profile", {}))
        st.markdown("**Startup profile** (extracted by Gemma, correct anything wrong):")
        c = st.columns(5)
        profile["country"] = c[0].text_input("Country", profile.get("country") or "") or None
        profile["stage"] = c[1].selectbox("Stage", [None, "idea", "prototype", "early revenue", "growth"],
                                          index=[None, "idea", "prototype", "early revenue", "growth"]
                                          .index(profile.get("stage")) if profile.get("stage") in
                                          ["idea", "prototype", "early revenue", "growth"] else 0)
        profile["sector"] = c[2].text_input("Sector", profile.get("sector") or "").lower() or None
        inc_opts = {"Unknown": None, "Yes": True, "No": False}
        inc_label = {None: "Unknown", True: "Yes", False: "No"}[profile.get("incorporated")]
        profile["incorporated"] = inc_opts[c[3].selectbox("Registered company", list(inc_opts),
                                                          index=list(inc_opts).index(inc_label))]
        size = c[4].number_input("Team size (0 = unknown)", 0, 100, profile.get("team_size") or 0)
        profile["team_size"] = size or None

        for m in match_all(profile, load_programmes(), run["results"]):
            p = m["programme"]
            with st.container(border=True):
                st.markdown(f"### {VERDICT_ICON[m['verdict']]} {p['name']} — {m['verdict']}")
                st.caption(f"{p.get('type', '')} · {', '.join(p.get('countries', []))} · "
                           f"Source: {p.get('source', 'not stated')}")
                st.markdown(p.get("offer", ""))
                for r in m["reasons"]:
                    st.markdown(f"- {r}")
                if m["confirm"]:
                    st.markdown(f"**To settle this, confirm:** {m['confirm']}")
                if m["outstanding"]:
                    st.markdown("**Milestone risk — evidence this programme asks for that you haven't shown:**")
                    for o in m["outstanding"]:
                        st.markdown(f"- {o}")
                if p.get("deadline"):
                    st.markdown(f"Deadline: {p['deadline']}")
                tracked = any(t["id"] == p["id"] for t in ss.tracker)
                if m["verdict"] != NOT_ELIGIBLE and not tracked:
                    if st.button("Track this programme", key=f"track_{p['id']}"):
                        ss.tracker.append({"id": p["id"], "name": p["name"], "status": "Interested",
                                           "note": "", "updated": date.today().isoformat()})
                        st.rerun()

with track_tab:
    if not ss.tracker:
        st.info("Track programmes from the Programmes tab.")
    for i, t in enumerate(ss.tracker):
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 4])
            c1.markdown(f"**{t['name']}**\n\nUpdated {t['updated']}")
            new = c2.selectbox("Status", TRACK_STATES, TRACK_STATES.index(t["status"]), key=f"st_{i}")
            note = c3.text_input("Next step / note", t["note"], key=f"note_{i}")
            if new != t["status"] or note != t["note"]:
                t.update(status=new, note=note, updated=date.today().isoformat())
    if ss.tracker:
        st.download_button("Export tracker (JSON)", json.dumps(ss.tracker, indent=2),
                           "tracker.json", "application/json")
