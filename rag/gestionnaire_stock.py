#!/usr/bin/env python3
"""
Gestionnaire de Stock - Version unifiée avec Articles.xlsx
Suppression de la dépendance au fichier inventaire_stock.csv
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

from .delai_parser import DelaiParser, DelaiInfo, TypeDelai

@dataclass
class ProduitStock:
    """Informations complètes d'un produit en stock"""
    product_id: str
    nom: str
    quantite_stock: int
    commandes_a_livrer: int  # Commandes à livrer aux clients
    stock_a_recevoir: int    # Stock à recevoir des fournisseurs
    delai_livraison: str
    prix_achat: float
    prix_vente_conseille: float
    marge_minimum: float
    
    # Informations calculées
    delai_info: Optional[DelaiInfo] = None

@dataclass
class ResultatVerification:
    """Résultat complet de la vérification de stock"""
    produit: ProduitStock
    quantite_demandee: int
    date_commande: datetime
    date_livraison_souhaitee: Optional[datetime]
    
    # Résultats de l'analyse
    stock_suffisant: bool
    type_disponibilite: str  # 'immediate', 'avec_commande', 'rupture'
    date_livraison_estimee: Optional[datetime]
    
    # Messages et actions
    message_principal: str
    message_detaille: str
    niveau_alerte: str  # 'info', 'warning', 'error'
    action_requise: str
    
    # Indicateurs pour email commercial
    necessite_alerte_commercial: bool = False
    details_pour_commercial: Dict = None

