"""Q&A tools for the supervisor agent.

These tools provide information about Matcha AI and the job matching process.
"""

import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Knowledge base for service information
SERVICE_INFO = {
    "about": """Matcha AI is a job matching service that helps connect job seekers with relevant opportunities.
We use AI to understand your skills, experience, and preferences to find the best job matches for you.
Our goal is to make job searching easier and more personalized.""",

    "process": """Here's how the Matcha AI job matching process works:
1. Profile Creation: Share your CV or tell us about your experience, skills, and preferences
2. Profile Review: Our AI extracts and organizes your information
3. Job Matching: We match your profile against available opportunities
4. Results: You receive personalized job recommendations with match scores

The whole process typically takes just a few minutes.""",

    "privacy": """Your privacy is important to us:
- Your data is encrypted and stored securely
- We only share your profile with employers when you apply for jobs
- You can request deletion of your data at any time
- We don't sell your personal information to third parties""",

    "profile": """Your profile includes:
- Personal info (name, email, phone, location)
- Work experience (companies, roles, responsibilities)
- Education (degrees, institutions)
- Skills (technical and soft skills)
- Job preferences (role type, location, salary expectations)

A more complete profile leads to better job matches!""",

    "cv_upload": """You can upload your CV/resume to quickly fill in your profile:
- Supported formats: PDF, DOCX
- Our AI will extract relevant information automatically
- You can review and update any extracted data
- Missing information can be provided through conversation""",

    "help": """I can help you with:
- Creating and updating your profile
- Uploading and parsing your CV
- Understanding how Matcha AI works
- Answering questions about the process

Just ask me what you'd like to know!""",
}


@tool
def get_service_info(topic: str) -> str:
    """
    Get information about Matcha AI and the job matching service.

    Args:
        topic: The topic to get information about. Options include:
               - 'about': General info about Matcha AI
               - 'process': How job matching works
               - 'privacy': Data privacy information
               - 'profile': What profile information is collected
               - 'cv_upload': How CV upload works
               - 'help': What assistance is available

    Returns:
        Information about the requested topic.

    Use this when users ask questions about the service, process, or how things work.
    """
    topic_lower = topic.lower().strip()

    # Try exact match first
    if topic_lower in SERVICE_INFO:
        return SERVICE_INFO[topic_lower]

    # Try partial matches
    for key, value in SERVICE_INFO.items():
        if topic_lower in key or key in topic_lower:
            return value

    # Keywords mapping
    keyword_mapping = {
        "what": "about",
        "how": "process",
        "data": "privacy",
        "secure": "privacy",
        "info": "profile",
        "cv": "cv_upload",
        "resume": "cv_upload",
        "upload": "cv_upload",
        "document": "cv_upload",
    }

    for keyword, mapped_topic in keyword_mapping.items():
        if keyword in topic_lower:
            return SERVICE_INFO[mapped_topic]

    # Default to help
    logger.info(f"Unknown topic '{topic}', returning help info")
    return SERVICE_INFO["help"]
