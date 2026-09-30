# app/services/conge/conge_service.py
from datetime import datetime
from app.models.conge import Conge, TypeConge, MotifConge
from app.services.conge.calcul_service import CalculService
from app.services.conge.solde_service import SoldeService
from app import db

class CongeService:
    
    def __init__(self):
        self.calcul_service = CalculService()
        self.solde_service = SoldeService()
    
    def creer_demande(self, data: dict, created_by: int) -> dict:
        """
        Crée une nouvelle demande de congé
        """
        # 1. Validation des données
        erreurs = self._valider_donnees(data)
        if erreurs:
            return {'success': False, 'erreurs': erreurs}
        
        # 2. Récupérer le type de congé
        type_conge = TypeConge.query.get(data['type_conge_id'])
        
        # 3. Calculer les jours
        calcul = self.calcul_service.calculer_jours_ouvres(
            data['date_debut'],
            data['date_fin'],
            data.get('est_au_maroc', True)
        )
        
        # 4. Vérifier le solde si nécessaire
        if type_conge.deduit_du_solde:
            disponible, solde, message = self.solde_service.verifier_solde_disponible(
                data['personnel_id'],
                calcul['jours_ouvres']
            )
            if not disponible:
                return {'success': False, 'message': message}
        
        # 5. Générer un numéro de demande
        numero = self._generer_numero_demande()
        
        # 6. Créer la demande
        conge = Conge(
            numero_demande=numero,
            personnel_id=data['personnel_id'],
            type_conge_id=data['type_conge_id'],
            motif_id=data.get('motif_id'),
            motif_libre=data.get('motif_libre'),
            description=data.get('description'),
            date_debut=data['date_debut'],
            date_fin=data['date_fin'],
            jours_demandes=calcul['jours_total'],
            jours_ouvres=calcul['jours_ouvres'],
            jours_feries_deduits=calcul['jours_feries'],
            est_au_maroc=data.get('est_au_maroc', True),
            piece_jointe=data.get('piece_jointe'),
            statut='PENDING',
            created_by=created_by
        )
        
        db.session.add(conge)
        db.session.commit()
        
        return {
            'success': True,
            'conge': conge,
            'calcul': calcul,
            'message': 'Demande créée avec succès'
        }
    
    def valider_demande(self, conge_id: int, valide_par: int) -> dict:
        """
        Valide une demande de congé
        """
        conge = Conge.query.get(conge_id)
        if not conge:
            return {'success': False, 'message': 'Demande non trouvée'}
        
        if conge.statut != 'PENDING':
            return {'success': False, 'message': 'Cette demande a déjà été traitée'}
        
        type_conge = TypeConge.query.get(conge.type_conge_id)
        
        # Consommer le solde si nécessaire
        if type_conge.deduit_du_solde:
            self.solde_service.consommer_solde(
                conge.personnel_id,
                conge.jours_ouvres,
                conge.id,
                f"Congé {type_conge.libelle}"
            )
        
        conge.statut = 'APPROVED'
        conge.valide_par = valide_par
        conge.date_validation = datetime.now()
        
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Demande validée avec succès',
            'conge': conge
        }
    
    def refuser_demande(self, conge_id: int, valide_par: int, motif_refus: str) -> dict:
        """
        Refuse une demande de congé
        """
        conge = Conge.query.get(conge_id)
        if not conge:
            return {'success': False, 'message': 'Demande non trouvée'}
        
        conge.statut = 'REJECTED'
        conge.valide_par = valide_par
        conge.date_validation = datetime.now()
        conge.motif_refus = motif_refus
        
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Demande refusée',
            'conge': conge
        }
    
    def annuler_demande(self, conge_id: int, motif_annulation: str) -> dict:
        """
        Annule une demande déjà validée (rembourse les jours)
        """
        conge = Conge.query.get(conge_id)
        if not conge or conge.statut != 'APPROVED':
            return {'success': False, 'message': 'Demande non trouvée ou non validée'}
        
        type_conge = TypeConge.query.get(conge.type_conge_id)
        
        # Rembourser le solde si nécessaire
        if type_conge.deduit_du_solde:
            self.solde_service.annuler_consommation(
                conge.personnel_id,
                conge.jours_ouvres,
                conge.id,
                motif_annulation
            )
        
        conge.statut = 'CANCELLED'
        db.session.commit()
        
        return {'success': True, 'message': 'Demande annulée avec succès'}
    
    def _valider_donnees(self, data: dict) -> list:
        """Valide les données de la demande"""
        erreurs = []
        
        if data['date_fin'] < data['date_debut']:
            erreurs.append("La date de fin doit être après la date de début")
        
        # Vérifier les chevauchements
        chevauchement = Conge.query.filter(
            Conge.personnel_id == data['personnel_id'],
            Conge.statut.in_(['PENDING', 'APPROVED']),
            Conge.date_debut <= data['date_fin'],
            Conge.date_fin >= data['date_debut']
        ).first()
        
        if chevauchement:
            erreurs.append("Une demande existe déjà sur cette période")
        
        return erreurs
    
    def _generer_numero_demande(self) -> str:
        """Génère un numéro de demande unique"""
        from datetime import datetime
        import random
        import string
        
        date_str = datetime.now().strftime('%Y%m')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"CONGE-{date_str}-{random_str}"