"""Campus facility photos, matched by keyword the same way people.py matches
named faculty — shown alongside a chat answer that covers that facility.

Photos are downloaded from bvrithyderabad.edu.in into data/images/. Only
facilities with a real available photo are listed here: the library and
hostel pages load their photos through a JS gallery widget that isn't present
in the static HTML, so no image could be sourced for those without a headless
browser — they're deliberately left out rather than showing a mislabeled or
stock substitute.
"""

from pathlib import Path

IMAGES_DIR = Path(__file__).resolve().parent.parent / "data" / "images"

FACILITIES = [
    {
        "name": "Sports facilities",
        "aliases": ["sport", "gymnasium", "gym area", "badminton", "basketball", "volleyball", "kabaddi", "kho-kho", "running track"],
        "image": IMAGES_DIR / "facility_sports.jpg",
    },
    {
        "name": "Campus",
        "aliases": ["campus", "wifi", "transport", "buses"],
        "image": IMAGES_DIR / "facility_campus.webp",
    },
]


def facilities_mentioned(text: str) -> list[dict]:
    lower = text.lower()
    return [f for f in FACILITIES if any(alias in lower for alias in f["aliases"])]
