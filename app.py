import json
import os
from datetime import date

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="ScholarPath", page_icon="🎓", layout="wide")


def cfg(key, default=None):
    if os.getenv(key):
        return os.getenv(key)
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


# Works with Gemini, OpenAI, Groq, etc. through the OpenAI-compatible API.
client = OpenAI(
    api_key=cfg("LLM_API_KEY") or "missing",
    base_url=cfg("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
)
MODEL = cfg("LLM_MODEL", "gemini-2.0-flash")


def llm(system, user):
    """Returns None if the AI is unavailable (limit, wrong model, no key), so the app never crashes."""
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.4,
        )
        return r.choices[0].message.content
    except Exception:
        return None


NOTE = "_AI model unavailable right now, so this is the built-in rule-based version._\n\n"


def fallback_roadmap(p, rows):
    gaps = " ".join(r["Gaps"] for r in rows)
    steps = [("Month 1", "Shortlist 3 to 4 scholarships from the table above and open each official site to confirm deadlines and requirements.")]
    if "IELTS" in gaps:
        steps.append(("Months 1 to 3", "Prepare for IELTS (target 6.5+), book your exam date early, and keep the score report ready."))
    if "publication" in gaps:
        steps.append(("Months 1 to 6", "Pick a supervisor or lab in your field, choose a small research problem from your projects, and aim to submit a paper or conference abstract."))
    if "work experience" in gaps:
        steps.append(("Months 2 to 8", "Take an internship, freelance project, or volunteer role and document measurable results."))
    if "CGPA" in gaps:
        steps.append(("Ongoing", "Finish the final semesters strongly and prefer scholarships with lower CGPA cutoffs."))
    steps += [
        ("Month 2", "Write the first SOP draft: your story, research interests, why this country and program, and your future goals."),
        ("Month 3", "Request 2 to 3 recommendation letters. Give recommenders your CV and a short summary of your work."),
        ("Month 4", "Get your SOP and CV reviewed by a professor or senior, then revise."),
        ("Before each deadline", "Collect transcripts, passport, test scores, and certificates at least 3 weeks before submission."),
    ]
    out = NOTE + "### Your roadmap\n"
    for when, what in steps:
        out += f"- **{when}:** {what}\n"
    out += "\nAlways verify deadlines on the official websites."
    return out


def fallback_review(text):
    words = len(text.split())
    checks = {
        "Has specific numbers or results": any(c.isdigit() for c in text),
        "Mentions research or projects": any(k in text.lower() for k in ["research", "project", "thesis"]),
        "States clear goals": any(k in text.lower() for k in ["goal", "aim", "plan to", "future"]),
        "Explains why this program or country": any(k in text.lower() for k in ["why", "because", "university", "program"]),
        "Good length (300+ words)": words >= 300,
    }
    score = 2 * sum(checks.values())
    out = NOTE + f"### SOP/CV check\n**Score: {min(score, 10)}/10** ({words} words)\n\n"
    for k, v in checks.items():
        out += f"- {'✅' if v else '❌'} {k}\n"
    out += "\nTip: replace general lines like 'I am passionate about AI' with a specific project and its result."
    return out


with open(os.path.join(os.path.dirname(__file__), "scholarships.json"), encoding="utf-8") as f:
    SCHOLARSHIPS = json.load(f)


# ---------- Agent 1: Discovery ----------
def discovery_agent(p):
    matches = []
    for s in SCHOLARSHIPS:
        if p["level"] not in s["levels"]:
            continue
        score = 2 if s["country"] in p["countries"] else 0
        score += 1 if p["cgpa"] >= s["min_cgpa"] else 0
        matches.append((score, s))
    matches.sort(key=lambda x: -x[0])
    return [s for _, s in matches[:6]]


