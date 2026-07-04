"""Known people (Principal, department HODs) with a photo and name aliases,
used to decide whose photo to show alongside a chat answer that names them.

Photos are downloaded from bvrithyderabad.edu.in's own principal/faculty pages
into data/images/ (not hotlinked, and not stored in the vectorstore — the
vector DB only holds text chunks + embeddings for retrieval, it's not an asset
store, and Streamlit's st.image needs a real file path to render anyway).
"""

from pathlib import Path

IMAGES_DIR = Path(__file__).resolve().parent.parent / "data" / "images"

PEOPLE = [
    {
        "name": "Dr. K. V. N. Sunitha",
        "role": "Founder Principal",
        "aliases": ["sunitha"],
        "image": IMAGES_DIR / "principal_sunitha.jpg",
    },
    {
        "name": "Dr. Aruna Rao S L",
        "role": "Professor & HoD, CSE",
        "aliases": ["aruna rao"],
        "image": IMAGES_DIR / "hod_cse_aruna_rao.jpg",
    },
    {
        "name": "Dr. Nagesh Deevi",
        "role": "Associate Professor & HoD, ECE",
        "aliases": ["nagesh deevi"],
        "image": IMAGES_DIR / "hod_ece_nagesh_deevi.webp",
    },
    {
        "name": "Dr. M. Sharanya",
        "role": "Professor & HoD, EEE",
        "aliases": ["sharanya"],
        "image": IMAGES_DIR / "hod_eee_sharanya.jpg",
    },
    {
        "name": "Dr. K. Srikar Goud",
        "role": "Assistant Professor & I/C HoD, IT",
        "aliases": ["srikar goud"],
        "image": IMAGES_DIR / "hod_it_srikar_goud.webp",
    },
    {
        "name": "Dr. Venkata Raja Sekhar Reddy N",
        "role": "Professor & HoD, CSE (AI&ML)",
        "aliases": ["raja sekhar reddy", "venkata raja sekhar"],
        "image": IMAGES_DIR / "hod_aiml_raja_sekhar.jpg",
    },
]


def people_mentioned(text: str) -> list[dict]:
    lower = text.lower()
    return [p for p in PEOPLE if any(alias in lower for alias in p["aliases"])]
