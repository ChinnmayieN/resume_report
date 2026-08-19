import os
import json
import time
import requests
import streamlit as st
from pypdf import PdfReader
from dotenv import load_dotenv
from scrapers.direct_scraper import fetch_jobs_direct as fetch_jobs

# 1. Load Environment & Streamlit Secrets
load_dotenv()

GROQ_API_KEY = None
if "GROQ_API_KEY" in st.secrets:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
if not GROQ_API_KEY:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 2. Helper function: Make direct REST calls to Groq API with dynamic model discovery
# 2. Helper function: Call standard Groq chat completion models directly
# 2. Helper function: Direct REST call to active Groq chat models
def call_groq_api(prompt: str) -> dict:
    if not GROQ_API_KEY:
        st.error("❌ `GROQ_API_KEY` is missing. Please add it to your Streamlit Cloud Secrets.")
        st.stop()

    clean_key = str(GROQ_API_KEY).strip().strip('"').strip("'")
    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json"
    }

    # Only currently active Groq production models
    active_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

    for model_name in active_models:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=25
            )
            
            if response.status_code == 200:
                data = response.json()
                return json.loads(data["choices"][0]["message"]["content"])
            else:
                # If the first model fails with something other than rate-limit, stop and report immediately
                st.error(f"⚠️ Groq [{model_name}] returned HTTP {response.status_code} using key ({clean_key[:8]}...): {response.text}")
        except Exception as e:
            st.error(f"Connection error with {model_name}: {e}")

    raise RuntimeError("Groq API request failed across active models.")
# 3. Helper function: Extract raw text from PDF
def extract_text_from_pdf(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

# 4. Helper function: Parse resume with Groq
def parse_resume_with_groq(resume_text: str) -> dict:
    prompt = f"""
    Analyze the following resume text and extract the candidate's core profile.
    
    === RESUME TEXT ===
    {resume_text[:4000]}
    
    Return ONLY a valid JSON object in this exact format:
    {{
        "primary_role": "<best target job title, e.g., Software Engineer>",
        "key_skills": ["skill1", "skill2", "skill3"],
        "years_experience": 1,
        "summary": "<1-2 sentence summary>"
    }}
    """
    return call_groq_api(prompt)

# 5. Helper function: Evaluate job matching
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

# --- UI Application Layout ---
st.set_page_config(page_title="AI Job Finder", page_icon="💼", layout="wide")

st.title("💼 AI Resume-Based Job Matcher")
st.write("Upload your resume PDF to instantly discover and evaluate matching job openings.")

uploaded_file = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])

if uploaded_file is not None:
    st.success("Resume uploaded successfully!")
    
    with st.spinner("Analyzing resume using Groq LLM..."):
        resume_text = extract_text_from_pdf(uploaded_file)
        profile = parse_resume_with_groq(resume_text)
    
    st.subheader("📋 Extracted Profile")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Target Role:** {profile.get('primary_role', 'Not detected')}")
        st.write(f"**Experience:** ~{profile.get('years_experience', 0)} years")
    with col2:
        st.write(f"**Key Skills:** {', '.join(profile.get('key_skills', []))}")
        st.write(f"**Summary:** {profile.get('summary', '')}")
        
    st.divider()
    st.subheader("🔍 Find Matching Jobs")
    
    c1, c2, c3 = st.columns([2, 2, 1])
    search_role = c1.text_input("Job Keyword", value=profile.get("primary_role", "Software Engineer"))
    search_location = c2.text_input("Location", value="Bengaluru")
    max_jobs_to_fetch = c3.slider("Max Jobs", 3, 15, 5)
    
    if st.button("🚀 Find & Evaluate Matching Jobs"):
        with st.spinner(f"Scraping live jobs for '{search_role}' in '{search_location}'..."):
            raw_jobs = fetch_jobs(search_query=search_role, location=search_location, max_jobs=max_jobs_to_fetch)
        
        if not raw_jobs:
            st.warning("No jobs found matching your criteria. Try adjusting the search keyword or location.")
        else:
            st.info(f"Retrieved {len(raw_jobs)} live job postings. Evaluating alignment with Groq...")
            
            evaluations = []
            progress_bar = st.progress(0)
            
            for idx, job in enumerate(raw_jobs):
                eval_res = evaluate_job(profile, job)
                evaluations.append(eval_res)
                progress_bar.progress((idx + 1) / len(raw_jobs))
                time.sleep(0.5)
            
            evaluations = sorted(evaluations, key=lambda x: x.get("match_score", 0), reverse=True)
            
            st.subheader("🎯 Evaluation Results")
            for eval_item in evaluations:
                score = eval_item.get("match_score", 0)
                if score >= 80:
                    score_badge = f":green[{score}% Match]"
                elif score >= 60:
                    score_badge = f":orange[{score}% Match]"
                else:
                    score_badge = f":red[{score}% Match]"
                
                with st.expander(f"{eval_item['title']} @ {eval_item['company']} — {score_badge}"):
                    st.write(f"**Recommendation:** {eval_item.get('recommendation', '')}")
                    st.write(f"**Matched Skills:** {', '.join(eval_item.get('matched_skills', []))}")
                    if eval_item.get("missing_skills"):
                        st.write(f"**Missing Skills:** {', '.join(eval_item.get('missing_skills', []))}")
                    
                    if eval_item.get("apply_url"):
                        st.link_button("👉 Apply Now", eval_item["apply_url"])