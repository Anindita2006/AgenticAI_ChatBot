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

# Keyed to the section headings produced by loader.py for data/knowledge_base.pdf
# (15 top-level sections; 14.x/15.x are addendum/appendix subsections pulled from
# assorted pages or, for 15.x, an unverified illustrative document with no real
# page of its own -- both deliberately left unmapped so they fall back to DEFAULT_URL
# rather than pointing to a guessed page).
_SECTION_URLS = {
    "1. About BVRIT Hyderabad": "https://bvrithyderabad.edu.in/about-bvrith/",
    "2. Vision & Mission": "https://bvrithyderabad.edu.in/about-bvrith/",
    "3. Management & Leadership": "https://bvrithyderabad.edu.in/principal/",
    "4. Accreditations & Rankings": "https://bvrithyderabad.edu.in/about-bvrith/",
    "5. Departments – UG Programs": "https://bvrithyderabad.edu.in/computer-science-and-engineering/about-the-department/",
    "6. Admissions": "https://bvrithyderabad.edu.in/admission/admission-process/",
    "7. Placements": "https://bvrithyderabad.edu.in/placement-details/",
    "8. Campus Facilities": "https://bvrithyderabad.edu.in/admission/hostel/",
    "9. Research & Development": "https://bvrithyderabad.edu.in/research/",
    "10. Differentiators & Special Centers": "https://bvrithyderabad.edu.in/about-bvrith/",
    "11. Student Activities & Clubs": "https://bvrithyderabad.edu.in/about-bvrith/",
    "12. Alumni": "https://bvrithyderabad.edu.in/about-bvrith/",
    "13. Contact Details": "https://bvrithyderabad.edu.in/contact-us/",
}

DEFAULT_URL = "https://bvrithyderabad.edu.in/"

GOOGLE_MAPS_URL = (
    "https://www.google.com/maps/search/?api=1&query="
    "BVRIT+HYDERABAD+College+of+Engineering+for+Women+Nizampet+Road+Bachupally+Hyderabad"
)

_LOCATION_KEYWORDS = ["address", "located", "location", "bachupally", "nizampet", "rajiv gandhi nagar colony"]

_DEPARTMENT_SECTION_PREFIXES = ("3. Management", "5. Departments")


def location_mentioned(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in _LOCATION_KEYWORDS)


def resolve_source_url(section: str, text: str) -> str:
    """Best-effort: prefer a department-specific page if the chunk text
    names one, otherwise fall back to the section's default page."""
    lower = text.lower()
    if section.startswith(_DEPARTMENT_SECTION_PREFIXES):
        for hint, url in _DEPARTMENT_HINTS:
            if hint in lower:
                return url
        if "principal" in lower:
            return "https://bvrithyderabad.edu.in/principal/"
    return _SECTION_URLS.get(section, DEFAULT_URL)
