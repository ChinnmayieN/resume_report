import os
import requests
import logging

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

def fetch_jobs_from_rapidapi(search_query: str, location: str = "Remote", max_jobs: int = 5) -> list[dict]:
    """
    Fetches job listings directly using RapidAPI free tier.
    """
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY is missing in .env file")

    url = "https://linkedin-data-api.p.rapidapi.com/search-jobs"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com"
    }
    
    params = {
        "keywords": search_query,
        "locationId": "103644278",  # Default US/Remote ID
        "datePosted": "anyTime"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        jobs = data.get("data", [])[:max_jobs]
        
        # Standardize format for Streamlit/Groq
        formatted_jobs = []
        for job in jobs:
            formatted_jobs.append({
                "title": job.get("title") or job.get("jobTitle"),
                "companyName": job.get("company") or job.get("companyName"),
                "description": job.get("description") or job.get("snippet", ""),
                "applyUrl": job.get("url") or job.get("jobUrl") or job.get("link")
            })
            
        return formatted_jobs
        
    except Exception as e:
        logger.error(f"RapidAPI request failed: {e}")
        return []