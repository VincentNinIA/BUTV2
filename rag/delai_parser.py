#!/usr/bin/env python3
"""
Parser pour les délais de réapprovisionnement
Gère les formats : "X semaines" et "X semaines après condition"
"""
import re
from datetime import datetime, timedelta
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class TypeDelai(Enum):
    STANDARD = "standard"           # "4 semaines"
    CONDITIONNEL = "conditionnel"  # "2 semaines après validation"
    INVALIDE = "invalide"          # Format non reconnu

@dataclass
class DelaiInfo:
    """Informations extraites d'un délai de livraison"""
    type_delai: TypeDelai
    nombre_semaines: int
    condition: Optional[str] = None
    texte_original: str = ""
    
    def __str__(self):
        if self.type_delai == TypeDelai.STANDARD:
            return f"{self.nombre_semaines} semaines"
        elif self.type_delai == TypeDelai.CONDITIONNEL:
            return f"{self.nombre_semaines} semaines après {self.condition}"
        else:
            return f"Format invalide: {self.texte_original}"

class DelaiParser:
    """Parser pour analyser les délais de réapprovisionnement"""
    
    def __init__(self):
        # Pattern pour format standard : "4 semaines"
        self.pattern_standard = re.compile(r'^(\d+)\s+semaines?$', re.IGNORECASE)
        
        # Pattern pour format conditionnel : "2 semaines après validation bat"
        self.pattern_conditionnel = re.compile(
            r'^(\d+)\s+semaines?\s+après\s+(.+)$', 
            re.IGNORECASE
        )
    
    def parser_delai(self, delai_text: str) -> DelaiInfo:
        """
        Parse un délai de livraison et retourne les informations structurées
        
        Args:
            delai_text: Texte du délai (ex: "4 semaines", "2 semaines après validation")
            
        Returns:
            DelaiInfo avec les informations extraites
        """
        delai_text = delai_text.strip()
        
        # Tenter le pattern standard
        match_standard = self.pattern_standard.match(delai_text)
        if match_standard:
            semaines = int(match_standard.group(1))
            return DelaiInfo(
                type_delai=TypeDelai.STANDARD,
                nombre_semaines=semaines,
                texte_original=delai_text
            )
        
        # Tenter le pattern conditionnel
        match_conditionnel = self.pattern_conditionnel.match(delai_text)
        if match_conditionnel:
            semaines = int(match_conditionnel.group(1))
            condition = match_conditionnel.group(2).strip()
            return DelaiInfo(
                type_delai=TypeDelai.CONDITIONNEL,
                nombre_semaines=semaines,
                condition=condition,
                texte_original=delai_text
            )
        
        # Format non reconnu
        return DelaiInfo(
            type_delai=TypeDelai.INVALIDE,
            nombre_semaines=0,
            texte_original=delai_text
        )
    
    def calculer_date_livraison(self, 
                               delai_info: DelaiInfo, 
                               date_commande: datetime,
                               condition_validee: bool = False) -> Tuple[Optional[datetime], str]:
        """
        Calcule la date de livraison estimée basée sur le délai
        
        Args:
            delai_info: Informations sur le délai
            date_commande: Date de la commande
            condition_validee: Pour les délais conditionnels, si la condition est remplie
            
        Returns:
            Tuple (date_livraison_estimee, statut_text)
        """
        if delai_info.type_delai == TypeDelai.INVALIDE:
            return None, f"❌ Délai invalide: {delai_info.texte_original}"
        
        if delai_info.type_delai == TypeDelai.STANDARD:
            # Calcul simple : date_commande + X semaines
            date_livraison = date_commande + timedelta(weeks=delai_info.nombre_semaines)
            return date_livraison, f"✅ Livraison estimée: {date_livraison.strftime('%d/%m/%Y')}"
        
        elif delai_info.type_delai == TypeDelai.CONDITIONNEL:
            if condition_validee:
                # La condition est remplie, on peut calculer
                date_livraison = date_commande + timedelta(weeks=delai_info.nombre_semaines)
                return date_livraison, f"✅ Livraison estimée (condition validée): {date_livraison.strftime('%d/%m/%Y')}"
            else:
                # La condition n'est pas encore remplie
                return None, f"⏳ En attente de: {delai_info.condition}"
        
        return None, "❓ Statut inconnu"
    
    def evaluer_disponibilite(self, 
                             stock_actuel: int,
                             stock_a_recevoir: int,
                             quantite_demandee: int,
                             delai_info: DelaiInfo,
                             date_commande: datetime,
                             date_livraison_souhaitee: Optional[datetime] = None) -> dict:
        """
        Évalue la disponibilité d'un produit avec gestion des ruptures
        
        Returns:
            Dict avec le statut complet de disponibilité
        """
        resultat = {
            'stock_suffisant': False,
            'type_disponibilite': '',
            'message': '',
            'date_livraison_estimee': None,
            'action_requise': '',
            'niveau_alerte': 'info'  # info, warning, error
        }
        
        # 1. Vérifier le stock actuel
        if stock_actuel >= quantite_demandee:
            resultat.update({
                'stock_suffisant': True,
                'type_disponibilite': 'immediate',
                'message': f'✅ Stock suffisant ({stock_actuel} disponibles)',
                'niveau_alerte': 'info'
            })
            return resultat
        
        # 2. Stock insuffisant, vérifier stock + commandes à recevoir
        stock_total = stock_actuel + stock_a_recevoir
        if stock_total >= quantite_demandee:
            # Calculer la date de livraison
            date_livraison, statut = self.calculer_date_livraison(delai_info, date_commande)
            
            resultat.update({
                'stock_suffisant': True,
                'type_disponibilite': 'avec_commande',
                'message': f'⚠️ Stock actuel insuffisant ({stock_actuel}) mais {stock_a_recevoir} en commande',
                'date_livraison_estimee': date_livraison,
                'niveau_alerte': 'warning'
            })
            
            # Vérifier si la date de livraison pose problème
            if date_livraison_souhaitee and date_livraison:
                if date_livraison > date_livraison_souhaitee:
                    resultat.update({
                        'niveau_alerte': 'error',
                        'message': f'🚨 Livraison trop tardive. Estimée: {date_livraison.strftime("%d/%m/%Y")}, Souhaitée: {date_livraison_souhaitee.strftime("%d/%m/%Y")}',
                        'action_requise': 'Contacter le commercial - délai dépassé'
                    })
            
            return resultat
        
        # 3. Rupture totale
        resultat.update({
            'stock_suffisant': False,
            'type_disponibilite': 'rupture',
            'message': f'🚨 RUPTURE - Stock: {stock_actuel}, À recevoir: {stock_a_recevoir}, Demandé: {quantite_demandee}',
            'niveau_alerte': 'error',
            'action_requise': 'Alerte commercial - rupture de stock'
        })
        
        return resultat

