import json
import time
import logging
from groq import Groq
from config import GROQ_API_KEY, CANDIDATE_PROFILE, MINIMUM_MATCH_SCORE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate_job_with_groq(job: dict) -> dict:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is missing in .env file")

    client = Groq(api_key=GROQ_API_KEY)

    # Robust key extraction covering all Apify LinkedIn Scraper variations
    job_title = job.get("title") or job.get("jobTitle") or job.get("position") or "Software Engineer"
    company = job.get("companyName") or job.get("company") or job.get("company_name") or "Company"
    description = job.get("description") or job.get("jobDescription") or job.get("text") or ""
    
    # Extract the correct apply URL
    apply_url = (
        job.get("applyUrl") or 
        job.get("jobUrl") or 
        job.get("link") or 
        job.get("url") or 
        job.get("externalApplyLink") or 
        ""
    )

    prompt = f"""
    You are an AI Job Matching Agent. Compare this job listing with the candidate profile.

    === CANDIDATE PROFILE ===
    {json.dumps(CANDIDATE_PROFILE, indent=2)}

    === JOB DETAILS ===
    Title: {job_title}
    Company: {company}
    Description: {description[:2500]}

    Return ONLY a valid JSON object in this exact format:
    {{
        "match_score": <int 0-100>,
        "should_apply": <boolean true if match_score >= {MINIMUM_MATCH_SCORE}>,
        "matched_skills": [<string>],
        "missing_skills": [<string>],
        "reasoning": "<short explanation>"
    }}
    """

    # Retry loop to handle Groq API Rate Limit (HTTP 429) cleanly
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )

            eval_result = json.loads(response.choices[0].message.content)
            
            # Re-attach target metadata
            eval_result["job_title"] = job_title
            eval_result["company"] = company
            eval_result["apply_url"] = apply_url
            return eval_result

        except Exception as e:
            if "429" in str(e):
                wait_time = (attempt + 1) * 3  # Exponential backoff: wait 3s, 6s, 9s...
                logger.warning(f"Groq Rate Limit reached (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Error during Groq evaluation: {e}")
                break

    return {
        "should_apply": False, 
        "match_score": 0, 
        "reasoning": "Evaluation failed due to rate limit or API error",
        "job_title": job_title,
        "company": company,
        "apply_url": apply_url
    }