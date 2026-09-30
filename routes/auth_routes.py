from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models.auth import Utilisateur, JournalConnexion
from app import db
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    print("Page de connexion    /login   ")
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = Utilisateur.query.filter_by(email=email).first()
        
        # Journaliser la tentative
        journal = JournalConnexion(
            email=email,
            action='ECHEC',
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        if user and check_password_hash(user.password_hash, password):
            if user.est_actif:
                login_user(user, remember=remember)
                user.derniere_connexion = datetime.now()
                
                # Mettre à jour le journal
                journal.utilisateur_id = user.id
                journal.action = 'CONNEXION'
                db.session.add(journal)
                db.session.commit()
                
                next_page = request.args.get('next')
                flash('Connexion réussie.', 'success')
                return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
            else:
                flash('Votre compte est désactivé. Contactez l\'administrateur.', 'danger')
        else:
            flash('Email ou mot de passe incorrect.', 'danger')
        
        db.session.add(journal)
        db.session.commit()
    
    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    journal = JournalConnexion(
        utilisateur_id=current_user.id,
        email=current_user.email,
        action='DECONNEXION',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(journal)
    db.session.commit()
    
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/profil')
@login_required
def profil():
    """Profil de l'utilisateur"""
    return render_template('auth/profil.html')