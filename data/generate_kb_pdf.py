"""
Builds data/bvrit_college_info.pdf, the grounding document for the RAG chatbot.

Content (Sections 1-10) is transcribed directly from bvrit_college_info.pdf, the
course's official reference grounding document for this exercise, so that facts
the chatbot is expected to handle via tool calls -- e.g. "has the counselling
deadline passed?" (date_checker) or "what's a 25% scholarship on this fee?"
(percentage_checker) -- actually exist in the knowledge base instead of being
refused as not-covered.

Unlike the old two-stage docx->pdf pipeline (generate_kb_doc.py + this file),
this script builds the PDF directly with reportlab: there is no intermediate
.docx, and src/loader.py reads this PDF directly at ingest time.

Each of the 10 sections starts on its own page (explicit page break) so the
page number is deterministic and can be used as citation metadata during
ingestion, without needing heuristic page-detection.
"""

import html
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak

OUTPUT_PATH = Path(__file__).resolve().parent / "bvrit_college_info.pdf"

SECTIONS = [
    {
        "heading": "1. ABOUT BVRIT",
        "body": [
            ("B V Raju Institute of Technology (BVRIT) Hyderabad College of Engineering for "
             "Women is an autonomous institution affiliated to Jawaharlal Nehru Technological "
             "University, Hyderabad (JNTUH). The college is located in Narsapur, Medak "
             "District, Telangana, on a 125-acre campus approximately 50 km from Hyderabad "
             "city centre."),
            ("BVRIT was established in 2009 by the Vishnu Educational Society, inspired by "
             "the vision of Sri B V Raju. The college exclusively admits women students and "
             "has grown to over 3,500 students across seven B.Tech programmes."),
            ("Vision: To be a premier institution empowering women through quality technical "
             "education, research, and innovation."),
            ("Mission: To provide industry-relevant engineering education with a focus on "
             "holistic development, ethical leadership, and social responsibility."),
            ("Accreditations & Rankings:"),
            ("- NAAC Accredited with 'A' Grade", True),
            ("- NBA Accredited: CSE, ECE, EEE, Mechanical, and IT programmes", True),
            ("- Approved by AICTE, New Delhi", True),
            ("- Autonomous status granted by UGC", True),
            ("- NIRF 2024 Rank Band: 201-300 (Engineering category)", True),
        ],
    },
    {
        "heading": "2. DEPARTMENTS & PROGRAMMES",
        "body": [
            ("BVRIT offers seven B.Tech programmes across seven departments: Computer Science & "
             "Engineering (CSE), CSE (AI & Machine Learning), CSE (Data Science), Electronics & "
             "Communication Engineering (ECE), Electrical & Electronics Engineering (EEE), "
             "Mechanical Engineering, and Information Technology (IT). Each department maintains "
             "dedicated laboratories, a department library, and active industry partnerships."),
            ("2.1 Computer Science & Engineering (CSE): established 2009, intake 240 students. "
             "The largest department at BVRIT with 45 "
             "faculty members, including 8 with PhD qualifications and 12 pursuing doctoral "
             "research. Operates 6 computing laboratories with 360 workstations. Key research "
             "areas include artificial intelligence, cybersecurity, cloud computing, and "
             "software engineering. Offers two specialisation tracks from the third year: Data "
             "Science and Cyber Security. Has a dedicated placement cell working with TCS, "
             "Infosys, Wipro, Cognizant, Amazon, and Microsoft. Notable achievements: 15 "
             "student research papers published in IEEE conferences in 2024-25; three teams "
             "qualified for Smart India Hackathon 2025 national finals; the BVRIT ACM Student "
             "Chapter has 280 active members."),
            ("2.2 Electronics & Communication Engineering (ECE): established 2009, intake 180 "
             "students, 38 faculty members, including "
             "6 with PhD qualifications. Maintains 5 laboratories covering VLSI design, "
             "embedded systems, communication systems, signal processing, and IoT. Partners "
             "with Texas Instruments for an embedded systems lab and National Instruments for "
             "a LabVIEW certification programme. Students access Cadence Virtuoso and Synopsys "
             "Design Compiler. Notable achievements: 8 student patents filed in 2024-25; the "
             "robotics team won second place at Robocon 2025 regional qualifiers."),
            ("2.3 Electrical & Electronics Engineering (EEE): established 2009, intake 120 "
             "students, 28 faculty members, including 5 "
             "with PhD qualifications. Operates 4 laboratories: power electronics, electrical "
             "machines, control systems, and renewable energy. Has a 10 kW rooftop solar "
             "installation used for teaching and research. Focus areas include smart grid "
             "technology, electric vehicle systems, and power system protection. Collaborates "
             "with BHEL and NTPC for industrial training programmes."),
            ("2.4 Mechanical Engineering: established 2009, intake 60 students, 25 faculty "
             "members, including 4 with PhD "
             "qualifications. Facilities include manufacturing workshops, a CAD/CAM "
             "laboratory, a thermal engineering lab, and a material testing laboratory. Has an "
             "MoU with Siemens for NX software training. Operates a student-run Formula SAE "
             "team that placed 8th nationally in Formula Bharat 2025."),
            ("2.5 Information Technology (IT): established 2009, intake 180 students, 32 "
             "faculty members, including 5 with PhD "
             "qualifications. Focuses on web technologies, database systems, software "
             "testing, and network security. Operates 4 computing laboratories with 240 "
             "workstations. Runs an annual 24-hour hackathon (BVRIT HackIT) attracting "
             "participants from 30+ colleges across Telangana. Active partnerships with Oracle "
             "Academy, Red Hat, and AWS Educate."),
            ("2.6 CSE (Artificial Intelligence & Machine Learning): established 2021, intake "
             "120 students, 18 "
             "faculty members, including 3 with PhD qualifications and 6 with industry "
             "experience in AI/ML. Has a dedicated GPU computing lab with 8 NVIDIA A100 "
             "workstations for deep learning research. Core specialisation areas: computer "
             "vision, natural language processing, reinforcement learning, and MLOps. "
             "Students complete a mandatory 6-month industry internship in the final year. "
             "Partner companies include Google, NVIDIA, and Qualcomm."),
            ("2.7 CSE (Data Science): established 2021, intake 120 students, 16 faculty "
             "members, including 2 "
             "with PhD qualifications and 5 with industry data science experience. Emphasises "
             "statistical modelling, big data systems, and data engineering. Students gain "
             "hands-on experience with Apache Spark, Hadoop, Tableau, Power BI, and cloud "
             "platforms (AWS, Azure). Partners with Deloitte and EY for case study projects."),
        ],
    },
    {
        "heading": "3. FEE STRUCTURE",
        "body": [
            ("All fees are quoted in Indian Rupees (Rs.) for the academic year 2025-26. Fees "
             "are payable annually at the beginning of each academic year. The fee structure "
             "is approved by the Telangana State Council for Higher Education (TSCHE)."),
            ("3.1 Tuition fees by programme (annual / 4-year total):"),
            ("- B.Tech CSE: Rs. 1,20,000 per year, Rs. 4,80,000 over 4 years", True),
            ("- B.Tech CSE (AI&ML): Rs. 1,35,000 per year, Rs. 5,40,000 over 4 years", True),
            ("- B.Tech CSE (Data Science): Rs. 1,35,000 per year, Rs. 5,40,000 over 4 years", True),
            ("- B.Tech ECE: Rs. 1,10,000 per year, Rs. 4,40,000 over 4 years", True),
            ("- B.Tech EEE: Rs. 1,00,000 per year, Rs. 4,00,000 over 4 years", True),
            ("- B.Tech Mechanical: Rs. 1,00,000 per year, Rs. 4,00,000 over 4 years", True),
            ("- B.Tech IT: Rs. 1,10,000 per year, Rs. 4,40,000 over 4 years", True),
            ("3.2 Hostel fees: accommodation is available for all students. The campus has 5 "
             "hostel blocks with a total capacity of 3,200 students."),
            ("- Room rent, shared 3-seater: Rs. 60,000 per year, Rs. 2,40,000 over 4 years", True),
            ("- Room rent, shared 2-seater: Rs. 75,000 per year, Rs. 3,00,000 over 4 years", True),
            ("- Mess charges (vegetarian): Rs. 48,000 per year, Rs. 1,92,000 over 4 years", True),
            ("- Mess charges (non-vegetarian): Rs. 54,000 per year, Rs. 2,16,000 over 4 years", True),
            ("3.3 Other fees:"),
            ("- Transport (college bus): Rs. 45,000 per year, optional", True),
            ("- Laboratory fee: Rs. 15,000 per year", True),
            ("- Library & digital resources: Rs. 8,000 per year", True),
            ("- Examination fee: Rs. 5,000 per semester (Rs. 10,000 per year)", True),
            ("- Student activity fee: Rs. 3,000 per year", True),
            ("- Caution deposit (refundable): Rs. 10,000, one-time at admission", True),
            ("- Admission processing fee: Rs. 5,000, one-time at admission", True),
            ("3.4 Total cost of attendance (estimated, 4 years, hostel residence with a "
             "3-seater room and vegetarian mess):"),
            ("- CSE: tuition Rs. 4,80,000 + hostel room Rs. 2,40,000 + mess Rs. 1,92,000 + lab "
             "Rs. 60,000 + library Rs. 32,000 + exam Rs. 40,000 + activity Rs. 12,000 + "
             "one-time Rs. 15,000 = Rs. 10,71,000 total", True),
            ("- ECE: same components except tuition Rs. 4,40,000 = Rs. 10,31,000 total", True),
            ("- EEE: same components except tuition Rs. 4,00,000 = Rs. 9,91,000 total", True),
            ("- Mechanical: same components as EEE, tuition Rs. 4,00,000 = Rs. 9,91,000 total", True),
            ("Note: transport fees (Rs. 45,000/year) are optional and not included in the "
             "totals above. Students using their own transport do not pay this fee."),
        ],
    },
    {
        "heading": "4. SCHOLARSHIPS & FEE CONCESSIONS",
        "body": [
            ("BVRIT offers several scholarship schemes to support meritorious and "
             "economically disadvantaged students. Scholarships are applied as a percentage "
             "discount on the annual tuition fee only (not on hostel, mess, or other fees)."),
            ("4.1 Merit scholarships:"),
            ("- Founder's Scholarship: EAMCET rank within top 1,000 -- 100% discount (full tuition waiver); renewable if CGPA >= 8.5", True),
            ("- Academic Excellence: EAMCET rank 1,001-5,000 -- 50% discount on tuition; renewable if CGPA >= 8.0", True),
            ("- Merit Reward: EAMCET rank 5,001-15,000 -- 25% discount on tuition; renewable if CGPA >= 7.5", True),
            ("- Sports Scholarship: national/state level sports achievement -- 25% discount on tuition; renewable if active participation", True),
            ("4.2 Need-based fee concessions:"),
            ("- Economically Weaker Section (EWS): family income below Rs. 8 lakh/year -- 50% discount on tuition", True),
            ("- SC/ST Scholarship: Telangana state SC/ST students -- full tuition reimbursement via state government", True),
            ("- BC Fee Reimbursement: Telangana BC students, income under Rs. 2 lakh -- full tuition reimbursement via state government", True),
            ("- Sibling Discount: second sibling currently enrolled at BVRIT -- 10% discount on tuition", True),
            ("Note: government scholarships (SC/ST, BC) are subject to state government "
             "disbursement timelines. Students must pay the full fee at admission and receive "
             "reimbursement after government processing, which typically takes 3-6 months."),
        ],
    },
    {
        "heading": "5. ADMISSIONS",
        "body": [
            ("5.1 Eligibility: candidates must have passed the Intermediate examination (or "
             "equivalent) with Mathematics, Physics, and Chemistry (MPC) with a minimum of 45% "
             "aggregate marks (40% for reserved categories). A valid TS EAMCET or AP EAMCET "
             "rank is required for admission through counselling. Direct admission under the "
             "management quota requires a minimum of 50% in MPC and a valid EAMCET rank. JEE "
             "Main qualified candidates are also eligible."),
            ("5.2 Admission process:"),
            ("- Step 1: Obtain TS EAMCET or AP EAMCET rank", True),
            ("- Step 2: Participate in the TSCHE web counselling process and select BVRIT as a preference", True),
            ("- Step 3: Report to the college with original documents within 5 days of allotment", True),
            ("- Step 4: Complete document verification, fee payment, and hostel allocation", True),
            ("- Step 5: Attend the orientation programme on the first day of classes", True),
            ("5.3 Important dates -- Academic Year 2025-26:"),
            ("- TS EAMCET 2025 Exam: 15 May 2025 (Completed)", True),
            ("- TS EAMCET Results Announced: 5 June 2025 (Completed)", True),
            ("- TSCHE Web Counselling Round 1: 1 July - 15 July 2025 (Completed)", True),
            ("- TSCHE Web Counselling Round 2: 20 July - 31 July 2025 (Completed)", True),
            ("- Last Date for Round 2 Reporting: 5 August 2025 (Upcoming)", True),
            ("- Management Quota Admission Deadline: 15 August 2025 (Upcoming)", True),
            ("- Orientation Programme: 18 August 2025 (Upcoming)", True),
            ("- Classes Commence: 19 August 2025 (Upcoming)", True),
            ("- Last Date for Late Admission (with penalty): 31 August 2025 (Upcoming)", True),
            ("- Mid-Semester Exam 1: 15 October - 20 October 2025 (Upcoming)", True),
            ("- End-Semester Exam (Odd Semester): 1 December - 15 December 2025 (Upcoming)", True),
            ("- Even Semester Classes Begin: 5 January 2026 (Upcoming)", True),
            ("- Mid-Semester Exam 2: 15 March - 20 March 2026 (Upcoming)", True),
            ("- End-Semester Exam (Even Semester): 1 May - 15 May 2026 (Upcoming)", True),
            ("Note: all dates are subject to change based on TSCHE and JNTUH academic calendar "
             "notifications. Students should verify dates on the official BVRIT website "
             "(www.bvrithyderabad.edu.in) before making any decisions."),
        ],
    },
    {
        "heading": "6. PLACEMENTS",
        "body": [
            ("The Training & Placement Cell coordinates campus recruitment activities, "
             "industry internships, and career development programmes. The placement season "
             "runs from August to April each year."),
            ("6.1 Placement statistics (2024-25) -- eligible students / students placed / "
             "placement % / highest package (LPA) / average package (LPA) / median package (LPA):"),
            ("- CSE: 228 eligible, 205 placed, 89.9%, highest Rs. 24.0 LPA, average Rs. 6.2 LPA, median Rs. 5.5 LPA", True),
            ("- ECE: 165 eligible, 132 placed, 80.0%, highest Rs. 18.5 LPA, average Rs. 5.1 LPA, median Rs. 4.5 LPA", True),
            ("- EEE: 108 eligible, 78 placed, 72.2%, highest Rs. 12.0 LPA, average Rs. 4.3 LPA, median Rs. 3.8 LPA", True),
            ("- Mechanical: 52 eligible, 35 placed, 67.3%, highest Rs. 10.5 LPA, average Rs. 4.0 LPA, median Rs. 3.5 LPA", True),
            ("- IT: 168 eligible, 147 placed, 87.5%, highest Rs. 21.0 LPA, average Rs. 5.8 LPA, median Rs. 5.2 LPA", True),
            ("- CSE (AI&ML): 105 eligible, 89 placed, 84.8%, highest Rs. 22.0 LPA, average Rs. 6.5 LPA, median Rs. 5.8 LPA", True),
            ("- CSE (Data Science): 102 eligible, 85 placed, 83.3%, highest Rs. 20.0 LPA, average Rs. 6.0 LPA, median Rs. 5.5 LPA", True),
            ("6.2 Top recruiters (2024-25): IT Services -- TCS, Infosys, Wipro, Cognizant, HCL "
             "Technologies, Tech Mahindra, Capgemini. Product Companies -- Amazon, Microsoft, "
             "Google (internships), Salesforce, ServiceNow. Core Companies -- BHEL, L&T, Tata "
             "Motors, Schneider Electric, Siemens. Startups & Mid-size -- Zoho, Freshworks, "
             "Razorpay, PhonePe, Swiggy (tech roles). Consulting -- Deloitte, EY, KPMG "
             "(technology consulting roles)."),
            ("6.3 Internship programme: all students complete a mandatory internship -- 6 "
             "weeks after Year 3 (summer) and 6 months in Year 4 (for select programmes). "
             "Stipends range from Rs. 10,000 to Rs. 60,000 per month depending on the company "
             "and role. In 2024-25, 78% of students who completed internships at product "
             "companies received pre-placement offers."),
            ("Disclaimer: placement statistics are historical data from the 2024-25 academic "
             "year and do not guarantee future outcomes. Individual placement depends on "
             "academic performance, skills, interview performance, and market conditions. "
             "BVRIT does not guarantee placement to any student."),
        ],
    },
    {
        "heading": "7. CAMPUS & FACILITIES",
        "body": [
            ("7.1 Academic facilities: Central Library with 50,000+ volumes, 2,500 e-journals, "
             "24/7 digital access, and a 200-seat reading hall. Computing labs with 1,200+ "
             "workstations across all departments and 100 Mbps dedicated internet. Smart "
             "classrooms equipped with interactive displays and lecture recording. A Research "
             "Centre with high-performance computing, a GPU cluster, and 3D printing. A "
             "60-seat Language Lab for English communication and soft skills training."),
            ("7.2 Hostel facilities: on-campus accommodation for all students across 5 hostel "
             "blocks (Jasmine, Lotus, Orchid, Rose, and Tulip) with a total capacity of 3,200 "
             "students. Each room is furnished with beds, study tables, chairs, and wardrobes. "
             "Facilities include 24/7 Wi-Fi (50 Mbps per hostel block), RO purified drinking "
             "water, hot water supply (6-8 AM, 6-8 PM), laundry service (outsourced, Rs. "
             "300/month), common rooms with TV and indoor games, and 24-hour security with "
             "CCTV surveillance. The mess serves three meals daily plus evening snacks, with a "
             "weekly rotating menu covering vegetarian and non-vegetarian preferences; a "
             "student mess committee reviews food quality monthly."),
            ("7.3 Sports & recreation: indoor -- badminton courts (4), table tennis (6 "
             "tables), chess room, yoga hall, gymnasium. Outdoor -- cricket ground, football "
             "field, basketball courts (2), volleyball courts (2), tennis court, 400m athletic "
             "track. Annual sports meet: BVRIT Olympia (held in February). Professional "
             "coaching available for badminton, basketball, and athletics."),
            ("7.4 Transport: BVRIT operates 35 college buses covering routes across Hyderabad, "
             "Secunderabad, Kukatpally, Miyapur, Ameerpet, Dilsukhnagar, and LB Nagar. Buses "
             "depart from designated pickup points at 7:00 AM and return by 5:30 PM. The "
             "annual transport fee is Rs. 45,000. Students using their own transport "
             "(two-wheelers permitted with valid licence and helmet) do not pay this fee. "
             "Parking is available on campus at no additional cost."),
            ("7.5 Medical & wellness: a full-time medical officer is available on campus (9 AM "
             "- 5 PM, Monday-Saturday). Emergency medical support is available 24/7. The "
             "nearest hospital is Apollo Hospitals, Jubilee Hills (45 km). An ambulance is "
             "stationed on campus. All students are covered under a group medical insurance "
             "policy (Rs. 1 lakh coverage) included in the admission fee."),
        ],
    },
    {
        "heading": "8. KEY FACULTY",
        "body": [
            ("8.1 College leadership:"),
            ("- Principal: Dr. K. Lakshmi Prasad, PhD (IIT Madras), 28 years of academic experience", True),
            ("- Vice-Principal: Dr. M. Sravanthi, PhD (NIT Warangal), 22 years in academia", True),
            ("- Dean (Academics): Dr. P. Raghavendra, PhD (JNTUH), responsible for curriculum and quality", True),
            ("- Dean (Student Affairs): Dr. S. Kavitha, PhD (Osmania University), responsible for student welfare", True),
            ("- Training & Placement Officer: Prof. N. Venkat Reddy, 18 years of industry + academic experience", True),
            ("8.2 Department heads (HOD / qualification / research area):"),
            ("- CSE: Dr. A. Padmavathi, PhD (IIT Hyderabad) -- Machine Learning, NLP", True),
            ("- CSE (AI&ML): Dr. R. Swathi, PhD (IIIT Hyderabad) -- Deep Learning, Computer Vision", True),
            ("- CSE (DS): Dr. B. Lakshmi, PhD (IISc Bangalore) -- Big Data Analytics, Statistical Learning", True),
            ("- ECE: Dr. K. Anitha, PhD (NIT Warangal) -- VLSI Design, Embedded Systems", True),
            ("- EEE: Dr. T. Manohar, PhD (IIT Bombay) -- Power Electronics, Smart Grids", True),
            ("- Mechanical: Dr. V. Anuradha, PhD (NIT Trichy) -- CAD/CAM, Additive Manufacturing", True),
            ("- IT: Dr. S. Priya, PhD (JNTUH) -- Cloud Computing, Network Security", True),
        ],
    },
    {
        "heading": "9. STUDENT SUPPORT SERVICES",
        "body": [
            ("9.1 Student Counselling Centre: provides free, confidential support for academic "
             "stress, personal issues, and mental health concerns. Two full-time counsellors "
             "are available Monday-Saturday, 9 AM - 5 PM. Appointments can be booked in person "
             "at the Admin Block, Room 105, or via email at counselling@bvrit.ac.in; walk-ins "
             "are welcome."),
            ("In case of crisis: students in distress can contact the counselling centre "
             "directly or call the 24-hour student helpline at 08455-221144. For after-hours "
             "emergencies, contact hostel wardens or campus security (available 24/7)."),
            ("External crisis resources:"),
            ("- iCall -- 9152987821 (Mon-Sat, 8 AM - 10 PM)", True),
            ("- Vandrevala Foundation Helpline -- 1860-2662-345 (24/7)", True),
            ("- NIMHANS Helpline -- 080-46110007", True),
            ("9.2 Anti-Ragging Committee: BVRIT has a zero-tolerance policy on ragging. The "
             "Anti-Ragging Committee can be contacted at antiragging@bvrit.ac.in or the UGC "
             "helpline 1800-180-5522. All complaints are investigated within 48 hours."),
            ("9.3 Grievance Redressal: students can submit grievances through the online "
             "portal (portal.bvrit.ac.in/grievance) or in writing to the Dean (Student "
             "Affairs). All grievances receive a response within 7 working days. The "
             "Grievance Redressal Committee meets monthly to review pending cases."),
        ],
    },
    {
        "heading": "10. CONTACT INFORMATION",
        "body": [
            ("Purpose / Email / Phone:"),
            ("- General Enquiries: info@bvrit.ac.in, 08455-221100", True),
            ("- Admissions Office: admissions@bvrit.ac.in, 08455-221111", True),
            ("- Fee Payment Queries: accounts@bvrit.ac.in, 08455-221122", True),
            ("- Training & Placement: placements@bvrit.ac.in, 08455-221133", True),
            ("- Hostel & Accommodation: hostel@bvrit.ac.in, 08455-221144", True),
            ("- Student Counselling: counselling@bvrit.ac.in, 08455-221155", True),
            ("- Transport: transport@bvrit.ac.in, 08455-221166", True),
            ("- Examination Cell: exams@bvrit.ac.in, 08455-221177", True),
            ("- Principal's Office: principal@bvrit.ac.in, 08455-221100 (ext. 101)", True),
            ("- Dean (Student Affairs): dean.sa@bvrit.ac.in, 08455-221100 (ext. 105)", True),
            ("10.1 Campus address: B V Raju Institute of Technology (BVRIT) Hyderabad College "
             "of Engineering for Women, Narsapur, Medak District, Telangana -- 502313, India."),
            ("Website: www.bvrithyderabad.edu.in. Google Maps: "
             "https://maps.google.com/?q=BVRIT+Narsapur"),
        ],
    },
]


