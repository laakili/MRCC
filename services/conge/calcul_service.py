# app/services/conge/calcul_service.py
from datetime import date, timedelta
import holidays

class CalculService:
    """Service de calcul des jours de congé"""
    
    def __init__(self):
        self.jours_feries_maroc = self._get_jours_feries_maroc()
    
    def _get_jours_feries_maroc(self):
        """Liste des jours fériés au Maroc"""
        return [
            (1, 1),   # Nouvel An
            (1, 11),  # Manifeste de l'indépendance
            (5, 1),   # Fête du Travail
            (7, 30),  # Fête du Trône
            (8, 14),  # Journée Oued Ed-Dahab
            (8, 20),  # Révolution du Roi et du Peuple
            (8, 21),  # Fête de la Jeunesse
            (11, 6),  # Marche Verte
            (11, 18), # Fête de l'Indépendance
            # Les fêtes religieuses variables (à ajouter dynamiquement)
        ]
    
    def calculer_jours_ouvres(self, date_debut: date, date_fin: date, est_au_maroc: bool = True) -> dict:
        """
        Calcule le nombre de jours ouvrés entre deux dates
        Retourne: {
            'jours_total': nombre total de jours,
            'jours_ouvres': jours sans dimanches ni fériés,
            'jours_feries': nombre de jours fériés dans la période,
            'detail_jours': liste des jours exclus
        }
        """
        jours_total = (date_fin - date_debut).days + 1
        jours_ouvres = 0
        jours_feries = 0
        jours_exclus = []
        
        current = date_debut
        while current <= date_fin:
            est_ouvre = True
            raison_exclusion = None
            
            # Exclure les dimanches
            if current.weekday() == 6:  # Dimanche
                est_ouvre = False
                raison_exclusion = "Dimanche"
            
            # Exclure les jours fériés (si au Maroc)
            if est_au_maroc and self._est_jour_ferie(current):
                est_ouvre = False
                raison_exclusion = "Férié"
                jours_feries += 1
            
            if est_ouvre:
                jours_ouvres += 1
            else:
                jours_exclus.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'raison': raison_exclusion
                })
            
            current += timedelta(days=1)
        
        return {
            'jours_total': jours_total,
            'jours_ouvres': jours_ouvres,
            'jours_feries': jours_feries,
            'jours_exclus': jours_exclus
        }
    
    def _est_jour_ferie(self, date_a_verifier: date) -> bool:
        """Vérifie si une date est fériée"""
        # Vérifier dans la base de données
        from app.models.conge import JourFerie
        jour_ferie = JourFerie.query.filter(
            (JourFerie.date_ferie == date_a_verifier) |
            (JourFerie.est_recurrent == True)
        ).first()
        
        if jour_ferie:
            return True
        
        # Vérifier les dates fixes
        for mois, jour in self.jours_feries_maroc:
            if date_a_verifier.month == mois and date_a_verifier.day == jour:
                return True
        
        return False