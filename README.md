# 🎓 ScholarPath

Multi-agent AI that helps Pakistani students pursue international scholarships.

Built for the HEC-NCEAC & PEC GenAI & Agentic AI Hackathon (Cohort 11).

## Problem
Final-year students want international scholarships but don't know where to start, what they are missing, or when to act.

## How it works
| Agent | Job |
|---|---|
| Discovery | Matches the profile to a curated scholarship dataset |
| Eligibility | Rule-based check of CGPA, IELTS, experience, and publications, with gaps listed |
| Roadmap | LLM builds a month-by-month plan working backward from deadlines |
| Reviewer | LLM scores and rewrites the SOP/CV like a committee would |

**Design choice:** scholarships come from a curated JSON file and eligibility is rule-based, so the system never invents scholarships or requirements. The LLM is used where it adds value: planning and writing feedback.

## Run locally
```bash
pip install -r requirements.txt
export LLM_API_KEY=your_key
# optional: LLM_BASE_URL and LLM_MODEL (defaults to Gemini's OpenAI-compatible endpoint)
streamlit run app.py
```

## Deploy (free)
Push to GitHub, then create an app on Streamlit Community Cloud and add `LLM_API_KEY` under Secrets.

## Limitations
Deadlines and requirements are approximate and must be verified on official sites. ScholarPath gives guidance, not guarantees.

## Future scope
Live scholarship updates, more countries, Urdu support, mentor matching.
