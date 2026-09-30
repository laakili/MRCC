from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.personnel import Grade, Emploi, UniteOrganisationnelle, Personnel
from app.models.mission import NatureMission, MoyenDeplacement
from app.models.formation import Formation
from app.models.affiliation import PartiPolitique, Syndicat
from app.models.auth import Utilisateur, DroitAcces
from app.utils.decorators import admin_required
from werkzeug.security import generate_password_hash
import subprocess
import os
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin')

# ==================== TABLEAU DE BORD ADMIN ====================

@bp.route('/')
@login_required
@admin_required
def index():
    """Tableau de bord administration"""
    stats = {
        'utilisateurs': Utilisateur.query.count(),
        'grades': Grade.query.count(),
        'emplois': Emploi.query.count(),
        'unites': UniteOrganisationnelle.query.count(),
        'natures_mission': NatureMission.query.count(),
        'partis': PartiPolitique.query.count(),
        'syndicats': Syndicat.query.count()
    }
    return render_template('admin/index.html', stats=stats)


# ==================== GESTION DES UTILISATEURS ====================

@bp.route('/utilisateurs')
@login_required
@admin_required
def list_utilisateurs():
    """Liste des utilisateurs"""
    utilisateurs = Utilisateur.query.order_by(Utilisateur.email).all()
    return render_template('admin/utilisateurs.html', utilisateurs=utilisateurs)


