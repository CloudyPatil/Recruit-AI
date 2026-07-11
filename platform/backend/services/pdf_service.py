from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import io


def generate_report_pdf(report):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.5*inch, bottomMargin=0.5*inch,
        leftMargin=0.6*inch, rightMargin=0.6*inch
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        fontSize=20, textColor=HexColor('#1a56db'),
        spaceAfter=4, alignment=TA_LEFT
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=11, textColor=HexColor('#6b7280'),
        spaceAfter=12
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'],
        fontSize=13, textColor=HexColor('#111827'),
        spaceBefore=12, spaceAfter=6,
        borderPadding=4
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=10, textColor=HexColor('#374151'),
        spaceAfter=4, leading=14
    )
    verdict_style = ParagraphStyle(
        'Verdict', parent=styles['Normal'],
        fontSize=14, textColor=HexColor('#ffffff'),
        alignment=TA_CENTER, spaceBefore=8, spaceAfter=8
    )
    
    elements = []
    
    candidate = report.get("candidate", {})
    job = report.get("job", {})
    scores = report.get("scores", {})
    integrity = report.get("integrity", {})
    truth = report.get("truthfulness", {})
    
    # HEADER
    elements.append(Paragraph(candidate.get("name", "Candidate"), title_style))
    elements.append(Paragraph(
        f"{job.get('title','')} {' at ' + job['company'] if job.get('company') else ''}",
        subtitle_style
    ))
    
    # Contact + verdict table
    verdict = report.get("verdict") or report.get("recommendation", "PENDING")
    verdict_color = "#10b981" if verdict in ["Strong Hire", "Hire", "RECOMMENDED"] else \
                    "#f59e0b" if verdict == "Maybe" else "#ef4444"
    
    contact_data = [[
        f"Email: {candidate.get('email','N/A')}\n"
        f"Phone: {candidate.get('phone','N/A')}\n"
        f"Location: {candidate.get('location','N/A')}",
        verdict
    ]]
    contact_table = Table(contact_data, colWidths=[4*inch, 2.5*inch])
    contact_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (1,0), (1,0), HexColor(verdict_color)),
        ('TEXTCOLOR', (1,0), (1,0), HexColor('#ffffff')),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('FONT', (1,0), (1,0), 'Helvetica-Bold', 12),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS', [4,4,4,4]),
    ]))
    elements.append(contact_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # EXECUTIVE SUMMARY
    if report.get("executive_summary"):
        elements.append(Paragraph("Executive Summary", section_style))
        elements.append(Paragraph(report["executive_summary"], body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    # STRENGTH + CONCERN
    if report.get("top_strength") or report.get("biggest_concern"):
        sc_data = [
            ["TOP STRENGTH", "BIGGEST CONCERN"],
            [report.get("top_strength","N/A"), report.get("biggest_concern","N/A")]
        ]
        sc_table = Table(sc_data, colWidths=[3.25*inch, 3.25*inch])
        sc_table.setStyle(TableStyle([
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
            ('FONT', (0,1), (-1,1), 'Helvetica', 9),
            ('BACKGROUND', (0,0), (0,0), HexColor('#dcfce7')),
            ('BACKGROUND', (1,0), (1,0), HexColor('#fee2e2')),
            ('TEXTCOLOR', (0,0), (0,0), HexColor('#166534')),
            ('TEXTCOLOR', (1,0), (1,0), HexColor('#991b1b')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
        ]))
        elements.append(sc_table)
        elements.append(Spacer(1, 0.15*inch))
    
    # SCORE BREAKDOWN
    elements.append(Paragraph("Score Breakdown", section_style))
    
    final = scores.get("final", 0)
    score_data = [
        ["Metric", "Score", "Visual"],
        ["Final Score", f"{final:.1f}%", _bar(final)],
        ["ML Resume Match", f"{scores.get('ml_score',0):.1f}%", _bar(scores.get('ml_score',0))],
        ["Communication (R1)", f"{scores.get('round1',0):.1f}%", _bar(scores.get('round1',0))],
        ["Aptitude (R2)", f"{scores.get('round2',0):.1f}%", _bar(scores.get('round2',0))],
        ["Technical (R3)", f"{scores.get('round3',0):.1f}%", _bar(scores.get('round3',0))],
    ]
    score_table = Table(score_data, colWidths=[2*inch, 1*inch, 3.5*inch])
    score_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
        ('FONT', (0,1), (0,1), 'Helvetica-Bold', 10),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#f3f4f6')),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # SKILL VERIFICATION
    if report.get("skill_verification"):
        elements.append(Paragraph("Skill Verification", section_style))
        sv_data = [["Skill", "Status", "Source"]]
        for s in report["skill_verification"][:10]:
            sources = []
            if s.get("in_github"): sources.append("GitHub")
            if s.get("in_interview"): sources.append("Interview")
            sv_data.append([
                s["skill"].title(),
                s["status"],
                ", ".join(sources) or "Resume only"
            ])
        sv_table = Table(sv_data, colWidths=[2*inch, 2*inch, 2.5*inch])
        sv_table.setStyle(TableStyle([
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
            ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
            ('BACKGROUND', (0,0), (-1,0), HexColor('#f3f4f6')),
            ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(sv_table)
        elements.append(Spacer(1, 0.15*inch))
    
    # COMMUNICATION ANALYSIS
    comm = report.get("communication", {})
    if comm:
        elements.append(Paragraph("Communication Analysis", section_style))
        comm_data = [
            ["Clarity", "Confidence", "Structure", "Grammar", "Pace"],
            [
                f"{comm.get('clarity',0)}/10",
                f"{comm.get('confidence',0)}/10",
                f"{comm.get('structure',0)}/10",
                f"{comm.get('grammar',0)}/10",
                comm.get('pace','N/A')
            ]
        ]
        comm_table = Table(comm_data, colWidths=[1.3*inch]*5)
        comm_table.setStyle(TableStyle([
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
            ('FONT', (0,1), (-1,1), 'Helvetica-Bold', 11),
            ('BACKGROUND', (0,0), (-1,0), HexColor('#f3f4f6')),
            ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(comm_table)
        elements.append(Spacer(1, 0.15*inch))
    
    # KEY MOMENTS
    best = report.get("best_answer", {})
    concern = report.get("concerning_answer", {})
    if best.get("question") or concern.get("question"):
        elements.append(Paragraph("Key Moments", section_style))
        
        if best.get("question"):
            elements.append(Paragraph(
                f"<b>Best Answer</b> — Q: {best.get('question','')}",
                body_style
            ))
            elements.append(Paragraph(
                f'<i>"{best.get("answer_excerpt","")}"</i>',
                body_style
            ))
            elements.append(Paragraph(
                f"✓ {best.get('why_good','')}",
                body_style
            ))
            elements.append(Spacer(1, 0.08*inch))
        
        if concern.get("question"):
            elements.append(Paragraph(
                f"<b>Concerning Answer</b> — Q: {concern.get('question','')}",
                body_style
            ))
            elements.append(Paragraph(
                f'<i>"{concern.get("answer_excerpt","")}"</i>',
                body_style
            ))
            elements.append(Paragraph(
                f"⚠ {concern.get('why_concerning','')}",
                body_style
            ))
        elements.append(Spacer(1, 0.15*inch))
    
    # TRUTHFULNESS
    if truth and truth.get("score") is not None:
        elements.append(Paragraph("Resume Truthfulness Check", section_style))
        truth_data = [
            ["Truthfulness Score", f"{truth.get('score',0)}/10"],
            ["Verified Claims", truth.get("verified_claims","N/A")],
            ["Suspicious Claims", truth.get("suspicious_claims","N/A")],
        ]
        truth_table = Table(truth_data, colWidths=[2*inch, 4.5*inch])
        truth_table.setStyle(TableStyle([
            ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 9),
            ('FONT', (1,0), (1,-1), 'Helvetica', 9),
            ('BACKGROUND', (0,0), (0,-1), HexColor('#f3f4f6')),
            ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(truth_table)
        elements.append(Spacer(1, 0.15*inch))
    
    # INTEGRITY
    elements.append(Paragraph("Integrity Report", section_style))
    int_data = [
        ["Status", "Risk Level", "Total Flags"],
        [
            integrity.get("status","CLEAN"),
            integrity.get("risk_level","LOW"),
            str(integrity.get("total_flags",0))
        ]
    ]
    int_table = Table(int_data, colWidths=[2.2*inch]*3)
    int_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('FONT', (0,1), (-1,1), 'Helvetica-Bold', 10),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#f3f4f6')),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(int_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # ACTION ITEMS
    if report.get("action_items"):
        elements.append(Paragraph("Discussion Points for HR", section_style))
        for i, item in enumerate(report["action_items"], 1):
            elements.append(Paragraph(f"{i}. {item}", body_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # AI SUMMARY
    if report.get("ai_summary"):
        elements.append(Paragraph("AI Summary", section_style))
        elements.append(Paragraph(report["ai_summary"], body_style))
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        "<i>Generated by RecruitAI Platform</i>",
        ParagraphStyle('Footer', parent=body_style, alignment=TA_CENTER,
                       fontSize=8, textColor=HexColor('#9ca3af'))
    ))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def _bar(score):
    """Create visual bar for PDF"""
    filled = int(score / 5)  # 20 chars max
    empty = 20 - filled
    return "█" * filled + "░" * empty