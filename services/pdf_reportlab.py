from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from flask import render_template
import io
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_fiche_personnel_reportlab(personnel):
    """Génère une fiche individuelle au format PDF avec ReportLab"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # Titre
    elements.append(Paragraph("OFFICE NATIONAL DES AÉROPORTS", styles['Title']))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph("FICHE INDIVIDUELLE DU PERSONNEL", styles['Heading2']))
    elements.append(Spacer(1, 1*cm))
    
    # Informations personnelles
    elements.append(Paragraph("INFORMATIONS PERSONNELLES", styles['Heading3']))
    data = [
        ["Matricule:", personnel.matricule or "-"],
        ["CIN:", personnel.carte_identite or "-"],
        ["Nom & Prénom:", f"{personnel.nom} {personnel.prenom}"],
        ["Date naissance:", personnel.date_de_naissance.strftime('%d/%m/%Y') if personnel.date_de_naissance else "-"],
        ["Lieu naissance:", personnel.lieu_naissance or "-"],
    ]
    table = Table(data, colWidths=[4*cm, 10*cm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Informations professionnelles
    elements.append(Paragraph("INFORMATIONS PROFESSIONNELLES", styles['Heading3']))
    data = [
        ["Date recrutement:", personnel.date_recrutement.strftime('%d/%m/%Y') if personnel.date_recrutement else "-"],
        ["Grade:", personnel.grade_ref.libelle if personnel.grade_ref else "-"],
        ["Emploi:", personnel.emploi_ref.identifiant_emploi if personnel.emploi_ref else "-"],
        ["Unité:", personnel.unite_ref.unite_organisat if personnel.unite_ref else "-"],
    ]
    table = Table(data, colWidths=[4*cm, 10*cm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
    ]))
    elements.append(table)
    
    # Pied de page
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph(f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Fonction d'adaptation pour garder le même nom
def generate_fiche_personnel(personnel):
    """Wrapper pour ReportLab"""
    return generate_fiche_personnel_reportlab(personnel)