#!/usr/bin/env python3
"""
Extracteur de produits et quantités optimisé
==========================================

Module unifié pour l'extraction des informations de commande depuis le texte utilisateur.
Combine la vérification par ID exact (prioritaire) avec l'extraction par nom et patterns.
"""

import re
import logging
import pandas as pd
from typing import Optional, Tuple
from rag.optimized_search import OptimizedProductSearch
from .text_extractor import normalize_text, extract_price_from_message

logger = logging.getLogger(__name__)

class ProductParser:
    """Classe pour l'extraction optimisée de produits et quantités"""
    
    def __init__(self, inventory_df: pd.DataFrame = None):
        """
        Initialise le parser avec l'inventaire
        
        Args:
            inventory_df: DataFrame de l'inventaire (optionnel)
        """
        self.inventory_df = inventory_df
        self.product_search = OptimizedProductSearch() if inventory_df is None else None
        
    def extract_product_info(self, message: str) -> Tuple[Optional[str], Optional[int], Optional[float]]:
        """
        Extrait les informations de produit avec vérification par ID exact en priorité
        
        Args:
            message: Message utilisateur
            
        Returns:
            tuple: (product_id, quantity, proposed_price)
        """
        logger.info(f"🔍 Extraction depuis : {message[:100]}...")
        
        # Étape 1: Extraction du prix (pour nettoyer le message)
        proposed_price = extract_price_from_message(message)
        if proposed_price:
            # Nettoyer le prix du message pour ne pas interférer
            message = self._clean_price_from_message(message)
        
        # Étape 2: Tentative par ID exact (PRIORITAIRE)
        product_id = self._extract_by_exact_id(message)
        
        if product_id:
            logger.info(f"✅ Produit trouvé par ID exact : {product_id}")
            quantity = self._extract_quantity_from_message(message)
            return product_id, quantity, proposed_price
        
        # Étape 3: Fallback par recherche dans l'inventaire
        logger.info("🔍 Recherche par nom de produit dans le message...")
        if self.inventory_df is not None:
            product_id = self._extract_by_product_name(message)
            if product_id:
                quantity = self._extract_quantity_from_message(message)
                logger.info(f"✅ Produit trouvé par nom : {product_id}")
                return product_id, quantity, proposed_price
        
        logger.warning("❌ Aucune extraction réussie")
        quantity = self._extract_quantity_from_message(message)  # Au moins essayer d'extraire la quantité
        return None, quantity, proposed_price
    
    def _extract_by_exact_id(self, message: str) -> Optional[str]:
        """
        Tentative 1: Recherche par ID exact au début du message
        Format attendu : "76000 00420000" ou similaire
        """
        # Pattern pour ID exact au début
        id_pattern = r'^(\d{5,7})\s+(\d{8})\b'
        
        match = re.search(id_pattern, message)
        if match:
            test_id = f"{match.group(1)} {match.group(2)}"
            
            # Vérifier si ce produit existe
            if self.product_search and self.product_search.get_product_info(test_id):
                return test_id
            elif self.inventory_df is not None:
                # Fallback sur inventory_df si product_search n'est pas disponible
                if 'product_id' in self.inventory_df.columns:
                    if test_id in self.inventory_df['product_id'].values:
                        return test_id
        
        # Patterns généraux pour ID dans le message
        general_patterns = [
            r'\b(\d{7})\s+(\d{8})\b',    # "7600005 00000000"
            r'\b(\d{5})\s+(\d{8})\b',    # "76000 00420000"
        ]
        
        for pattern in general_patterns:
            matches = re.findall(pattern, message)
            if matches:
                test_id = f"{matches[0][0]} {matches[0][1]}"
                
                if self.product_search and self.product_search.get_product_info(test_id):
                    return test_id
                elif self.inventory_df is not None and 'product_id' in self.inventory_df.columns:
                    if test_id in self.inventory_df['product_id'].values:
                        return test_id
        
        return None
    
    def _extract_by_product_name(self, message: str) -> Optional[str]:
        """
        Recherche par nom de produit dans l'inventaire
        """
        if self.inventory_df is None:
            return None
            
        normalized_message = normalize_text(message).lower()
        
        # Préparer la colonne nom_normalise si elle n'existe pas
        if 'nom_normalise' not in self.inventory_df.columns:
            self.inventory_df['nom_normalise'] = self.inventory_df['nom'].apply(normalize_text)
        
        # Recherche par nom
        for _, row in self.inventory_df.iterrows():
            if row['nom_normalise'].lower() in normalized_message:
                return row.get('product_id', row['nom'])
                
        return None
    
    def _extract_quantity_from_message(self, message: str) -> Optional[int]:
        """Extrait la quantité d'un message"""
        # Patterns par priorité
        patterns = [
            r'[Qq]té\s+(\d+)',           # "Qté 300"
            r'[Qq]uantité\s*:?\s*(\d+)', # "Quantité : 300" 
            r'(\d+)\s+unités?',          # "300 unités"
            r'(\d+)\s+pièces?',          # "300 pièces"
            r'(\d+)\s+(?:caisses?|boites?|rouleaux?|sacs?)', # "300 caisses"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _clean_price_from_message(self, message: str) -> str:
        """Nettoie les expressions de prix du message"""
        # Patterns pour nettoyer le prix
        price_patterns = [
            r'[Pp]rix\s*:\s*\d+(?:[,.]?\d+)?€?',    # "Prix : 1€"
            r'à\s+\d+(?:[,.]?\d+)?€',               # "à 8€"
            r'\d+(?:[,.]?\d+)?€',                   # "1€"
        ]
        
        cleaned_message = message
        for pattern in price_patterns:
            cleaned_message = re.sub(pattern, '', cleaned_message)
        
        # Nettoyer les espaces multiples
        cleaned_message = re.sub(r'\s+', ' ', cleaned_message).strip()
        return cleaned_message

    def debug_extraction(self, message: str) -> dict:
        """
        Version debug pour voir toutes les étapes d'extraction
        Utile pour identifier où ça plante ! 
        """
        debug_info = {
            "message_original": message,
            "price_found": None,
            "message_after_price_cleaning": None,
            "exact_id_found": None,
            "product_name_found": None,
            "quantity_found": None,
            "final_result": None
        }
        
        try:
            # Étape 1: Prix
            debug_info["price_found"] = extract_price_from_message(message)
            debug_info["message_after_price_cleaning"] = self._clean_price_from_message(message)
            
            # Étape 2: ID exact
            debug_info["exact_id_found"] = self._extract_by_exact_id(message)
            
            # Étape 3: Nom produit
            if not debug_info["exact_id_found"]:
                debug_info["product_name_found"] = self._extract_by_product_name(message)
            
            # Étape 4: Quantité
            debug_info["quantity_found"] = self._extract_quantity_from_message(message)
            
            # Résultat final
            product_id = debug_info["exact_id_found"] or debug_info["product_name_found"]
            debug_info["final_result"] = (
                product_id, 
                debug_info["quantity_found"], 
                debug_info["price_found"]
            )
            
        except Exception as e:
            debug_info["error"] = str(e)
            logger.error(f"Erreur dans debug_extraction: {e}")
        
        return debug_info 