import logging
from apify_client import ApifyClient
from config import APIFY_API_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_jobs_from_apify(search_query: str, location: str = "Remote", max_jobs: int = 5) -> list[dict]:
    """
    Fetches job listings directly as JSON into memory using Apify's LinkedIn Jobs Scraper.
    """
    if not APIFY_API_TOKEN:
        raise ValueError("APIFY_API_TOKEN is missing in .env file")

    client = ApifyClient(APIFY_API_TOKEN)
    
    run_input = {
        "includeKeyword": search_query,
        "locationName": location,
        "datePosted": "3days",  # Fetch recent openings
        "maxJobs": max_jobs,
    }

    logger.info(f"Triggering Apify LinkedIn Scraper for query: '{search_query}'...")
    
    # Run the Apify Actor (e.g., orgupdate/linkedin-jobs-scraper)
    run = client.actor("orgupdate/linkedin-jobs-scraper").call(run_input=run_input)
    
    # Download dataset items directly as a list of Python dicts
    items = client.dataset(run["defaultDatasetId"]).list_items().items
    logger.info(f"Successfully scraped {len(items)} raw jobs from Apify.")
    
    return items