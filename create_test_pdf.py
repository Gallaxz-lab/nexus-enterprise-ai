import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def generate_sanitized_resume(filename: str = "sanitized-candidate-resume.pdf"):
    """Programmatically compiles a production-compliant test candidate resume asset."""
    # Ensure local path targets exist
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom typographical framework assignments
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'DocSection',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=8
    )

    story = []

    # Document Header Space
    story.append(Paragraph("JANE DOE", title_style))
    story.append(Paragraph("<b>Role Tracking Signature:</b> Senior Python Backend Developer", body_style))
    story.append(Paragraph("<b>Tenancy Assignment Namespace:</b> Organization A (Sanitized Data Profile)", body_style))
    story.append(Spacer(1, 10))

    # Professional Summary Block
    story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
    summary_text = (
        "Highly analytical Senior Backend Engineer with over 6 years of dedicated expertise specializing in "
        "the Python software ecosystem. Extensively field-tested constructing highly resilient microservice architectural "
        "layers running over the FastAPI framework. Proven track record auditing, refactoring, and tuning high-throughput "
        "relational data storage structures inside production-grade PostgreSQL engines. Expertly implemented robust "
        "application data isolation boundaries utilizing runtime context filtering keys to enforce enterprise row-level tenant security."
    )
    story.append(Paragraph(summary_text, body_style))

    # Core Competencies Block
    story.append(Paragraph("TECHNICAL EXPERTISE MATRIX", section_style))
    skills_text = (
        "<b>Programming Languages & Tooling:</b> Python (Expert), SQL, Bash, Go<br/>"
        "<b>Frameworks & API Architecture:</b> FastAPI, Pydantic, SQLAlchemy Core ORM, Alembic Migrations<br/>"
        "<b>Database Engines:</b> PostgreSQL (Advanced Performance Tuning), Redis Cache Optimization, SQLite<br/>"
        "<b>Deployment Systems:</b> Docker, Docker Compose, Linux Architecture Systems"
    )
    story.append(Paragraph(skills_text, body_style))

    # Professional Experience Block
    story.append(Paragraph("CHRONOLOGICAL WORK HISTORY", section_style))
    
    job_title = "<b>Senior Backend Software Engineer</b> — Enterprise Automation Co. (2022 – Present)"
    story.append(Paragraph(job_title, body_style))
    
    job_desc = (
        "• Engineered a multi-tenant cloud automation backend orchestration engine from scratch utilizing FastAPI and PostgreSQL.<br/>"
        "• Structured explicit query token context validation interceptors guaranteeing absolute enterprise tenant group boundaries.<br/>"
        "• Optimized long-running relational execution times by 40% using advanced execution planning, indexing strategies, and raw connection pooling implementations.<br/>"
        "• Wrote 50+ fully comprehensive endpoint integration verification unit test cases utilizing pytest."
    )
    story.append(Paragraph(job_desc, body_style))
    
    # Portfolio Disclaimer Footnote Footprint
    story.append(Spacer(1, 20))
    disclaimer_text = (
        "<font color='gray' size='8'><i>This document is a fully sanitized, fictional mock profile data portfolio generation asset "
        "built exclusively to assert validation pathways across the Nexus Enterprise AI platform integration engine test suite. "
        "AI verification disclaimer: This is for informational purposes only. AI responses may include mistakes.</i></font>"
    )
    story.append(Paragraph(disclaimer_text, body_style))

    # Write binary out directly to target disk path
    doc.build(story)

if __name__ == "__main__":
    generate_sanitized_resume()