# ---------- Agent 2: Eligibility (rule engine, so results are never hallucinated) ----------
def eligibility_agent(p, schol):
    rows = []
    for s in schol:
        gaps = []
        if p["cgpa"] < s["min_cgpa"]:
            gaps.append(f"CGPA below ~{s['min_cgpa']}")
        if s["min_ielts"] and p["ielts"] < s["min_ielts"]:
            gaps.append("No IELTS yet" if p["ielts"] == 0 else f"IELTS below {s['min_ielts']}")
        if p["work_months"] < s["min_work_months"]:
            gaps.append(f"Needs {s['min_work_months']} months of work experience")
        if s["publication_recommended"] and p["publications"] == 0:
            gaps.append("No publication yet (strongly recommended)")
        status = "✅ Eligible" if not gaps else ("⚠️ Close" if len(gaps) <= 2 else "❌ Big gaps")
        rows.append({"Scholarship": s["name"], "Country": s["country"], "Deadline": s["typical_deadline"],
                     "Status": status, "Gaps": "; ".join(gaps) or "None"})
    return rows


# ---------- Agent 3: Roadmap ----------
def roadmap_agent(p, rows):
    system = ("You are a scholarship mentor for Pakistani students. Build a realistic month-by-month plan. "
              "Work backward from deadlines, close every listed gap, and be specific and actionable. "
              "Deadlines are approximate, so remind the student to verify on official sites. Use markdown.")
    user = f"Today is {date.today():%d %B %Y}.\nStudent profile: {json.dumps(p)}\nEligibility table: {json.dumps(rows)}"
    return llm(system, user) or fallback_roadmap(p, rows)


# ---------- Agent 4: Reviewer ----------
def reviewer_agent(p, text):
    system = ("You are a strict scholarship committee reviewer. Score the text out of 10 on specificity, "
              "research or career fit, clarity of goals, and impact. List the 3 biggest weaknesses, "
              "then rewrite the weakest paragraph to show improvement. Do not invent facts about the student.")
    return llm(system, f"Student profile: {json.dumps(p)}\n\nSOP/CV text:\n{text}") or fallback_review(text)


# ---------- UI ----------
st.markdown("""<style>
.hero{background:linear-gradient(135deg,#4f46e5,#7c3aed 55%,#db2777);padding:28px 32px;border-radius:18px;color:#fff;margin-bottom:18px}
.hero h1{margin:0;font-size:2.4rem;color:#fff}
.hero p{margin:6px 0 14px;opacity:.92;font-size:1.05rem;color:#fff}
.chip{display:inline-block;background:rgba(255,255,255,.18);padding:5px 12px;border-radius:999px;margin:3px 6px 3px 0;font-size:.85rem;font-weight:600;color:#fff}
.card{background:rgba(128,128,128,.10);border:1px solid rgba(128,128,128,.28);border-radius:14px;padding:16px 18px;margin-bottom:14px}
.card h4{margin:0 0 6px 0}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.78rem;font-weight:700;color:#fff}
.ok{background:#059669}.mid{background:#d97706}.bad{background:#dc2626}
.muted{opacity:.75;font-size:.9rem}
</style>""", unsafe_allow_html=True)

st.markdown(
    '<div class="hero"><h1>🎓 ScholarPath</h1>'
    "<p>Multi-agent AI that finds scholarships, checks your gaps, and builds your roadmap.</p>"
    '<span class="chip">1 Discovery</span><span class="chip">2 Eligibility</span>'
    '<span class="chip">3 Roadmap</span><span class="chip">4 Reviewer</span></div>',
    unsafe_allow_html=True,
)

DEFAULTS = dict(name="", cgpa=3.2, field="Computer Science", level="Masters", countries=["Germany", "UK"],
                ielts=0.0, publications=0, work_months=0, projects="", sop="")
DEMO = dict(name="Hadiya", cgpa=3.4, field="Computer Science", level="Masters", countries=["Germany", "UK"],
            ielts=0.0, publications=0, work_months=0, projects="AI-based secure SDN project")
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def load_demo():
    st.session_state.update(DEMO)