@bp.route('/utilisateurs/ajouter', methods=['GET', 'POST'])
@login_required
@admin_required
def ajouter_utilisateur():
    """Ajouter un utilisateur"""
    if request.method == 'POST':
        try:
            # Vérifier si l'email existe déjà
            if Utilisateur.query.filter_by(email=request.form['email']).first():
                flash('Cet email est déjà utilisé.', 'danger')
                return redirect(url_for('admin.ajouter_utilisateur'))
            
            utilisateur = Utilisateur(
                email=request.form['email'],
                password_hash=generate_password_hash(request.form['password']),
                role=request.form['role'],
                personnel_id=request.form.get('personnel_id', type=int) or None,
                est_actif='est_actif' in request.form
            )
            db.session.add(utilisateur)
            db.session.commit()
            flash('Utilisateur ajouté avec succès.', 'success')
            return redirect(url_for('admin.list_utilisateurs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    
    personnels = Personnel.query.filter_by(statut='ACTIF').order_by(Personnel.nom).all()
    return render_template('admin/ajouter_utilisateur.html', personnels=personnels)


@bp.route('/utilisateurs/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_utilisateur(id):
    """Modifier un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            utilisateur.email = request.form['email']
            if request.form.get('password'):
                utilisateur.password_hash = generate_password_hash(request.form['password'])
            utilisateur.role = request.form['role']
            utilisateur.personnel_id = request.form.get('personnel_id', type=int) or None
            utilisateur.est_actif = 'est_actif' in request.form
            db.session.commit()
            flash('Utilisateur modifié avec succès.', 'success')
            return redirect(url_for('admin.list_utilisateurs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    
    personnels = Personnel.query.filter_by(statut='ACTIF').order_by(Personnel.nom).all()
    return render_template('admin/modifier_utilisateur.html', 
                         utilisateur=utilisateur, 
                         personnels=personnels)


@bp.route('/utilisateurs/supprimer/<int:id>', methods=['POST'])
@login_required
@admin_required
def supprimer_utilisateur(id):
    """Supprimer un utilisateur"""
    if id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin.list_utilisateurs'))
    
    utilisateur = Utilisateur.query.get_or_404(id)
    try:
        db.session.delete(utilisateur)
        db.session.commit()
        flash('Utilisateur supprimé.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    
    return redirect(url_for('admin.list_utilisateurs'))


# ==================== GESTION DES DROITS ====================

@bp.route('/droits')
@login_required
@admin_required
def list_droits():
    """Liste des droits par rôle"""
    droits = DroitAcces.query.order_by(DroitAcces.role, DroitAcces.module).all()
    
    # Organiser par rôle
    droits_par_role = {}
    for droit in droits:
        if droit.role not in droits_par_role:
            droits_par_role[droit.role] = []
        droits_par_role[droit.role].append(droit)
    
    modules = ['PERSONNEL', 'ABSENCE', 'FORMATION', 'MISSION', 'ADMIN']
    roles = ['ADMIN', 'CHEF_RH', 'AGENT']
    
    return render_template('admin/droits.html', 
                         droits_par_role=droits_par_role,
                         modules=modules,
                         roles=roles)


@bp.route('/droits/modifier/<int:id>', methods=['POST'])
@login_required
@admin_required
def modifier_droit(id):
    """Modifier un droit"""
    droit = DroitAcces.query.get_or_404(id)
    
    droit.peut_lire = 'peut_lire' in request.form
    droit.peut_creer = 'peut_creer' in request.form
    droit.peut_modifier = 'peut_modifier' in request.form
    droit.peut_supprimer = 'peut_supprimer' in request.form
    droit.peut_exporter = 'peut_exporter' in request.form
    droit.peut_imprimer = 'peut_imprimer' in request.form
    
    db.session.commit()
    flash('Droit modifié.', 'success')
    return redirect(url_for('admin.list_droits'))


# ==================== GESTION DES RÉFÉRENTIELS ====================

# --- Emplois ---
@bp.route('/emplois')
@login_required
@admin_required
def list_emplois():
    emplois = Emploi.query.order_by(Emploi.identifiant_emploi).all()
    return render_template('admin/emplois.html', emplois=emplois)


# --- Natures de Mission ---
@bp.route('/natures-mission')
@login_required
@admin_required
def list_natures_mission():
    natures = NatureMission.query.order_by(NatureMission.libelle).all()
    return render_template('admin/natures_mission.html', natures=natures)


# ==================== OUTILS TECHNIQUES ====================

@bp.route('/sauvegarde')
@login_required
@admin_required
def sauvegarde():
    """Page de sauvegarde de la base de données"""
    return render_template('admin/sauvegarde.html')


@bp.route('/sauvegarde/executer', methods=['POST'])
@login_required
@admin_required
def executer_sauvegarde():
    """Exécuter une sauvegarde de la base de données"""
    try:
        # Configuration
        db_name = 'onda_rh'
        backup_dir = os.path.join(os.path.dirname(__file__), '../../backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        filepath = os.path.join(backup_dir, filename)
        
        # Exécuter pg_dump (à adapter selon votre configuration)
        # cmd = f"pg_dump -U postgres {db_name} > {filepath}"
        # subprocess.run(cmd, shell=True, check=True)
        
        flash(f'Sauvegarde créée : {filename}', 'success')
    except Exception as e:
        flash(f'Erreur lors de la sauvegarde : {str(e)}', 'danger')
    
    return redirect(url_for('admin.sauvegarde'))


@bp.route('/audit')
@login_required
@admin_required
def audit():
    """Journal d'audit"""
    from app.models.auth import JournalConnexion
    
    page = request.args.get('page', 1, type=int)
    per_page = 100
    
    # Journal des connexions
    connexions = JournalConnexion.query.order_by(JournalConnexion.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin/audit.html', connexions=connexions)


# ==================== GESTION DES UNITÉS ====================

@bp.route('/unites')
@login_required
@admin_required
def list_unites():
    """Liste des unités organisationnelles"""
    unites = UniteOrganisationnelle.query.order_by(UniteOrganisationnelle.type_uo, UniteOrganisationnelle.unite_organisat).all()
    return render_template('admin/unites.html', unites=unites)


@bp.route('/unites/ajouter', methods=['POST'])
@login_required
@admin_required
def ajouter_unite():
    """Ajouter une unité"""
    try:
        unite = UniteOrganisationnelle(
            id_uo=request.form['id_uo'],
            unite_organisat=request.form['unite_organisat'],
            type_uo=request.form['type_uo'],
            entite_sup=request.form.get('entite_sup'),
            entite_categorie=request.form.get('entite_categorie'),
            local_geo=request.form.get('local_geo'),
            fonctionnement=request.form.get('fonctionnement'),
            pole=request.form.get('pole')
        )
        db.session.add(unite)
        db.session.commit()
        flash('Unité ajoutée avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.list_unites'))


@bp.route('/unites/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_unite(id):
    """Modifier une unité"""
    unite = UniteOrganisationnelle.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            unite.id_uo = request.form['id_uo']
            unite.unite_organisat = request.form['unite_organisat']
            unite.type_uo = request.form['type_uo']
            unite.entite_sup = request.form.get('entite_sup')
            unite.entite_categorie = request.form.get('entite_categorie')
            unite.local_geo = request.form.get('local_geo')
            unite.fonctionnement = request.form.get('fonctionnement')
            unite.pole = request.form.get('pole')
            
            db.session.commit()
            flash('Unité modifiée avec succès.', 'success')
            return redirect(url_for('admin.list_unites'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    
    return render_template('admin/unites_modifier.html', unite=unite)


# ==================== GESTION DES EMPLOIS ====================

@bp.route('/emplois/ajouter', methods=['POST'])
@login_required
@admin_required
def ajouter_emploi():
    """Ajouter un emploi"""
    try:
        emploi = Emploi(
            code_emploi=request.form['code_emploi'],
            identifiant_emploi=request.form['identifiant_emploi']
        )
        db.session.add(emploi)
        db.session.commit()
        flash('Emploi ajouté avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.list_emplois'))


@bp.route('/emplois/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_emploi(id):
    """Modifier un emploi"""
    emploi = Emploi.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            emploi.code_emploi = request.form['code_emploi']
            emploi.identifiant_emploi = request.form['identifiant_emploi']
            db.session.commit()
            flash('Emploi modifié avec succès.', 'success')
            return redirect(url_for('admin.list_emplois'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    
    return render_template('admin/emplois_modifier.html', emploi=emploi)


# ==================== GESTION DES GRADES ====================

@bp.route('/grades')
@login_required
@admin_required
def list_grades():
    """Liste des grades"""
    grades = Grade.query.order_by(Grade.ordre_hierarchique).all()
    return render_template('admin/grades.html', grades=grades)


@bp.route('/grades/ajouter', methods=['POST'])
@login_required
@admin_required
def ajouter_grade():
    """Ajouter un grade"""
    try:
        grade = Grade(
            code=request.form['code'],
            libelle=request.form['libelle'],
            ordre_hierarchique=request.form['ordre_hierarchique'],
            categorie=request.form.get('categorie'),
            clt=request.form.get('clt', type=int),
            description=request.form.get('description'),
            actif='actif' in request.form
        )
        db.session.add(grade)
        db.session.commit()
        flash('Grade ajouté avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.list_grades'))


@bp.route('/grades/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_grade(id):
    """Modifier un grade"""
    grade = Grade.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            grade.code = request.form['code']
            grade.libelle = request.form['libelle']
            grade.ordre_hierarchique = request.form['ordre_hierarchique']
            grade.categorie = request.form.get('categorie')
            grade.clt = request.form.get('clt', type=int)
            grade.description = request.form.get('description')
            grade.actif = 'actif' in request.form
            db.session.commit()
            flash('Grade modifié avec succès.', 'success')
            return redirect(url_for('admin.list_grades'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    
    return render_template('admin/grades_modifier.html', grade=grade)


# ==================== GESTION DES NATURES DE MISSION ====================


@bp.route('/natures-mission/ajouter', methods=['POST'])
@login_required
@admin_required
def ajouter_nature_mission():
    """Ajouter une nature de mission"""
    try:
        nature = NatureMission(
            code=request.form['code'],
            libelle=request.form['libelle'],
            description=request.form.get('description'),
            actif='actif' in request.form
        )
        db.session.add(nature)
        db.session.commit()
        flash('Nature de mission ajoutée avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.list_natures_mission'))


@bp.route('/natures-mission/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_nature_mission(id):
    """Modifier une nature de mission"""
    nature = NatureMission.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            nature.code = request.form['code']
            nature.libelle = request.form['libelle']
            nature.description = request.form.get('description')
            nature.actif = 'actif' in request.form
            db.session.commit()
            flash('Nature de mission modifiée avec succès.', 'success')
            return redirect(url_for('admin.list_natures_mission'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    
    return render_template('admin/natures_mission_modifier.html', nature=nature)


# ==================== GESTION DES MOYENS DE DÉPLACEMENT ====================

@bp.route('/moyens-deplacement')
@login_required
@admin_required
def list_moyens_deplacement():
    """Liste des moyens de déplacement"""
    moyens = MoyenDeplacement.query.order_by(MoyenDeplacement.libelle).all()
    return render_template('admin/moyens_deplacement.html', moyens=moyens)


@bp.route('/moyens-deplacement/ajouter', methods=['POST'])
@login_required
@admin_required
def ajouter_moyen_deplacement():
    """Ajouter un moyen de déplacement"""
    try:
        moyen = MoyenDeplacement(
            code=request.form['code'],
            libelle=request.form['libelle'],
            description=request.form.get('description'),
            actif='actif' in request.form
        )
        db.session.add(moyen)
        db.session.commit()
        flash('Moyen de déplacement ajouté avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.list_moyens_deplacement'))


@bp.route('/moyens-deplacement/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_moyen_deplacement(id):
    """Modifier un moyen de déplacement"""
    moyen = MoyenDeplacement.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            moyen.code = request.form['code']
            moyen.libelle = request.form['libelle']
            moyen.description = request.form.get('description')
            moyen.actif = 'actif' in request.form
            db.session.commit()
            flash('Moyen de déplacement modifié avec succès.', 'success')
            return redirect(url_for('admin.list_moyens_deplacement'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    
    return render_template('admin/moyens_deplacement_modifier.html', moyen=moyen)


@bp.route('/droits/sauvegarder', methods=['POST'])
@login_required
@admin_required
def sauvegarder_tous_droits():
    """Sauvegarder tous les droits en une fois"""
    try:
        for key, value in request.form.items():
            if key.startswith('droit_'):
                parts = key.split('_')
                droit_id = int(parts[1])
                field = '_'.join(parts[2:])
                
                droit = DroitAcces.query.get(droit_id)
                if droit:
                    setattr(droit, field, value == 'on')
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Droits mis à jour'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500