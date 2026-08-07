import os
import sys
import time
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.apify_scraper import fetch_jobs_from_apify
from evaluator.groq_evaluator import evaluate_job_with_groq
from automator.playwright_applier import apply_to_job
from config import CANDIDATE_PROFILE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_agent_pipeline():
    logger.info("=== Starting Job Application Agent ===")
    
    # 1. Fetch raw jobs into memory
    search_term = CANDIDATE_PROFILE["target_roles"][0]
    raw_jobs = fetch_jobs_from_apify(search_query=search_term, location="Remote", max_jobs=5)

    applied_count = 0
    
    # 2. Iterate through each job listing
    for idx, raw_job in enumerate(raw_jobs, 1):
        logger.info(f"\n--- Processing Job [{idx}/{len(raw_jobs)}] ---")
        
        # Evaluate match using Groq LLM
        eval_result = evaluate_job_with_groq(raw_job)
        
        logger.info(f"Title: {eval_result.get('job_title')} | Company: {eval_result.get('company')}")
        logger.info(f"Score: {eval_result.get('match_score')}% | Should Apply: {eval_result.get('should_apply')}")
        logger.info(f"Reasoning: {eval_result.get('reasoning')}")
        logger.info(f"Apply URL: {eval_result.get('apply_url')}")

        # 3. Apply if match score is high enough
        if eval_result.get("should_apply"):
            success = apply_to_job(eval_result)
            if success:
                applied_count += 1

        # Pause 1 second to respect Groq API free-tier rate limits
        time.sleep(1)

    logger.info(f"\n=== Pipeline Completed! Applied to {applied_count} matching positions. ===")

if __name__ == "__main__":
    run_agent_pipeline()