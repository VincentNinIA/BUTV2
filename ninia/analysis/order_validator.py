#!/usr/bin/env python3
"""
Validateur de commandes
======================

Module responsable de la validation complète des commandes :
- Vérification de l'existence du produit
- Validation des stocks disponibles
- Calcul et vérification des marges
- Analyse de faisabilité globale
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from rag.retrieval import fetch_docs
from rag.optimized_search import OptimizedProductSearch

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Résultat de validation d'une commande"""
    status: str  # "OK", "ATTENTION", "REFUSED", "ERROR"
    message: str
    product_id: Optional[str] = None
    product_info: Optional[Dict] = None
    analysis: Optional[Dict] = None
    alternatives: Optional[list] = None
    selection_llm: Optional[Dict] = None
    substitution_effective: bool = False
    
class OrderValidator:
    """Classe pour valider les commandes de façon modulaire"""
    
    def __init__(self):
        """Initialise le validateur"""
        self.product_search = OptimizedProductSearch()
        
    def validate_order(
        self, 
        product_id: str, 
        quantity: int, 
        proposed_price: Optional[float] = None
    ) -> ValidationResult:
        """
        Valide une commande complète
        
        Args:
            product_id: ID ou nom du produit
            quantity: Quantité demandée
            proposed_price: Prix proposé (optionnel)
            
        Returns:
            ValidationResult: Résultat complet de la validation
        """
        logger.info(f"🔍 Validation commande : {quantity}x {product_id} @ {proposed_price}€")
        
        try:
            # Étape 1: Vérifier l'existence du produit
            if not self._product_exists(product_id):
                return ValidationResult(
                    status="ERROR",
                    message=f"❌ Produit '{product_id}' non trouvé dans l'inventaire",
                    product_id=product_id
                )
            
            # Étape 2: Récupérer les informations détaillées via fetch_docs
            query = f"Commande de {quantity} {product_id}"
            if proposed_price:
                query += f" à {proposed_price} euros"
                
            result = fetch_docs(
                query=query,
                product_id=product_id,
                required_qty=quantity,
                prix_propose=proposed_price
            )
            
            if not result or not result.get("produit"):
                return ValidationResult(
                    status="ERROR",
                    message=f"❌ Impossible de récupérer les informations pour '{product_id}'",
                    product_id=product_id
                )
            
            product_info = result["produit"]
            alternatives = result.get("alternatives", [])
            
            # Étape 3: Analyser la faisabilité
            analysis = self._analyze_feasibility(product_info, quantity, proposed_price)
            
            # Étape 4: Déterminer le statut final
            status, message = self._determine_status(product_id, analysis, product_info)
            
            return ValidationResult(
                status=status,
                message=message,
                product_id=product_id,
                product_info=product_info,
                analysis=analysis,
                alternatives=alternatives
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la validation : {str(e)}")
            return ValidationResult(
                status="ERROR",
                message=f"❌ Erreur lors de la validation : {str(e)}",
                product_id=product_id
            )
    
    def _product_exists(self, product_id: str) -> bool:
        """Vérifie si un produit existe"""
        try:
            product_info = self.product_search.get_product_info(product_id)
            return product_info is not None
        except Exception as e:
            logger.warning(f"⚠️ Erreur vérification existence produit : {e}")
            return False
    
    def _analyze_feasibility(
        self, 
        product_info: Dict, 
        quantity: int, 
        proposed_price: Optional[float]
    ) -> Dict[str, Any]:
        """
        Analyse la faisabilité de la commande
        
        Args:
            product_info: Informations du produit
            quantity: Quantité demandée
            proposed_price: Prix proposé
            
        Returns:
            Dict: Analyse détaillée
        """
        # Récupération des données de base
        stock_disponible = product_info.get('stock_disponible', 0)
        prix_achat = product_info.get('prix_achat', 0)
        marge_minimum = product_info.get('marge_minimum', 0)
        prix_vente_conseille = product_info.get('prix_vente_conseille', 0)
        
        # Analyse du stock
        stock_suffisant = stock_disponible >= quantity
        
        # Analyse de la marge
        if proposed_price is not None:
            prix_final = proposed_price
            marge_actuelle = proposed_price - prix_achat
        else:
            prix_final = prix_vente_conseille
            marge_actuelle = prix_vente_conseille - prix_achat
            
        marge_suffisante = marge_actuelle >= marge_minimum
        
        # Analyse des délais (par défaut compatible)
        delai_compatible = True
        
        return {
            "quantite_demandee": quantity,
            "stock_disponible": stock_disponible,
            "stock_suffisant": stock_suffisant,
            "prix_final": prix_final,
            "prix_achat": prix_achat,
            "marge_actuelle": marge_actuelle,
            "marge_minimum": marge_minimum,
            "marge_suffisante": marge_suffisante,
            "delai_compatible": delai_compatible,
            "delai_dispo": product_info.get('delai', 'standard'),
            "prix_propose_retenu": proposed_price
        }
    
    def _determine_status(
        self, 
        product_id: str, 
        analysis: Dict, 
        product_info: Dict
    ) -> tuple[str, str]:
        """
        Détermine le statut final et le message
        
        Args:
            product_id: ID du produit
            analysis: Analyse de faisabilité
            product_info: Informations produit
            
        Returns:
            tuple: (status, message)
        """
        stock_suffisant = analysis["stock_suffisant"]
        marge_suffisante = analysis["marge_suffisante"]
        stock_disponible = analysis["stock_disponible"]
        quantite_demandee = analysis["quantite_demandee"]
        marge_actuelle = analysis["marge_actuelle"]
        marge_minimum = analysis["marge_minimum"]
        prix_final = analysis["prix_final"]
        
        # Logique de statut : signaler TOUS les problèmes
        if not stock_suffisant and not marge_suffisante:
            status = "REFUSED"
            message = f"❌ {product_id} : REFUSÉ - Stock insuffisant ({stock_disponible}/{quantite_demandee}) ET Marge insuffisante ({marge_actuelle:.2f}€ < {marge_minimum:.2f}€)"
        elif not stock_suffisant:
            status = "ATTENTION"
            message = f"⚠️ {product_id} : STOCK INSUFFISANT - Disponible: {stock_disponible}, demandé: {quantite_demandee}"
        elif not marge_suffisante:
            status = "REFUSED"
            message = f"❌ {product_id} : REFUSÉ - Marge insuffisante (actuelle: {marge_actuelle:.2f}€, minimum: {marge_minimum:.2f}€)"
        else:
            status = "OK"
            message = f"✅ {product_id} : OK - Quantité: {quantite_demandee}, Prix: {prix_final:.2f}€"
        
        return status, message
        
    def debug_validation(
        self, 
        product_id: str, 
        quantity: int, 
        proposed_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Version debug pour voir toutes les étapes de validation
        Parfait pour identifier où ça plante !
        """
        debug_info = {
            "input": {
                "product_id": product_id,
                "quantity": quantity,
                "proposed_price": proposed_price
            },
            "steps": {},
            "final_result": None,
            "error": None
        }
        
        try:
            # Étape 1: Existence produit
            debug_info["steps"]["product_exists"] = self._product_exists(product_id)
            
            if not debug_info["steps"]["product_exists"]:
                debug_info["error"] = "Produit n'existe pas"
                return debug_info
            
            # Étape 2: Fetch docs
            try:
                query = f"Commande de {quantity} {product_id}"
                if proposed_price:
                    query += f" à {proposed_price} euros"
                    
                result = fetch_docs(
                    query=query,
                    product_id=product_id,
                    required_qty=quantity,
                    prix_propose=proposed_price
                )
                debug_info["steps"]["fetch_docs_success"] = bool(result and result.get("produit"))
                debug_info["steps"]["fetch_docs_result"] = result
                
            except Exception as e:
                debug_info["steps"]["fetch_docs_error"] = str(e)
                debug_info["error"] = f"Erreur fetch_docs: {e}"
                return debug_info
            
            if not result or not result.get("produit"):
                debug_info["error"] = "fetch_docs n'a pas retourné de produit"
                return debug_info
                
            # Étape 3: Analyse faisabilité
            product_info = result["produit"]
            analysis = self._analyze_feasibility(product_info, quantity, proposed_price)
            debug_info["steps"]["analysis"] = analysis
            
            # Étape 4: Statut final
            status, message = self._determine_status(product_id, analysis, product_info)
            debug_info["steps"]["final_status"] = status
            debug_info["steps"]["final_message"] = message
            
            # Résultat final
            debug_info["final_result"] = ValidationResult(
                status=status,
                message=message,
                product_id=product_id,
                product_info=product_info,
                analysis=analysis,
                alternatives=result.get("alternatives", [])
            )
            
        except Exception as e:
            debug_info["error"] = f"Erreur générale: {str(e)}"
            logger.error(f"Erreur debug_validation: {e}")
        
        return debug_info 