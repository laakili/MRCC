# app/services/conge/solde_service.py
from datetime import date
from app.models.conge import SoldeConge, HistoriqueSolde
from app import db

class SoldeService:
    """Service de gestion des soldes de congés"""
    
    SOLDE_ANNUEL_DEFAULT = 30
    
    def get_or_create_solde(self, personnel_id: int, annee: int = None) -> SoldeConge:
        """Récupère ou crée le solde pour une année donnée"""
        if annee is None:
            annee = date.today().year
        
        solde = SoldeConge.query.filter_by(
            personnel_id=personnel_id,
            annee=annee
        ).first()
        
        if not solde:
            # Créer le solde pour l'année
            solde = SoldeConge(
                personnel_id=personnel_id,
                annee=annee,
                jours_acquis=self.SOLDE_ANNUEL_DEFAULT,
                solde_initial=self.SOLDE_ANNUEL_DEFAULT,
                solde_actuel=self.SOLDE_ANNUEL_DEFAULT
            )
            db.session.add(solde)
            db.session.commit()
        
        return solde
    
    def verifier_solde_disponible(self, personnel_id: int, jours_demandes: float, annee: int = None) -> tuple:
        """
        Vérifie si le solde est suffisant
        Retourne: (disponible, solde_actuel, message)
        """
        if annee is None:
            annee = date.today().year
        
        solde = self.get_or_create_solde(personnel_id, annee)
        
        if solde.solde_actuel >= jours_demandes:
            return True, solde.solde_actuel, "Solde suffisant"
        else:
            return False, solde.solde_actuel, f"Solde insuffisant: {solde.solde_actuel} jours disponibles"
    
    def consommer_solde(self, personnel_id: int, jours: float, reference_id: int, motif: str) -> bool:
        """Consomme des jours du solde"""
        annee = date.today().year
        solde = self.get_or_create_solde(personnel_id, annee)
        
        ancien_solde = solde.solde_actuel
        solde.solde_actuel -= jours
        solde.jours_consommes += jours
        
        # Enregistrer dans l'historique
        historique = HistoriqueSolde(
            personnel_id=personnel_id,
            solde_id=solde.id,
            type_mouvement='CONSOMMATION',
            montant=jours,
            ancien_solde=ancien_solde,
            nouveau_solde=solde.solde_actuel,
            reference_id=reference_id,
            reference_type='CONGE',
            motif=motif
        )
        db.session.add(historique)
        db.session.commit()
        
        return True
    
    def annuler_consommation(self, personnel_id: int, jours: float, reference_id: int, motif: str) -> bool:
        """Annule une consommation (rembourse les jours)"""
        annee = date.today().year
        solde = self.get_or_create_solde(personnel_id, annee)
        
        ancien_solde = solde.solde_actuel
        solde.solde_actuel += jours
        solde.jours_consommes -= jours
        
        historique = HistoriqueSolde(
            personnel_id=personnel_id,
            solde_id=solde.id,
            type_mouvement='ANNULATION',
            montant=jours,
            ancien_solde=ancien_solde,
            nouveau_solde=solde.solde_actuel,
            reference_id=reference_id,
            reference_type='CONGE',
            motif=motif
        )
        db.session.add(historique)
        db.session.commit()
        
        return True
    
    def effectuer_report_annuel(self, personnel_id: int, annee_source: int, annee_cible: int) -> dict:
        """
        Reporte les jours non consommés d'une année à l'autre
        """
        solde_source = self.get_or_create_solde(personnel_id, annee_source)
        solde_cible = self.get_or_create_solde(personnel_id, annee_cible)
        
        jours_reportes = solde_source.solde_actuel
        
        # Mettre à jour le solde source
        ancien_source = solde_source.solde_actuel
        solde_source.jours_reportes += jours_reportes
        solde_source.solde_actuel = 0
        
        # Mettre à jour le solde cible
        ancien_cible = solde_cible.solde_actuel
        solde_cible.jours_reportes += jours_reportes
        solde_cible.solde_actuel += jours_reportes
        
        # Historique pour la source
        hist_source = HistoriqueSolde(
            personnel_id=personnel_id,
            solde_id=solde_source.id,
            type_mouvement='REPORT',
            montant=-jours_reportes,
            ancien_solde=ancien_source,
            nouveau_solde=0,
            reference_type='REPORT_ANNUEL',
            motif=f"Report vers {annee_cible}"
        )
        
        # Historique pour la cible
        hist_cible = HistoriqueSolde(
            personnel_id=personnel_id,
            solde_id=solde_cible.id,
            type_mouvement='REPORT',
            montant=jours_reportes,
            ancien_solde=ancien_cible,
            nouveau_solde=solde_cible.solde_actuel,
            reference_type='REPORT_ANNUEL',
            motif=f"Report de {annee_source}"
        )
        
        db.session.add_all([hist_source, hist_cible])
        db.session.commit()
        
        return {
            'personnel_id': personnel_id,
            'annee_source': annee_source,
            'annee_cible': annee_cible,
            'jours_reportes': jours_reportes
        }