import os
import time
import logging
from playwright.sync_api import sync_playwright
from config import CANDIDATE_PROFILE, HEADLESS_BROWSER

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_to_job(job_eval: dict) -> bool:
    apply_url = job_eval.get("apply_url")
    if not apply_url:
        logger.warning(f"No apply URL found for {job_eval['job_title']} @ {job_eval['company']}")
        return False

    logger.info(f"Opening browser for: {job_eval['job_title']} @ {job_eval['company']}...")

    with sync_playwright() as p:
        # Launch system Chrome to bypass Windows policy restrictions
        browser = p.chromium.launch(channel="chrome", headless=HEADLESS_BROWSER)
        page = browser.new_page()

        try:
            page.goto(apply_url, timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            # Standard inputs autofill attempt
            inputs_map = {
                'input[name*="name"], input[id*="name"]': CANDIDATE_PROFILE["full_name"],
                'input[type="email"], input[name*="email"]': CANDIDATE_PROFILE["email"],
                'input[type="tel"], input[name*="phone"]': CANDIDATE_PROFILE["phone"],
                'input[name*="linkedin"]': CANDIDATE_PROFILE["linkedin_url"],
                'input[name*="github"]': CANDIDATE_PROFILE["github_url"],
            }

            for selector, value in inputs_map.items():
                try:
                    if page.locator(selector).first.is_visible(timeout=1000):
                        page.locator(selector).first.fill(value)
                except Exception:
                    continue  # Field not present, skip

            # Upload resume if file field is available
            resume_file = CANDIDATE_PROFILE["resume_path"]
            if os.path.exists(resume_file):
                file_input = page.locator('input[type="file"]')
                if file_input.count() > 0:
                    file_input.first.set_input_files(os.path.abspath(resume_file))
                    logger.info("Uploaded resume successfully.")

            logger.info(f"Form filled for {job_eval['job_title']}. Reviewing...")
            
            if not HEADLESS_BROWSER:
                time.sleep(5)

            browser.close()
            return True

        except Exception as e:
            logger.error(f"Failed to auto-apply to {apply_url}: {e}")
            browser.close()
            return False