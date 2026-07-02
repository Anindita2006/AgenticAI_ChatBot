"""
Builds data/bvrith_college_info.pdf from the same SECTIONS content used for the
.docx (see generate_kb_doc.py) so there is a single source of truth for the
knowledge-base text. Useful as a fallback for anyone without Word, and as an
alternative ingestion input via PyPDFLoader-style page-aware loaders.

Same pagination rule as the .docx: each of the 8 sections starts on its own page,
so page number == section index, keeping citation metadata consistent regardless
of which file format is ingested.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem

from generate_kb_doc import SECTIONS

OUTPUT_PATH = "bvrith_college_info.pdf"


def build_pdf(output_path: str = OUTPUT_PATH) -> None:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="BVRIT HYDERABAD College of Engineering for Women - Information Document",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=18, spaceAfter=12)
    subtitle_style = ParagraphStyle("SubtitleStyle", parent=styles["Italic"], fontSize=10, spaceAfter=6)
    heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading1"], fontSize=14, spaceBefore=6, spaceAfter=10)
    body_style = ParagraphStyle("BodyStyle", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=8)
    bullet_style = ParagraphStyle("BulletStyle", parent=body_style, spaceAfter=4)

    story = []
    story.append(Paragraph("BVRIT HYDERABAD College of Engineering for Women", title_style))
    story.append(Paragraph("Official Information Document &mdash; Knowledge Base for the College FAQ Chatbot", subtitle_style))
    story.append(Paragraph(
        "Compiled from bvrithyderabad.edu.in (About, Admissions, Fee Details, "
        "Placements, Training &amp; Placement Cell, CSE Department pages). Facts not "
        "found on the official pages are explicitly marked as unavailable rather "
        "than invented.",
        subtitle_style,
    ))
    story.append(PageBreak())

    for i, section in enumerate(SECTIONS):
        story.append(Paragraph(section["heading"], heading_style))
        bullets = []
        for item in section["body"]:
            if isinstance(item, tuple):
                text, _is_bullet = item
                bullets.append(ListItem(Paragraph(text, bullet_style)))
            else:
                if bullets:
                    story.append(ListFlowable(bullets, bulletType="bullet", leftIndent=14))
                    story.append(Spacer(1, 6))
                    bullets = []
                story.append(Paragraph(item, body_style))
        if bullets:
            story.append(ListFlowable(bullets, bulletType="bullet", leftIndent=14))
        if i < len(SECTIONS) - 1:
            story.append(PageBreak())

    doc.build(story)
    print(f"Saved {output_path} ({len(SECTIONS)} sections + 1 title page)")


if __name__ == "__main__":
    build_pdf()