def build_pdf(output_path=OUTPUT_PATH) -> None:
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="BVRIT Hyderabad College of Engineering for Women - Information Document",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=18, spaceAfter=12)
    subtitle_style = ParagraphStyle("SubtitleStyle", parent=styles["Italic"], fontSize=10, spaceAfter=6)
    heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading1"], fontSize=14, spaceBefore=6, spaceAfter=10)
    body_style = ParagraphStyle("BodyStyle", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=8)
    bullet_style = ParagraphStyle("BulletStyle", parent=body_style, spaceAfter=4, leftIndent=14)

    def esc(text: str) -> str:
        # Paragraph text is parsed as a restricted XML-like markup -- an
        # unescaped "&" (e.g. in "AI&ML", "L&T") gets silently mangled into
        # garbage like "AI&ML;" by reportlab's parser, corrupting both the
        # rendered PDF and the text ingest.py later extracts from it.
        return html.escape(text, quote=False)

    story = []
    story.append(Paragraph(esc("BVRIT Hyderabad College of Engineering for Women"), title_style))
    story.append(Paragraph("Comprehensive reference for the BVRIT FAQ Chatbot &middot; Academic Year 2025-26", subtitle_style))
    story.append(PageBreak())

    for i, section in enumerate(SECTIONS):
        story.append(Paragraph(esc(section["heading"]), heading_style))
        for item in section["body"]:
            if isinstance(item, tuple):
                text, _is_bullet = item
                # The text already carries its own literal "- " prefix (see
                # SECTIONS above) -- rendered as a plain Paragraph, not wrapped
                # in a ListFlowable/ListItem, whose bullet-glyph mechanism
                # leaves a stray control character in extracted text (pypdf
                # pulls the decorative bullet glyph itself out as U+007F,
                # polluting the text between every single bullet line).
                story.append(Paragraph(esc(text), bullet_style))
            else:
                story.append(Paragraph(esc(item), body_style))
        if i < len(SECTIONS) - 1:
            story.append(PageBreak())

    doc.build(story)
    print(f"Saved {output_path} ({len(SECTIONS)} sections + 1 title page)")


if __name__ == "__main__":
    build_pdf()
