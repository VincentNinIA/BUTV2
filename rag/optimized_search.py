#!/usr/bin/env python3
"""
Module de recherche optimisée par ID avec cache et parser de commandes.
Optimisé pour les IDs composés de 2 parties avec espaces (ex: "76000 00420000").
"""

import pandas as pd
import re
import os
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache
import time

class OptimizedProductSearch:
    """Classe pour la recherche optimisée de produits par ID"""
    
    def __init__(self, excel_file_path: str = "data/Articles.xlsx"):
        """
        Initialise la recherche optimisée
        
        Args:
            excel_file_path: Chemin vers le fichier Excel
        """
        self.excel_file_path = excel_file_path
        self.df = None
        self.id_index = {}  # Index trié par ID pour recherche rapide
        self.cache = {}  # Cache des recherches récentes
        self.cache_max_size = 1000
        self.load_data()
        
    def load_data(self):
        """Charge les données et crée l'index optimisé"""
        try:
            # Charger le fichier Excel
            self.df = pd.read_excel(self.excel_file_path)
            
            # Nettoyer les noms des colonnes
            self.df.columns = (
                self.df.columns
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
            self.df.rename(columns={
                'n': 'product_id',
                'description': 'nom',
                'stock_magasin': 'quantite_stock',
                'qte_sur_commande_vente': 'commandes_alivrer',  # ✅ CORRECT: Commandes clients à livrer
                'qte_sur_commande_achat': 'stock_a_recevoir_achat',  # ✅ CORRECT: Stock fournisseurs à recevoir
                'delai_de_reappro': 'delai_livraison',
                'coût_unit_total_estime': 'prix_achat',
            }, inplace=True)
            
            # Calculer les prix de vente et marges
            if 'prix_achat' in self.df.columns:
                self.df['prix_vente_conseille'] = self.df['prix_achat'] * 1.15
                self.df['marge_minimum'] = self.df['prix_achat'] * 0.15
            else:
                self.df['prix_vente_conseille'] = 0.0
                self.df['marge_minimum'] = 0.0
            
            # Créer l'index par ID
            self._create_id_index()
            
            print(f"✅ Données chargées: {len(self.df)} produits indexés")
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement: {e}")
            self.df = pd.DataFrame()
    
    def _create_id_index(self):
        """Crée un index optimisé par ID pour recherche rapide"""
        self.id_index = {}
        
        if 'product_id' in self.df.columns:
            for idx, row in self.df.iterrows():
                product_id = str(row['product_id']).strip()
                
                # Normaliser l'ID (supprimer espaces multiples)
                normalized_id = self._normalize_id(product_id)
                
                # Indexer par ID original et normalisé
                self.id_index[product_id] = idx
                self.id_index[normalized_id] = idx
                
                # Indexer aussi sans espaces pour recherche flexible
                id_sans_espaces = product_id.replace(' ', '')
                self.id_index[id_sans_espaces] = idx
    
    def _normalize_id(self, product_id: str) -> str:
        """Normalise un ID produit (espaces multiples -> simple)"""
        return re.sub(r'\s+', ' ', product_id.strip())
    
    def search_by_id(self, product_id: str) -> Optional[pd.Series]:
        """
        Recherche un produit par ID avec cache
        
        Args:
            product_id: ID du produit à rechercher
            
        Returns:
            pd.Series du produit ou None si non trouvé
        """
        # Vérifier le cache
        if product_id in self.cache:
            return self.cache[product_id]
        
        # Recherche dans l'index
        result = self._search_in_index(product_id)
        
        # Mettre en cache si trouvé
        if result is not None:
            self._add_to_cache(product_id, result)
        
        return result
    
    def _search_in_index(self, product_id: str) -> Optional[pd.Series]:
        """Recherche dans l'index avec différentes stratégies"""
        search_variants = [
            product_id,  # ID original
            product_id.strip(),  # ID sans espaces début/fin
            self._normalize_id(product_id),  # ID normalisé
            product_id.replace(' ', ''),  # ID sans espaces
            product_id.replace('   ', ' '),  # Espaces multiples -> simple
        ]
        
        for variant in search_variants:
            if variant in self.id_index:
                idx = self.id_index[variant]
                return self.df.iloc[idx]
        
        return None
    
    def _add_to_cache(self, key: str, value: pd.Series):
        """Ajoute un élément au cache avec gestion de la taille"""
        if len(self.cache) >= self.cache_max_size:
            # Supprimer le plus ancien (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = value
    
    def get_product_info(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations complètes d'un produit
        
        Args:
            product_id: ID du produit
            
        Returns:
            Dictionnaire avec les informations du produit
        """
        product = self.search_by_id(product_id)
        if product is None:
            return None
        
        # Calculer le stock disponible avec la logique métier CORRECTE
        stock_magasin = int(product.get('quantite_stock', 0))
        commandes_a_livrer = int(product.get('commandes_alivrer', 0))  # ✅ Commandes clients à livrer (SOUSTRAIRE)
        stock_a_recevoir = int(product.get('stock_a_recevoir_achat', 0))  # ✅ Stock fournisseurs à recevoir (AJOUTER)
        stock_disponible = stock_magasin + stock_a_recevoir - commandes_a_livrer
        
        return {
            'product_id': product.get('product_id', ''),
            'nom': product.get('nom', ''),
            'stock_magasin': stock_magasin,
            'commandes_a_livrer': commandes_a_livrer,  # ✅ Commandes clients à livrer
            'stock_a_recevoir': stock_a_recevoir,     # ✅ Stock fournisseurs à recevoir
            'stock_disponible': stock_disponible,
            'prix_achat': float(product.get('prix_achat', 0)),
            'prix_vente_conseille': float(product.get('prix_vente_conseille', 0)),
            'marge_minimum': float(product.get('marge_minimum', 0)),
            'delai_livraison': product.get('delai_livraison', 'N/A'),
            'stock_suffisant': stock_disponible > 0,
            'marge_ok': (float(product.get('prix_vente_conseille', 0)) - float(product.get('prix_achat', 0))) >= float(product.get('marge_minimum', 0))
        }
    
    def clear_cache(self):
        """Vide le cache"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retourne les statistiques du cache"""
        return {
            'cache_size': len(self.cache),
            'cache_max_size': self.cache_max_size,
            'index_size': len(self.id_index)
        }


class CommandeParser:
    """Parser intelligent pour les commandes"""
    
    def __init__(self, search_engine: OptimizedProductSearch):
        self.search_engine = search_engine
        
    def parse_ligne_commande(self, ligne: str) -> Optional[Dict[str, Any]]:
        """
        Parse une ligne de commande au format:
        "76000 00420000 CAISSE US SC 450X300X230MM Qté 300 Prix : 0,7€"
        
        Args:
            ligne: Ligne de commande à parser
            
        Returns:
            Dictionnaire avec les informations parsées ou None si erreur
        """
        ligne = ligne.strip()
        
        # Patterns pour différents formats (ID composé corrigé)
        patterns = [
            # Format principal avec ID composé: "76000 00420000 DESCRIPTION Qté QUANTITE Prix : PRIX€"
            r'^(\d+\s+\d+)\s+([A-Za-z\s\d\-/\(\)\.]+?)\s+Qté\s+(\d+)\s+Prix\s*:\s*([\d,\.]+)€?$',
            # Format avec ID alphanumérique composé: "760001C 00010000 DESCRIPTION Qté QUANTITE Prix : PRIX€"
            r'^(\w+\s+\d+)\s+([A-Za-z\s\d\-/\(\)\.]+?)\s+Qté\s+(\d+)\s+Prix\s*:\s*([\d,\.]+)€?$',
            # Format alternatif sans deux-points: "ID_COMPOSE DESCRIPTION Qté QUANTITE Prix PRIX€"
            r'^(\d+\s+\d+)\s+([A-Za-z\s\d\-/\(\)\.]+?)\s+Qté\s+(\d+)\s+Prix\s+([\d,\.]+)€?$',
            # Format avec ID simple: "76000 DESCRIPTION Qté QUANTITE Prix : PRIX€"
            r'^(\d+\w*)\s+([A-Za-z\s\d\-/\(\)\.]+?)\s+Qté\s+(\d+)\s+Prix\s*:\s*([\d,\.]+)€?$',
            # Format minimal: "ID DESCRIPTION QUANTITE PRIX"
            r'^(\w+\s*\w*)\s+([A-Za-z\s\d\-/\(\)\.]+?)\s+(\d+)\s+([\d,\.]+)€?$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, ligne)
            if match:
                try:
                    # Extraire les groupes
                    id_produit = match.group(1).strip()
                    designation = match.group(2).strip()
                    quantite = int(match.group(3))
                    prix_str = match.group(4).replace(',', '.')
                    prix = float(prix_str)
                    
                    # Rechercher le produit dans l'inventaire
                    product_info = self.search_engine.get_product_info(id_produit)
                    
                    result = {
                        'id_produit': id_produit,
                        'designation': designation,
                        'quantite': quantite,
                        'prix_unitaire': prix,
                        'prix_total': prix * quantite,
                        'parsing_success': True,
                        'product_found': product_info is not None
                    }
                    
                    if product_info:
                        result.update({
                            'product_info': product_info,
                            'stock_suffisant': product_info['stock_disponible'] >= quantite,
                            'marge_proposee': prix - product_info['prix_achat'],
                            'marge_ok': prix >= (product_info['prix_achat'] + product_info['marge_minimum']),
                            'prix_conseille': product_info['prix_vente_conseille']
                        })
                    
                    return result
                    
                except (ValueError, IndexError) as e:
                    print(f"❌ Erreur parsing valeurs: {e}")
                    continue
        
        return {
            'ligne_originale': ligne,
            'parsing_success': False,
            'erreur': 'Format de commande non reconnu'
        }
    
    def parse_commande_complete(self, commande_text: str) -> Dict[str, Any]:
        """
        Parse une commande complète avec plusieurs lignes
        
        Args:
            commande_text: Texte de la commande complète
            
        Returns:
            Dictionnaire avec toutes les lignes parsées
        """
        lignes = [ligne.strip() for ligne in commande_text.split('\n') if ligne.strip()]
        
        result = {
            'lignes_parsees': [],
            'total_lignes': len(lignes),
            'lignes_valides': 0,
            'lignes_invalides': 0,
            'total_quantite': 0,
            'total_prix': 0.0,
            'produits_non_trouves': [],
            'stocks_insuffisants': [],
            'marges_insuffisantes': []
        }
        
        for i, ligne in enumerate(lignes):
            ligne_parsed = self.parse_ligne_commande(ligne)
            ligne_parsed['numero_ligne'] = i + 1
            
            result['lignes_parsees'].append(ligne_parsed)
            
            if ligne_parsed['parsing_success']:
                result['lignes_valides'] += 1
                result['total_quantite'] += ligne_parsed['quantite']
                result['total_prix'] += ligne_parsed['prix_total']
                
                if not ligne_parsed['product_found']:
                    result['produits_non_trouves'].append(ligne_parsed['id_produit'])
                elif ligne_parsed['product_found'] and not ligne_parsed.get('stock_suffisant', False):
                    result['stocks_insuffisants'].append(ligne_parsed['id_produit'])
                elif ligne_parsed['product_found'] and not ligne_parsed.get('marge_ok', False):
                    result['marges_insuffisantes'].append(ligne_parsed['id_produit'])
            else:
                result['lignes_invalides'] += 1
        
        return result


# Instance globale pour utilisation dans l'application
_search_engine = OptimizedProductSearch()
_parser = CommandeParser(_search_engine)

def search_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Interface simple pour rechercher un produit par ID"""
    return _search_engine.get_product_info(product_id)

def parse_commande(commande_text: str) -> Dict[str, Any]:
    """Interface simple pour parser une commande"""
    return _parser.parse_commande_complete(commande_text)

def get_search_stats() -> Dict[str, int]:
    """Retourne les statistiques de recherche"""
    return _search_engine.get_cache_stats()

# Test si exécuté directement
if __name__ == "__main__":
    # Test de la recherche
    print("🔍 Test de recherche par ID:")
    product = search_product_by_id("76000 00420000")
    if product:
        print(f"✅ Produit trouvé: {product['nom']}")
        print(f"📦 Stock: {product['stock_disponible']}")
        print(f"💰 Prix: {product['prix_vente_conseille']:.2f}€")
    else:
        print("❌ Produit non trouvé")
    
    print("\n🔍 Test de parsing de commande:")
    commande = "76000 00420000 CAISSE US SC 450X300X230MM Qté 300 Prix : 0,7€"
    result = parse_commande(commande)
    print(f"✅ Parsing réussi: {result['lignes_valides']}/{result['total_lignes']} lignes")
    print(f"💰 Total: {result['total_prix']:.2f}€")
    
    print(f"\n📊 Stats: {get_search_stats()}") 