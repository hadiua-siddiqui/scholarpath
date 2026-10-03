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
    score = 2 + 2 * sum(checks.values())
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
st.title("🎓 ScholarPath")
st.caption("Multi-agent AI that finds scholarships, checks your gaps, and builds your roadmap.")

with st.sidebar:
    st.header("Your profile")
    name = st.text_input("Name")
    cgpa = st.number_input("CGPA (out of 4.0)", 0.0, 4.0, 3.2, 0.01)
    field = st.text_input("Field of study", "Computer Science")
    level = st.selectbox("Target degree", ["Masters", "PhD"])
    countries = st.multiselect("Target countries", sorted({s["country"] for s in SCHOLARSHIPS}),
                               default=["Germany", "UK"])
    ielts = st.number_input("IELTS score (0 if not taken)", 0.0, 9.0, 0.0, 0.5)
    publications = st.number_input("Publications", 0, 20, 0)
    work_months = st.number_input("Work experience (months)", 0, 120, 0)
    projects = st.text_area("Projects / research interests", "")
    sop = st.text_area("Paste your SOP or CV text (optional)", height=150)
    run = st.button("Run agents 🚀", type="primary")

if run:
    profile = dict(name=name, cgpa=cgpa, field=field, level=level, countries=countries, ielts=ielts,
                   publications=publications, work_months=work_months, projects=projects)

    with st.status("Agents working...", expanded=True) as status:
        st.write("🔎 Discovery agent: matching scholarships")
        matches = discovery_agent(profile)
        st.write("✅ Eligibility agent: checking requirements")
        rows = eligibility_agent(profile, matches)
        st.write("🗺️ Roadmap agent: building your plan")
        roadmap = roadmap_agent(profile, rows)
        review = None
        if sop.strip():
            st.write("📝 Reviewer agent: critiquing your text")
            review = reviewer_agent(profile, sop)
        status.update(label="Done", state="complete")

    t1, t2, t3 = st.tabs(["Matches and gaps", "Roadmap", "SOP/CV review"])
    with t1:
        st.dataframe(rows, use_container_width=True)
        for s in matches:
            st.markdown(f"**{s['name']}**: {s['notes']} [Official site]({s['url']})")
        st.info("Deadlines and rules are approximate. Always verify on the official website.")
    with t2:
        st.markdown(roadmap)
        st.download_button("Download roadmap", roadmap, "scholarpath_roadmap.md")
    with t3:
        st.markdown(review or "Paste your SOP or CV in the sidebar to get a review.")
else:
    st.info("Fill in your profile on the left and click **Run agents**.")
