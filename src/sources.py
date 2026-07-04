"""Maps a retrieved chunk's section (+ text, for department disambiguation)
back to the actual bvrithyderabad.edu.in page it was transcribed from, so
citations in the chat UI can link to the real source instead of just naming
a section and page number.
"""

_DEPARTMENT_HINTS = [
    ("cse ai&ml", "https://bvrithyderabad.edu.in/cse-artificial-intelligence-and-machine-learning/about-the-department/"),
    ("cse (ai&ml)", "https://bvrithyderabad.edu.in/cse-artificial-intelligence-and-machine-learning/about-the-department/"),
    ("cse-ai", "https://bvrithyderabad.edu.in/cse-artificial-intelligence-and-machine-learning/about-the-department/"),
    ("csm", "https://bvrithyderabad.edu.in/cse-artificial-intelligence-and-machine-learning/about-the-department/"),
    ("artificial intelligence and machine learning", "https://bvrithyderabad.edu.in/cse-artificial-intelligence-and-machine-learning/about-the-department/"),
    ("information technology", "https://bvrithyderabad.edu.in/information-technology/faculty/"),
    ("electronics and communication", "https://bvrithyderabad.edu.in/electronics-and-communication-engineering/about-the-department/"),
    ("electrical and electronics", "https://bvrithyderabad.edu.in/electrical-and-electronics-engineering/about-the-department/"),
    ("computer science and engineering", "https://bvrithyderabad.edu.in/computer-science-and-engineering/about-the-department/"),
]

_SECTION_URLS = {
    "1. About BVRIT Hyderabad": "https://bvrithyderabad.edu.in/about-bvrith/",
    "2. Departments": "https://bvrithyderabad.edu.in/computer-science-and-engineering/about-the-department/",
    "3. Admissions": "https://bvrithyderabad.edu.in/admission/admission-process/",
    "4. Fee Structure": "https://bvrithyderabad.edu.in/admission/fee-details/",
    "5. Placements": "https://bvrithyderabad.edu.in/placement-details/",
    "6. Campus & Facilities": "https://bvrithyderabad.edu.in/admission/hostel/",
    "7. Faculty": "https://bvrithyderabad.edu.in/principal/",
    "8. Contact": "https://bvrithyderabad.edu.in/contact-us/",
}

DEFAULT_URL = "https://bvrithyderabad.edu.in/"


def resolve_source_url(section: str, text: str) -> str:
    """Best-effort: prefer a department-specific page if the chunk text
    names one, otherwise fall back to the section's default page."""
    lower = text.lower()
    if section in ("2. Departments", "7. Faculty"):
        for hint, url in _DEPARTMENT_HINTS:
            if hint in lower:
                return url
        if section == "7. Faculty" and "principal" in lower:
            return "https://bvrithyderabad.edu.in/principal/"
    return _SECTION_URLS.get(section, DEFAULT_URL)
