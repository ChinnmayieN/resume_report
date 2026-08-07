import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Agent Settings
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "false").lower() == "true"
MINIMUM_MATCH_SCORE = 75  # Only apply to jobs scoring >= 75%

# User Candidate Profile
CANDIDATE_PROFILE = {
    "full_name": "Alex Mercer",
    "email": "alex.mercer@example.com",
    "phone": "+1 555-019-2834",
    "linkedin_url": "https://linkedin.com/in/alex-mercer",
    "github_url": "https://github.com/alex-mercer",
    "target_roles": ["Software Engineer", "Full Stack Developer", "Backend Developer"],
    "primary_skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "AWS"],
    "years_experience": 3,
    "desired_salary": "$90,000",
    "work_preference": "Remote",
    "resume_path": "resume.pdf"  # Place your CV PDF in the root directory
}