class GestionnaireStock:
    """Gestionnaire principal pour la vérification des stocks et ruptures"""
    
    def __init__(self, chemin_excel: str = "data/Articles.xlsx"):
        """
        Initialise le gestionnaire avec le fichier Excel unifié
        
        Args:
            chemin_excel: Chemin vers le fichier Articles.xlsx
        """
        self.chemin_excel = chemin_excel
        self.delai_parser = DelaiParser()
        self.inventaire: Dict[str, ProduitStock] = {}
        self.charger_inventaire()
    
    def charger_inventaire(self):
        """Charge l'inventaire depuis le fichier Articles.xlsx avec normalisation"""
        try:
            # Charger le fichier Excel
            df = pd.read_excel(self.chemin_excel)
            
            # Nettoyer les noms des colonnes (même logique que optimized_search.py)
            df.columns = (
                df.columns
                .str.strip()
                .str.lower()
                .str.replace('é', 'e')
                .str.replace('è', 'e')
                .str.replace('ê', 'e')
                .str.replace('à', 'a')
                .str.replace('ç', 'c')
                .str.replace('°', '')
                .str.replace(' ', '_')
                .str.replace('.', '')
                .str.replace("'", '')
                .str.replace('(', '')
                .str.replace(')', '')
                .str.replace('/', '_')
            )
            
            # Renommer les colonnes selon la logique métier CORRECTE
            df.rename(columns={
                'n': 'product_id',
                'description': 'nom',
                'stock_magasin': 'quantite_stock',
                'qte_sur_commande_vente': 'commandes_alivrer',  # ✅ CORRECT: Commandes clients à livrer
                'qte_sur_commande_achat': 'stock_a_recevoir_achat',   # ✅ CORRECT: Stock fournisseurs à recevoir
                'delai_de_reappro': 'delai_livraison',
                'coût_unit_total_estime': 'prix_achat',
            }, inplace=True)
            
            # Calculer les prix de vente et marges si manquants
            if 'prix_achat' in df.columns:
                df['prix_vente_conseille'] = df['prix_achat'] * 1.15
                df['marge_minimum'] = df['prix_achat'] * 0.15
            else:
                df['prix_vente_conseille'] = 0.0
                df['marge_minimum'] = 0.0
            
            # Convertir en dictionnaire de produits
            for _, row in df.iterrows():
                # Gérer les valeurs manquantes
                try:
                    product_id_raw = row['product_id'] if 'product_id' in row else ''
                    if pd.isna(product_id_raw):
                        continue
                    product_id = str(product_id_raw).strip()
                    if not product_id or product_id == 'nan' or product_id == '':
                        continue
                    
                    nom = str(row['nom']) if 'nom' in row and pd.notna(row['nom']) else ''
                    quantite_stock = int(row['quantite_stock']) if 'quantite_stock' in row and pd.notna(row['quantite_stock']) else 0
                    commandes_alivrer = int(row['commandes_alivrer']) if 'commandes_alivrer' in row and pd.notna(row['commandes_alivrer']) else 0
                    stock_a_recevoir = int(row['stock_a_recevoir_achat']) if 'stock_a_recevoir_achat' in row and pd.notna(row['stock_a_recevoir_achat']) else 0
                    delai_livraison = str(row['delai_livraison']) if 'delai_livraison' in row and pd.notna(row['delai_livraison']) else ''
                    prix_achat = float(row['prix_achat']) if 'prix_achat' in row and pd.notna(row['prix_achat']) else 0.0
                    prix_vente_conseille = float(row['prix_vente_conseille']) if 'prix_vente_conseille' in row and pd.notna(row['prix_vente_conseille']) else 0.0
                    marge_minimum = float(row['marge_minimum']) if 'marge_minimum' in row and pd.notna(row['marge_minimum']) else 0.0
                except (KeyError, ValueError, TypeError) as e:
                    print(f"Erreur traitement ligne {product_id}: {e}")
                    continue
                
                # Parser le délai de livraison
                delai_info = self.delai_parser.parser_delai(delai_livraison)
                
                produit = ProduitStock(
                    product_id=product_id,
                    nom=nom,
                    quantite_stock=quantite_stock,
                    commandes_a_livrer=commandes_alivrer,
                    stock_a_recevoir=stock_a_recevoir,
                    delai_livraison=delai_livraison,
                    prix_achat=prix_achat,
                    prix_vente_conseille=prix_vente_conseille,
                    marge_minimum=marge_minimum,
                    delai_info=delai_info
                )
                
                # Indexer le produit avec plusieurs variantes d'ID (comme OptimizedProductSearch)
                self.inventaire[produit.product_id] = produit
                
                # Ajouter des variantes normalisées pour la recherche
                normalized_id = self._normalize_product_id(produit.product_id)
                if normalized_id != produit.product_id:
                    self.inventaire[normalized_id] = produit
                
                # Ajouter version sans espaces
                id_sans_espaces = produit.product_id.replace(' ', '')
                if id_sans_espaces != produit.product_id:
                    self.inventaire[id_sans_espaces] = produit
            
            print(f"✅ Inventaire chargé: {len(self.inventaire)} produits")
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement de l'inventaire: {e}")
            self.inventaire = {}
    
    def _normalize_product_id(self, product_id: str) -> str:
        """Normalise un ID produit (même logique que OptimizedProductSearch)"""
        import re
        return re.sub(r'\s+', ' ', product_id.strip())
    
    def verifier_produit(self, 
                        product_id: str,
                        quantite_demandee: int,
                        date_commande: Optional[datetime] = None,
                        date_livraison_souhaitee: Optional[datetime] = None) -> ResultatVerification:
        """
        Vérification complète d'un produit selon la logique métier
        
        Args:
            product_id: ID du produit à vérifier
            quantite_demandee: Quantité demandée par le client
            date_commande: Date de la commande (défaut: aujourd'hui)
            date_livraison_souhaitee: Date de livraison souhaitée par le client
        """
        if date_commande is None:
            date_commande = datetime.now()
        
        # Vérifier que le produit existe (avec normalisation des IDs comme dans OptimizedProductSearch)
        normalized_product_id = self._normalize_product_id(product_id)
        
        # Essayer plusieurs variantes de l'ID
        search_variants = [
            product_id,  # ID original
            normalized_product_id,  # ID normalisé
            product_id.strip(),  # Sans espaces début/fin
            product_id.replace(' ', ''),  # Sans espaces
        ]
        
        found_product = None
        for variant in search_variants:
            if variant in self.inventaire:
                found_product = self.inventaire[variant]
                break
        
        if found_product is None:
            return self._creer_resultat_produit_inexistant(product_id, quantite_demandee, date_commande)
        
        produit = found_product
        
        # === ÉTAPE 1: Vérification stock actuel ===
        stock_disponible = produit.quantite_stock - produit.commandes_a_livrer
        if stock_disponible >= quantite_demandee:
            return self._creer_resultat_stock_suffisant(produit, quantite_demandee, date_commande)
        
        # === ÉTAPE 2: Vérification avec stock à recevoir ===
        stock_total_futur = stock_disponible + produit.stock_a_recevoir
        if stock_total_futur >= quantite_demandee:
            return self._creer_resultat_stock_avec_reappro(
                produit, quantite_demandee, date_commande, date_livraison_souhaitee
            )
        
        # === ÉTAPE 3: Rupture totale ===
        return self._creer_resultat_rupture_totale(
            produit, quantite_demandee, date_commande, date_livraison_souhaitee
        )
    
    def _creer_resultat_produit_inexistant(self, product_id: str, quantite_demandee: int, date_commande: datetime) -> ResultatVerification:
        """Crée un résultat pour un produit inexistant"""
        produit_fictif = ProduitStock(
            product_id=product_id,
            nom="PRODUIT INEXISTANT",
            quantite_stock=0,
            commandes_a_livrer=0,
            stock_a_recevoir=0,
            delai_livraison="",
            prix_achat=0,
            prix_vente_conseille=0,
            marge_minimum=0
        )
        
        return ResultatVerification(
            produit=produit_fictif,
            quantite_demandee=quantite_demandee,
            date_commande=date_commande,
            date_livraison_souhaitee=None,
            stock_suffisant=False,
            type_disponibilite='inexistant',
            date_livraison_estimee=None,
            message_principal=f"❌ Produit {product_id} inexistant dans l'inventaire",
            message_detaille=f"Le produit {product_id} n'existe pas dans notre catalogue",
            niveau_alerte='error',
            action_requise='Vérifier la référence produit',
            necessite_alerte_commercial=True,
            details_pour_commercial={
                'type_probleme': 'produit_inexistant',
                'product_id': product_id,
                'quantite_demandee': quantite_demandee
            }
        )
    
    def _creer_resultat_stock_suffisant(self, produit: ProduitStock, quantite_demandee: int, date_commande: datetime) -> ResultatVerification:
        """Crée un résultat pour stock suffisant"""
        stock_disponible = produit.quantite_stock - produit.commandes_a_livrer
        return ResultatVerification(
            produit=produit,
            quantite_demandee=quantite_demandee,
            date_commande=date_commande,
            date_livraison_souhaitee=None,
            stock_suffisant=True,
            type_disponibilite='immediate',
            date_livraison_estimee=date_commande + timedelta(days=1),  # Livraison immédiate
            message_principal=f"✅ Stock suffisant ({stock_disponible} disponibles)",
            message_detaille=f"Produit {produit.product_id} disponible immédiatement. Stock disponible: {stock_disponible}, Demandé: {quantite_demandee}",
            niveau_alerte='info',
            action_requise='',
            necessite_alerte_commercial=False
        )
    
    def _creer_resultat_stock_avec_reappro(self, 
                                          produit: ProduitStock, 
                                          quantite_demandee: int, 
                                          date_commande: datetime,
                                          date_livraison_souhaitee: Optional[datetime]) -> ResultatVerification:
        """Crée un résultat pour stock insuffisant mais avec réapprovisionnement"""
        
        stock_disponible = produit.quantite_stock - produit.commandes_a_livrer
        stock_total_futur = stock_disponible + produit.stock_a_recevoir
        
        # Calculer la date de livraison estimée
        date_livraison_estimee = None
        if produit.delai_info:
            date_livraison_estimee, _ = self.delai_parser.calculer_date_livraison(
                produit.delai_info, date_commande
            )
        
        # Vérifier si le délai est acceptable
        delai_acceptable = True
        if date_livraison_souhaitee and date_livraison_estimee:
            delai_acceptable = date_livraison_estimee <= date_livraison_souhaitee
        
        if not delai_acceptable:
            # Délai dépassé
            message_principal = f"🚨 Délai dépassé - Livraison estimée: {date_livraison_estimee.strftime('%d/%m/%Y') if date_livraison_estimee else 'Inconnue'}"
            niveau_alerte = 'error'
            action_requise = 'Contact commercial requis - délai dépassé'
            necessite_alerte = True
        else:
            # Stock partiel avec réapprovisionnement
            message_principal = f"⚠️ Stock partiel - Réappro nécessaire (livraison {date_livraison_estimee.strftime('%d/%m/%Y') if date_livraison_estimee else 'à déterminer'})"
            niveau_alerte = 'warning'
            action_requise = 'Informer client du délai'
            necessite_alerte = False
        
        message_detaille = f"""STOCK AVEC RÉAPPROVISIONNEMENT:
  • Stock disponible: {stock_disponible}
  • Stock à recevoir: {produit.stock_a_recevoir}
  • Stock total futur: {stock_total_futur}
  • Quantité demandée: {quantite_demandee}
  • Délai de réapprovisionnement: {produit.delai_livraison}"""
        
        details_commercial = {
            'type_probleme': 'delai_livraison' if not delai_acceptable else 'stock_partiel',
            'product_id': produit.product_id,
            'nom_produit': produit.nom,
            'quantite_demandee': quantite_demandee,
            'stock_actuel': produit.quantite_stock,
            'stock_a_recevoir': produit.stock_a_recevoir,
            'stock_disponible': stock_disponible,
            'stock_total_futur': stock_total_futur,
            'date_commande': date_commande.strftime('%d/%m/%Y'),
            'date_livraison_souhaitee': date_livraison_souhaitee.strftime('%d/%m/%Y') if date_livraison_souhaitee else 'Non spécifiée',
            'date_livraison_estimee': date_livraison_estimee.strftime('%d/%m/%Y') if date_livraison_estimee else 'Inconnue',
            'delai_reappro': produit.delai_livraison
        }
        
        return ResultatVerification(
            produit=produit,
            quantite_demandee=quantite_demandee,
            date_commande=date_commande,
            date_livraison_souhaitee=date_livraison_souhaitee,
            stock_suffisant=True,  # Suffisant avec réapprovisionnement
            type_disponibilite='avec_commande',
            date_livraison_estimee=date_livraison_estimee,
            message_principal=message_principal,
            message_detaille=message_detaille,
            niveau_alerte=niveau_alerte,
            action_requise=action_requise,
            necessite_alerte_commercial=necessite_alerte,
            details_pour_commercial=details_commercial
        )

    def _creer_resultat_rupture_totale(self, 
                                      produit: ProduitStock, 
                                      quantite_demandee: int, 
                                      date_commande: datetime,
                                      date_livraison_souhaitee: Optional[datetime]) -> ResultatVerification:
        """Crée un résultat pour rupture totale"""
        
        stock_disponible = produit.quantite_stock - produit.commandes_a_livrer
        stock_total_futur = stock_disponible + produit.stock_a_recevoir
        deficit = quantite_demandee - stock_total_futur
        
        # Message principal
        message_principal = f"❌ Rupture totale: {stock_total_futur} total futur < {quantite_demandee} demandée"
        
        # Message détaillé
        message_detaille = f"""RUPTURE DE STOCK CRITIQUE:
  • Stock en magasin: {produit.quantite_stock}
  • Commandes à livrer: {produit.commandes_a_livrer}
  • Stock disponible: {stock_disponible}
  • Stock à recevoir: {produit.stock_a_recevoir}
  • Stock total futur: {stock_total_futur}
  • Quantité demandée: {quantite_demandee}
  • Déficit: {deficit}"""
        
        details_commercial = {
            'type_probleme': 'rupture_totale',
            'product_id': produit.product_id,
            'nom_produit': produit.nom,
            'quantite_demandee': quantite_demandee,
            'stock_actuel': produit.quantite_stock,
            'stock_a_recevoir': produit.stock_a_recevoir,
            'deficit': deficit,
            'date_commande': date_commande.strftime('%d/%m/%Y'),
            'date_livraison_souhaitee': date_livraison_souhaitee.strftime('%d/%m/%Y') if date_livraison_souhaitee else 'Non spécifiée',
            'delai_reappro': produit.delai_livraison
        }
        
        return ResultatVerification(
            produit=produit,
            quantite_demandee=quantite_demandee,
            date_commande=date_commande,
            date_livraison_souhaitee=date_livraison_souhaitee,
            stock_suffisant=False,
            type_disponibilite='rupture',
            date_livraison_estimee=None,
            message_principal=message_principal,
            message_detaille=message_detaille,
            niveau_alerte='error',
            action_requise='ALERTE COMMERCIAL URGENTE - Rupture de stock',
            necessite_alerte_commercial=True,
            details_pour_commercial=details_commercial
        )
    
    def verifier_commande_complete(self, lignes_commande: List[Dict]) -> Dict:
        """
        Vérifie une commande complète avec plusieurs lignes
        
        Args:
            lignes_commande: Liste de dict avec 'product_id', 'quantite', etc.
            
        Returns:
            Dict avec résumé global et détails par ligne
        """
        resultats = []
        alertes_commerciales = []
        
        for ligne in lignes_commande:
            resultat = self.verifier_produit(
                product_id=ligne['product_id'],
                quantite_demandee=ligne['quantite'],
                date_commande=ligne.get('date_commande'),
                date_livraison_souhaitee=ligne.get('date_livraison_souhaitee')
            )
            
            resultats.append(resultat)
            
            if resultat.necessite_alerte_commercial:
                alertes_commerciales.append(resultat)
        
        # Calcul du résumé global
        nb_total = len(resultats)
        nb_ok = len([r for r in resultats if r.stock_suffisant and r.niveau_alerte == 'info'])
        nb_warning = len([r for r in resultats if r.niveau_alerte == 'warning'])
        nb_error = len([r for r in resultats if r.niveau_alerte == 'error'])
        
        statut_global = 'OK' if nb_error == 0 and nb_warning == 0 else 'PROBLEMES' if nb_error == 0 else 'CRITIQUE'
        
        return {
            'statut_global': statut_global,
            'resume': {
                'total_lignes': nb_total,
                'lignes_ok': nb_ok,
                'lignes_warning': nb_warning,
                'lignes_error': nb_error
            },
            'resultats_detail': resultats,
            'alertes_commerciales': alertes_commerciales,
            'necessite_intervention': len(alertes_commerciales) > 0
        }

