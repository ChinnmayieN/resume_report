import requests
import urllib.parse
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def fetch_jobs_direct(search_query: str, location: str = "Bengaluru", max_jobs: int = 5) -> list[dict]:
    """
    Scrapes LinkedIn's public guest job endpoint directly with strict URL encoding for location handling.
    """
    # Clean and format location string for India
    formatted_location = location.strip()
    if formatted_location.lower() in ["bangalore", "banglore"]:
        formatted_location = "Bengaluru, Karnataka, India"
    elif formatted_location.lower() == "mumbai":
        formatted_location = "Mumbai, Maharashtra, India"
    elif "india" not in formatted_location.lower() and formatted_location.lower() != "remote":
        formatted_location = f"{formatted_location}, India"

    # Safely URL-encode parameters
    encoded_keywords = urllib.parse.quote(search_query)
    encoded_location = urllib.parse.quote(formatted_location)
    
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_keywords}&location={encoded_location}&start=0"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        job_cards = soup.find_all("li")
        jobs = []
        
        for card in job_cards[:max_jobs]:
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            location_tag = card.find("span", class_="job-search-card__location")
            link_tag = card.find("a", class_="base-card__full-link")
            
            if title_tag and company_tag and link_tag:
                job_loc = location_tag.text.strip() if location_tag else formatted_location
                jobs.append({
                    "title": title_tag.text.strip(),
                    "companyName": company_tag.text.strip(),
                    "location": job_loc,
                    "description": f"{title_tag.text.strip()} position at {company_tag.text.strip()} in {job_loc}.",
                    "applyUrl": link_tag["href"].split("?")[0]
                })
                
        return jobs
    except Exception as e:
        logger.error(f"Direct LinkedIn scraping failed: {e}")
        return []