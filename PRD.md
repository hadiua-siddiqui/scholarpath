# ScholarPath: Product Requirements Document

## 1. Problem
Pakistani final-year students want international scholarships but face scattered information, unclear eligibility, and no personal plan. Many miss deadlines or apply without the required profile (IELTS, publications, experience).

## 2. Target users
Final-year undergraduates and fresh graduates in Pakistan targeting Masters or PhD scholarships abroad.

## 3. Solution
A multi-agent AI system: a student enters their profile and receives matched scholarships, a gap analysis, a month-by-month roadmap, and an SOP/CV critique.

## 4. Key features
- Discovery agent: matches profile to a curated scholarship dataset
- Eligibility agent: rule-based requirement check with a clear gap table
- Roadmap agent: deadline-driven monthly plan, downloadable
- Reviewer agent: committee-style scoring and rewrite suggestions

## 5. Architecture
Streamlit UI, Python agent functions sharing one profile object, OpenAI-compatible LLM API (Gemini by default), curated JSON dataset. Eligibility is deterministic to avoid hallucinations.

## 6. Success metrics
Time to a personal roadmap (under 1 minute), number of gaps identified per student, reviewer score improvement after revision.

## 7. Limitations and responsible use
Deadlines and rules are approximate and must be verified on official sites. The tool provides guidance, not guarantees.

## 8. Future scope
Live scholarship updates, more countries and programs, Urdu interface, mentor matching, application tracker.
