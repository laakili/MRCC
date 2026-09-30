from weasyprint import HTML
from flask import render_template
from datetime import datetime
import io
import logging

logger = logging.getLogger(__name__)

def generate_fiche_personnel(personnel):
    """Génère une fiche individuelle au format PDF"""
    try:
        html = render_template('pdf/fiche_personnel.html', 
                              personnel=personnel, 
                              now=datetime.now)
        
        # Essayer avec différents paramètres selon la version
        try:
            # Pour WeasyPrint >= 54
            pdf = HTML(string=html).write_pdf()
        except TypeError:
            try:
                # Pour WeasyPrint < 54
                pdf = HTML(string=html).write_pdf()
            except Exception as e:
                logger.error(f"Erreur PDF WeasyPrint: {e}")
                # Fallback vers une méthode alternative
                return generate_simple_pdf(html)
        
        return pdf
    except Exception as e:
        logger.error(f"Erreur génération PDF: {e}")
        return generate_error_pdf(f"Erreur: {str(e)}")

def generate_simple_pdf(html_content):
    """Génère un PDF simple avec une approche alternative"""
    try:
        # Tentative avec une configuration minimale
        html = HTML(string=html_content)
        return html.write_pdf()
    except Exception as e:
        logger.error(f"Erreur PDF simple: {e}")
        return generate_error_pdf("Erreur de génération PDF")

def generate_error_pdf(error_message):
    """Génère un PDF simple en cas d'erreur"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Erreur</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 50px; }}
            .error {{ color: red; padding: 20px; border: 1px solid red; }}
        </style>
    </head>
    <body>
        <h1>Erreur de génération PDF</h1>
        <div class="error">{error_message}</div>
        <p>Veuillez contacter l'administrateur.</p>
    </body>
    </html>
    """
    try:
        return HTML(string=html).write_pdf()
    except:
        # Si tout échoue, retourner un message d'erreur simple
        return b"Erreur PDF"

def generate_absence_pdf(absence):
    """Génère un justificatif d'absence au format PDF"""
    try:
        html = render_template('pdf/absence.html', 
                              absence=absence, 
                              now=datetime.now)
        return HTML(string=html).write_pdf()
    except Exception as e:
        logger.error(f"Erreur PDF absence: {e}")
        return generate_error_pdf(f"Erreur: {str(e)}")

def generate_ordre_mission_pdf(mission):
    """Génère un ordre de mission au format PDF"""
    try:
        html = render_template('pdf/ordre_mission.html', 
                              mission=mission, 
                              now=datetime.now)
        return HTML(string=html).write_pdf()
    except Exception as e:
        logger.error(f"Erreur PDF mission: {e}")
        return generate_error_pdf(f"Erreur: {str(e)}")

def generate_attestation_travail(personnel):
    """Génère une attestation de travail"""
    try:
        html = render_template('pdf/attestation_travail.html', 
                              personnel=personnel, 
                              now=datetime.now)
        return HTML(string=html).write_pdf()
    except Exception as e:
        logger.error(f"Erreur PDF attestation: {e}")
        return generate_error_pdf(f"Erreur: {str(e)}")