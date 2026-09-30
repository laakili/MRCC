from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.personnel import Personnel
from app.models.absence import Absence
from app.models.formation import Formation
from app.models.mission import Mission
from datetime import datetime, timedelta
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Page d'accueil - redirige vers le tableau de bord ou la page de connexion"""
    print("== index  =============  Page d'accueil - redirige vers le tableau de bord ou la page de connexion")
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord principal avec statistiques"""
    
    # Calculer les statistiques
    stats = {
        'total_personnel': Personnel.query.count(),
        'personnel_actif': Personnel.query.filter_by(statut='ACTIF').count(),
        'personnel_inactif': Personnel.query.filter_by(statut='INACTIF').count(),
        
        'absences_aujourdhui': Absence.query.filter(
            Absence.date_debut <= datetime.now().date(),
            Absence.date_fin >= datetime.now().date(),
            Absence.statut == 'VALIDE'
        ).count(),
        
        'absences_en_attente': Absence.query.filter_by(statut='EN_ATTENTE').count(),
        'absences_validees': Absence.query.filter_by(statut='VALIDE').count(),
        
        'formations_planifiees': Formation.query.filter_by(statut='PLANIFIEE').count(),
        'formations_en_cours': Formation.query.filter_by(statut='EN_COURS').count(),
        'formations_terminees': Formation.query.filter_by(statut='TERMINEE').count(),
        
        'missions_en_cours': Mission.query.filter(
            Mission.date_debut <= datetime.now().date(),
            Mission.date_fin >= datetime.now().date(),
            Mission.statut.in_(['VALIDE', 'EN_COURS'])
        ).count(),
        
        'missions_soumises': Mission.query.filter_by(statut='SOUMIS').count(),
        'missions_terminees': Mission.query.filter_by(statut='TERMINE').count(),
    }
    
    # Statistiques supplémentaires
    stats['total_absences'] = Absence.query.count()
    stats['total_formations'] = Formation.query.count()
    stats['total_missions'] = Mission.query.count()
    
    # Évolution mensuelle (exemple simplifié)
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    stats['nouveaux_personnel_mois'] = Personnel.query.filter(
        db.extract('year', Personnel.date_recrutement) == current_year,
        db.extract('month', Personnel.date_recrutement) == current_month
    ).count()
    
    return render_template('dashboard.html', stats=stats)