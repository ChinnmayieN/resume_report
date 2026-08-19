import os
import json
import time
import requests
import streamlit as st
from pypdf import PdfReader
from dotenv import load_dotenv
from scrapers.direct_scraper import fetch_jobs_direct as fetch_jobs

load_dotenv()

# Safely read GROQ_API_KEY from Streamlit Cloud Secrets or local .env
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("❌ `GROQ_API_KEY` is missing. Please add it to your Streamlit Cloud Secrets or .env file.")
    st.stop()

# Helper: Direct API call to bypass Groq SDK / Python 3.14 issues
def call_groq_api(prompt: str) -> dict:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=25)
    
    if response.status_code != 200:
        st.error(f"Groq API Error ({response.status_code}): {response.text}")
        raise RuntimeError(f"Groq API failed: {response.text}")
        
    data = response.json()
    return json.loads(data["choices"][0]["message"]["content"])


st.set_page_config(page_title="AI Job Finder", page_icon="💼", layout="wide")

st.title("💼 AI Resume-Based Job Matcher")
st.write("Upload your resume PDF to instantly discover and evaluate matching job openings.")

# 1. Helper function: Extract raw text from PDF
def extract_text_from_pdf(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

# 2. Helper function: Extract structured profile from resume
def parse_resume_with_groq(resume_text: str) -> dict:
    prompt = f"""
    Analyze the following resume text and extract the candidate's core profile.
    
    === RESUME TEXT ===
    {resume_text[:4000]}
    
    Return ONLY a valid JSON object in this exact format:
    {{
        "primary_role": "<best target job title>",
        "key_skills": ["skill1", "skill2", "skill3"],
        "years_experience": 1,
        "summary": "<1-2 sentence summary>"
    }}
    """
    return call_groq_api(prompt)

# 3. Helper function: Evaluate job match against candidate profile
def evaluate_job(candidate_profile: dict, job: dict) -> dict:
    job_title = job.get("title") or job.get("jobTitle") or "Role"
    company = job.get("companyName") or job.get("company") or "Company"
    description = job.get("description") or job.get("jobDescription") or ""
    apply_url = job.get("applyUrl") or job.get("jobUrl") or job.get("link") or ""

    prompt = f"""
    Evaluate if this candidate matches the job posting.
    
    === CANDIDATE PROFILE ===
    {json.dumps(candidate_profile, indent=2)}
    
    === JOB DETAILS ===
    Title: {job_title}
    Company: {company}
    Description: {description[:2500]}
    
    Return ONLY a valid JSON object in this exact format:
    {{
        "match_score": 80,
        "matched_skills": ["skill1", "skill2"],
        "missing_skills": ["skill1"],
        "recommendation": "<short 1-sentence assessment>"
    }}
    """
    res = call_groq_api(prompt)
    res["title"] = job_title
    res["company"] = company
    res["apply_url"] = apply_url
    return res

# --- UI LAYOUT ---

uploaded_file = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])

if uploaded_file is not None:
    st.success("Resume uploaded successfully!")
    
    with st.spinner("Analyzing resume using Groq LLM..."):
        resume_text = extract_text_from_pdf(uploaded_file)
        profile = parse_resume_with_groq(resume_text)
    
    st.subheader("📋 Extracted Profile")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Target Role:** {profile.get('primary_role')}")
        st.write(f"**Estimated Experience:** {profile.get('years_experience')} years")
    with col2:
        st.write(f"**Key Skills:** {', '.join(profile.get('key_skills', []))}")
    st.info(f"**Summary:** {profile.get('summary')}")

    st.markdown("---")
    
    # Search Options
    st.subheader("🔍 Search Job Postings")
    c1, c2, c3 = st.columns([2, 2, 1])
    search_role = c1.text_input("Job Keyword", value=profile.get("primary_role", "Software Engineer"))
    search_location = c2.text_input("Location", value="Remote")
    max_jobs_to_fetch = c3.slider("Max Jobs", 3, 15, 5)

    if st.button("🚀 Find & Evaluate Matching Jobs"):
        with st.spinner(f"Scraping active jobs for '{search_role}'..."):
            raw_jobs = fetch_jobs(search_query=search_role, location=search_location, max_jobs=max_jobs_to_fetch)
        
        st.success(f"Fetched {len(raw_jobs)} live job postings. Evaluating match scores...")
        
        evaluations = []
        progress_bar = st.progress(0)
        
        for idx, job in enumerate(raw_jobs):
            eval_res = evaluate_job(profile, job)
            evaluations.append(eval_res)
            progress_bar.progress((idx + 1) / len(raw_jobs))
            time.sleep(1)  # Prevent rate limit spikes

        # Sort jobs by match score descending
        evaluations = sorted(evaluations, key=lambda x: x["match_score"], reverse=True)

        st.subheader("🎯 Matching Positions")
        
        for eval_item in evaluations:
            score = eval_item["match_score"]
            
            # Color badge by score
            if score >= 75:
                score_badge = f":green[{score}% Match]"
            elif score >= 50:
                score_badge = f":orange[{score}% Match]"
            else:
                score_badge = f":red[{score}% Match]"

            with st.expander(f"{eval_item['title']} @ {eval_item['company']} — {score_badge}"):
                st.write(f"📍 **Location:** {eval_item.get('location', search_location)}")
                st.write(f"**Recommendation:** {eval_item['recommendation']}")
                st.write(f"**Matched Skills:** {', '.join(eval_item.get('matched_skills', []))}")
                if eval_item.get('missing_skills'):
                    st.write(f"**Missing Skills:** {', '.join(eval_item.get('missing_skills', []))}")
                
                if eval_item.get('apply_url'):
                    st.link_button("👉 Apply Now", eval_item['apply_url'])