def tester_parser():
    """Fonction de test pour valider le parser"""
    print("=== TEST DU PARSER DE DÉLAIS ===\n")
    
    parser = DelaiParser()
    date_test = datetime(2024, 1, 15)  # 15 janvier 2024
    
    # Test des différents formats
    tests = [
        "4 semaines",
        "2 semaines", 
        "3 semaines",
        "2 semaines après validation bat",
        "format invalide",
        "10 semaine"  # Test singulier
    ]
    
    for delai_text in tests:
        print(f"📝 Test: '{delai_text}'")
        delai_info = parser.parser_delai(delai_text)
        print(f"   Type: {delai_info.type_delai.value}")
        print(f"   Semaines: {delai_info.nombre_semaines}")
        if delai_info.condition:
            print(f"   Condition: {delai_info.condition}")
        
        # Test calcul de date
        if delai_info.type_delai != TypeDelai.INVALIDE:
            if delai_info.type_delai == TypeDelai.CONDITIONNEL:
                # Test avec condition non validée
                date_liv, statut = parser.calculer_date_livraison(delai_info, date_test, False)
                print(f"   📅 Sans validation: {statut}")
                
                # Test avec condition validée
                date_liv, statut = parser.calculer_date_livraison(delai_info, date_test, True)
                print(f"   📅 Avec validation: {statut}")
            else:
                date_liv, statut = parser.calculer_date_livraison(delai_info, date_test)
                print(f"   📅 {statut}")
        print()
    
    # Test d'évaluation complète
    print("=== TEST D'ÉVALUATION DE DISPONIBILITÉ ===\n")
    
    scenarios = [
        {"nom": "Stock suffisant", "stock": 100, "commande": 50, "demande": 80},
        {"nom": "Stock + commandes OK", "stock": 30, "commande": 50, "demande": 70},
        {"nom": "Rupture totale", "stock": 10, "commande": 5, "demande": 50},
    ]
    
    delai_standard = parser.parser_delai("3 semaines")
    
    for scenario in scenarios:
        print(f"🔍 Scénario: {scenario['nom']}")
        resultat = parser.evaluer_disponibilite(
            scenario['stock'], 
            scenario['commande'], 
            scenario['demande'], 
            delai_standard, 
            date_test
        )
        print(f"   {resultat['message']}")
        print(f"   Niveau: {resultat['niveau_alerte']}")
        if resultat['action_requise']:
            print(f"   Action: {resultat['action_requise']}")
        print()

if __name__ == "__main__":
    tester_parser() 