def tester_gestionnaire():
    """Test complet du gestionnaire de stock"""
    print("=== TEST DU GESTIONNAIRE DE STOCK ===\n")
    
    # CORRECTION: Utiliser uniquement Articles.xlsx
    gestionnaire = GestionnaireStock()
    
    # Test avec des IDs réels d'Articles.xlsx
    tests = [
        ("76000 00420000", 300, "Stock suffisant"),  # Commande normale
        ("7600005 00000000", 2000, "Rupture massive"),  # Déficit important
        ("76000 00330000", 50, "Stock limite"),  # À la limite du stock
        ("produit_inexistant", 10, "Produit inexistant")  # Produit qui n'existe pas
    ]
    
    for product_id, quantite, description in tests:
        print(f"🔍 Test: {description}")
        print(f"   Produit: {product_id}")
        print(f"   Quantité: {quantite}")
        
        resultat = gestionnaire.verifier_produit(
            product_id=product_id,
            quantite_demandee=quantite,
            date_commande=datetime.now(),
            date_livraison_souhaitee=datetime.now() + timedelta(days=7)
        )
        
        print(f"   📊 Résultat: {resultat.message_principal}")
        print(f"   🎯 Niveau: {resultat.niveau_alerte}")
        print(f"   📧 Alerte: {resultat.necessite_alerte_commercial}")
        print()
    
    print(f"✅ Gestionnaire testé avec {len(gestionnaire.inventaire)} produits chargés")
    print("✅ Test terminé avec succès !")

if __name__ == "__main__":
    tester_gestionnaire() 