with st.sidebar:
    st.header("Your profile")
    st.button("✨ Load demo profile", on_click=load_demo, key="demo")
    st.text_input("Name", key="name")
    st.number_input("CGPA (out of 4.0)", min_value=0.0, max_value=4.0, step=0.01, key="cgpa")
    st.text_input("Field of study", key="field")
    st.selectbox("Target degree", ["Masters", "PhD"], key="level")
    st.multiselect("Target countries", sorted({s["country"] for s in SCHOLARSHIPS}), key="countries")
    st.number_input("IELTS score (0 if not taken)", min_value=0.0, max_value=9.0, step=0.5, key="ielts")
    st.number_input("Publications", min_value=0, max_value=20, key="publications")
    st.number_input("Work experience (months)", min_value=0, max_value=120, key="work_months")
    st.text_area("Projects / research interests", key="projects")
    st.text_area("Paste your SOP or CV text (optional)", height=150, key="sop")
    run = st.button("Run agents 🚀", type="primary", key="run")

if run:
    ss = st.session_state
    profile = dict(name=ss.name, cgpa=ss.cgpa, field=ss.field, level=ss.level, countries=ss.countries,
                   ielts=ss.ielts, publications=ss.publications, work_months=ss.work_months, projects=ss.projects)

    with st.status("Agents working...", expanded=True) as status:
        st.write("🔎 Discovery agent: matching scholarships")
        matches = discovery_agent(profile)
        st.write("✅ Eligibility agent: checking requirements")
        rows = eligibility_agent(profile, matches)
        st.write("🗺️ Roadmap agent: building your plan")
        roadmap = roadmap_agent(profile, rows)
        review = None
        if ss.sop.strip():
            st.write("📝 Reviewer agent: critiquing your text")
            review = reviewer_agent(profile, ss.sop)
        status.update(label="All agents finished", state="complete")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scholarships matched", len(rows))
    m2.metric("Eligible now", sum(r["Status"].startswith("✅") for r in rows))
    m3.metric("Close (1-2 gaps)", sum(r["Status"].startswith("⚠️") for r in rows))
    m4.metric("Big gaps", sum(r["Status"].startswith("❌") for r in rows))

    t1, t2, t3 = st.tabs(["🎯 Matches and gaps", "🗺️ Roadmap", "📝 SOP/CV review"])
    with t1:
        cols = st.columns(2)
        for i, (s, r) in enumerate(zip(matches, rows)):
            css = "ok" if r["Status"].startswith("✅") else ("mid" if r["Status"].startswith("⚠️") else "bad")
            label = r["Status"].split(" ", 1)[1]
            cols[i % 2].markdown(
                f'<div class="card"><h4>{s["name"]}</h4>'
                f'<span class="badge {css}">{label}</span> <span class="muted">{s["country"]} · {s["typical_deadline"]}</span>'
                f'<p style="margin:10px 0 4px"><b>Gaps:</b> {r["Gaps"]}</p>'
                f'<p class="muted" style="margin:0 0 6px">{s["notes"]}</p>'
                f'<a href="{s["url"]}" target="_blank">Official site ↗</a></div>',
                unsafe_allow_html=True,
            )
        st.info("Deadlines and rules are approximate. Always verify on the official website.")
    with t2:
        with st.container(border=True):
            st.markdown(roadmap)
        st.download_button("⬇️ Download roadmap", roadmap, "scholarpath_roadmap.md")
    with t3:
        with st.container(border=True):
            st.markdown(review or "Paste your SOP or CV in the sidebar to get a review.")
else:
    st.subheader("How it works")
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="card"><h4>1. Enter your profile</h4><p class="muted">CGPA, field, IELTS, projects and target countries. Or click <b>Load demo profile</b>.</p></div>', unsafe_allow_html=True)
    c2.markdown('<div class="card"><h4>2. Run the agents</h4><p class="muted">Discovery, Eligibility, Roadmap and Reviewer agents work one after another.</p></div>', unsafe_allow_html=True)
    c3.markdown('<div class="card"><h4>3. Get your plan</h4><p class="muted">Matches, a gap table, a month-by-month roadmap and SOP feedback.</p></div>', unsafe_allow_html=True)
