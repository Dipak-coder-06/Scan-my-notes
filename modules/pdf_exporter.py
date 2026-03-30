"""
modules/pdf_exporter.py
-----------------------
Generates a downloadable PDF of the Q&A session using reportlab.
"""
import io
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

def export_qa_to_pdf(doc_name: str, chat_history: List[Dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=HexColor('#1e40af'),
        spaceAfter=20
    )
    
    question_style = ParagraphStyle(
        'Question',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=HexColor('#1f2937'),
        spaceBefore=15,
        spaceAfter=8
    )
    
    answer_style = ParagraphStyle(
        'Answer',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica',
        textColor=HexColor('#374151'),
        leading=16,
        spaceAfter=6
    )

    citation_style = ParagraphStyle(
        'Citation',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Oblique',
        textColor=HexColor('#6b7280'),
        leftIndent=15,
        spaceAfter=15
    )

    story = []
    
    # Title
    story.append(Paragraph(f"Ironclad Scholar QA Report", title_style))
    story.append(Paragraph(f"<b>Document:</b> {doc_name}", styles['Normal']))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#d1d5db'), spaceAfter=20))

    # Extract Q&A pairs
    questions = [m for m in chat_history if m["role"] == "user"]
    answers = [m for m in chat_history if m["role"] == "assistant"]

    if not questions:
        story.append(Paragraph("No questions were asked during this session.", styles['Normal']))
    
    for q, a in zip(questions, answers):
        # Question
        story.append(Paragraph(f"Q: {q['content']}", question_style))
        
        # Answer
        # Clean answer text of basic markdown for PDF (very basic strip for compatibility)
        ans_text = a["content"].replace("**", "").replace("*", "")
        story.append(Paragraph(f"A: {ans_text}", answer_style))
        
        # Citations
        citations = a.get("citations", [])
        if citations and not a.get("no_information"):
            c_text = "Sources: " + " | ".join([f"[{c['citation_index']}] {c['label']}" for c in citations])
            story.append(Paragraph(c_text, citation_style))
        else:
            story.append(Spacer(1, 10))
            
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#e5e7eb'), spaceBefore=10, spaceAfter=10))

    doc.build(story)
    return buffer.getvalue()


def export_mcqs_to_pdf(doc_name: str, mcqs: List[Dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=HexColor('#1e40af'),
        spaceAfter=20
    )
    
    q_style = ParagraphStyle(
        'Question',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=HexColor('#1f2937'),
        spaceBefore=15,
        spaceAfter=8
    )
    
    opt_style = ParagraphStyle(
        'Option',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica',
        textColor=HexColor('#374151'),
        leftIndent=20,
        spaceAfter=4
    )
    
    ans_style = ParagraphStyle(
        'Answer',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=HexColor('#166534'), # Green
        spaceBefore=10,
        spaceAfter=4
    )
    
    expl_style = ParagraphStyle(
        'Explanation',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Oblique',
        textColor=HexColor('#4b5563'),
        spaceAfter=15
    )

    story = []
    
    story.append(Paragraph(f"Ironclad Scholar MCQ Quiz", title_style))
    story.append(Paragraph(f"<b>Document:</b> {doc_name}", styles['Normal']))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#d1d5db'), spaceAfter=20))

    if not mcqs:
        story.append(Paragraph("No MCQs generated.", styles['Normal']))
    else:
        # Part 1: Questions Only
        story.append(Paragraph("<b>Quiz Questions</b>", styles['Heading2']))
        for i, mcq in enumerate(mcqs, 1):
            story.append(Paragraph(f"{i}. {mcq.get('question', '')}", q_style))
            for opt in mcq.get('options', []):
                story.append(Paragraph(opt, opt_style))
            story.append(Spacer(1, 10))
            
        story.append(Paragraph("<b>— End of Quiz —</b>", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Part 2: Answer Key & Explanations
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#d1d5db'), spaceAfter=20))
        story.append(Paragraph("<b>Answer Key & Explanations</b>", styles['Heading2']))
        for i, mcq in enumerate(mcqs, 1):
            story.append(Paragraph(f"Question {i}", q_style))
            story.append(Paragraph(f"Correct Answer: {mcq.get('correct_answer', '')}", ans_style))
            story.append(Paragraph(f"Explanation: {mcq.get('explanation', '')}", expl_style))

    doc.build(story)
    return buffer.getvalue()
