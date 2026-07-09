"""Loads the .pdf knowledge base into section/page-tagged text blocks.

The document (data/knowledge_base.pdf) is a real export scraped from the
college's live website: 15 numbered top-level sections (Title Case headings,
e.g. "5. Departments – UG Programs"), two of which (14, 15) further break
down into numbered subsections (e.g. "14.9 EAMCET / EAPCET Rank Cut-Offs").
The body text also contains unrelated numbered lists (patent titles, ranked
items) that restart at 1 -- a heading is therefore only accepted when its
number continues the expected top-level sequence *and* its title matches the
known section title, not from the numbering pattern alone.
"""

import re
from dataclasses import dataclass

from pypdf import PdfReader

TOP_HEADING_RE = re.compile(r"^(\d{1,2})\.\s+(.+)$")
SUB_HEADING_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\s+(.+)$")

# Canonical top-level titles, normalized (lowercase, alphanumeric only) so
# comparisons are immune to dash/encoding variants pypdf produces for the
# same glyph across extractions. Section 15's title wraps onto a second PDF
# line ("... Illustrative Training" / "Document (Unverified)"), so its entry
# is deliberately just the first line's text -- matched as a prefix below.
_CANONICAL_TITLES = {
    1: "aboutbvrithyderabad",
    2: "visionmission",
    3: "managementleadership",
    4: "accreditationsrankings",
    5: "departmentsugprograms",
    6: "admissions",
    7: "placements",
    8: "campusfacilities",
    9: "researchdevelopment",
    10: "differentiatorsspecialcenters",
    11: "studentactivitiesclubs",
    12: "alumni",
    13: "contactdetails",
    14: "addendumgapfillcontentmergedfromlivewebsite",
    15: "appendixsupplementarycontentfromillustrativetraining",
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _is_expected_top_heading(number: int, title: str, expected_next: int) -> bool:
    if number != expected_next:
        return False
    canonical = _CANONICAL_TITLES.get(number)
    if not canonical:
        return False
    candidate = _normalize(title)
    if not candidate:
        return False
    return candidate == canonical or candidate.startswith(canonical) or canonical.startswith(candidate)


@dataclass
class SectionBlock:
    section: str
    page: int
    text: str


def load_pdf_sections(path) -> list[SectionBlock]:
    reader = PdfReader(str(path))

    sections: list[SectionBlock] = []
    current_heading = None
    current_heading_page = None
    current_top_number = 0
    current_lines: list[str] = []

    def flush():
        if current_heading is not None:
            sections.append(SectionBlock(
                section=current_heading,
                page=current_heading_page,
                text="\n".join(current_lines).strip(),
            ))

    for page_index, page in enumerate(reader.pages, start=1):
        for raw_line in page.extract_text().splitlines():
            line = raw_line.strip()
            if not line:
                continue

            sub_match = SUB_HEADING_RE.match(line)
            if sub_match and int(sub_match.group(1)) == current_top_number:
                flush()
                current_heading = f"{sub_match.group(1)}.{sub_match.group(2)} {sub_match.group(3).strip()}"
                current_heading_page = page_index
                current_lines = []
                continue

            top_match = TOP_HEADING_RE.match(line)
            if top_match and _is_expected_top_heading(
                int(top_match.group(1)), top_match.group(2), current_top_number + 1
            ):
                flush()
                current_top_number = int(top_match.group(1))
                current_heading = f"{top_match.group(1)}. {top_match.group(2).strip()}"
                current_heading_page = page_index
                current_lines = []
                continue

            if current_heading is None:
                continue  # title page / table of contents before section 1
            current_lines.append(line)

    flush()
    return sections


if __name__ == "__main__":
    import sys
    from config import KB_PDF_PATH

    path = sys.argv[1] if len(sys.argv) > 1 else KB_PDF_PATH
    blocks = load_pdf_sections(path)
    for b in blocks:
        print(f"[page {b.page}] {b.section} ({len(b.text)} chars)")
