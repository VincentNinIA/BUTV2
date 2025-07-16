#!/usr/bin/env python3
"""
Gestionnaire d'alternatives
==========================

Module responsable de la gestion complète des alternatives :
- Recherche d'alternatives pour un produit
- Enrichissement des données d'alternatives
- Coordination avec le sélecteur LLM
- Gestion des fallbacks
"""

import logging
from typing import List, Dict, Any, Optional
from rag.retrieval import fetch_docs, enrich_alternatives_for_llm
from .selector import AlternativesSelector

logger = logging.getLogger(__name__)

class AlternativesManager:
    """Gestionnaire principal pour les alternatives de produits"""
    
    def __init__(self, llm_client=None):
        """
        Initialise le gestionnaire d'alternatives
        
        Args:
            llm_client: Client LLM optionnel pour la sélection intelligente
        """
        self.selector = AlternativesSelector(llm_client)
        
    def find_alternatives_for_order(
        self,
        product_id: str,
        quantity: int,
        proposed_price: Optional[float] = None,
        problems: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        Trouve et analyse les alternatives pour une commande problématique
        
        Args:
            product_id: ID du produit original
            quantity: Quantité demandée
            proposed_price: Prix proposé (optionnel)
            problems: Dict des problèmes identifiés {"stock": True, "margin": False}
            
        Returns:
            Dict contenant les alternatives et l'analyse
        """
        logger.info(f"🔍 Recherche d'alternatives pour : {product_id}")
        
        try:
            # Étape 1: Récupérer les alternatives via fetch_docs
            query = f"Alternative pour {product_id}"
            result = fetch_docs(
                query=query,
                product_id=product_id,
                required_qty=quantity,
                prix_propose=proposed_price
            )
            
            if not result or not result.get("alternatives"):
                return {
                    "status": "NO_ALTERNATIVES",
                    "message": f"Aucune alternative trouvée pour {product_id}",
                    "alternatives": [],
                    "original_product": result.get("produit") if result else None
                }
            
            alternatives = result["alternatives"]
            original_product = result.get("produit", {})
            
            logger.info(f"✅ {len(alternatives)} alternatives trouvées")
            
            # Étape 2: Enrichir les alternatives pour l'analyse LLM
            enriched_alternatives = enrich_alternatives_for_llm(
                alternatives, 
                original_product, 
                proposed_price
            )
            
            # Étape 3: Filtrer les alternatives selon les problèmes
            filtered_alternatives = self._filter_alternatives_by_problems(
                enriched_alternatives, 
                quantity, 
                problems or {}
            )
            
            return {
                "status": "ALTERNATIVES_FOUND",
                "message": f"{len(filtered_alternatives)} alternatives compatibles trouvées",
                "alternatives": filtered_alternatives,
                "original_product": original_product,
                "total_found": len(alternatives),
                "after_filtering": len(filtered_alternatives)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur recherche alternatives : {str(e)}")
            return {
                "status": "ERROR",
                "message": f"Erreur lors de la recherche : {str(e)}",
                "alternatives": [],
                "original_product": None
            }
    
    def select_best_alternative(
        self,
        original_product: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        selection_criteria: Optional[List[str]] = None,
        context_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sélectionne la meilleure alternative via LLM ou fallback
        
        Args:
            original_product: Produit original demandé
            alternatives: Liste des alternatives disponibles
            selection_criteria: Critères de sélection prioritaires
            context_info: Contexte supplémentaire (quantité demandée, problème détecté, etc.)
            
        Returns:
            Dict contenant la sélection et l'analyse
        """
        if not alternatives:
            return {
                "selected": None,
                "reason": "Aucune alternative disponible",
                "confidence": 0.0,
                "method": "none"
            }
        
        if len(alternatives) == 1:
            return {
                "selected": alternatives[0],
                "reason": "Seule alternative disponible",
                "confidence": 0.8,
                "method": "single_choice"
            }
        
        # Enrichir le produit original avec le contexte
        enriched_original = original_product.copy()
        if context_info:
            enriched_original.update({
                'quantite_demandee': context_info.get('quantity', 0),
                'probleme_detecte': context_info.get('problem_type', 'Non spécifié'),
                'prix_propose': context_info.get('proposed_price', None)
            })
        
        # Utiliser le sélecteur LLM avec le contexte enrichi
        return self.selector.select_best_alternative(
            enriched_original,
            alternatives,
            selection_criteria
        )
    
    def _filter_alternatives_by_problems(
        self,
        alternatives: List[Dict[str, Any]],
        required_quantity: int,
        problems: Dict[str, bool]
    ) -> List[Dict[str, Any]]:
        """
        Filtre léger des alternatives pour garder un maximum d'options pour le LLM
        
        Args:
            alternatives: Liste des alternatives
            required_quantity: Quantité nécessaire
            problems: Problèmes à résoudre
            
        Returns:
            List: Alternatives légèrement filtrées (garde le maximum pour l'analyse LLM)
        """
        # ⚠️ FILTRAGE TRÈS PERMISSIF : On garde presque tout pour le LLM
        filtered = []
        
        for alt in alternatives:
            is_valid = True
            rejection_reason = []
            
            # ✅ Ne plus filtrer sur le stock - Le LLM peut proposer livraison partielle
            # if problems.get("stock", False):
            #     if alt.get("stock_disponible", 0) < required_quantity:
            #         rejection_reason.append("stock insuffisant")
            #         is_valid = False
            
            # ✅ Ne plus filtrer sur la marge - Le LLM peut proposer négociation prix
            # if problems.get("margin", False):
            #     marge_actuelle = alt.get("marge", 0)
            #     marge_minimum = alt.get("marge_minimum", 0)
            #     if marge_actuelle < marge_minimum:
            #         rejection_reason.append("marge insuffisante")
            #         is_valid = False
            
            # ⚠️ SEUL FILTRE CONSERVÉ : Similarité technique très faible (< 5%)
            similarite = alt.get("similarite_technique")
            if isinstance(similarite, (int, float)) and similarite < 0.05:
                rejection_reason.append(f"similarité technique trop faible ({similarite:.1%})")
                is_valid = False
            
            if is_valid:
                filtered.append(alt)
            else:
                logger.debug(f"Alternative {alt.get('name')} éliminée : {', '.join(rejection_reason)}")
        
        logger.info(f"🔍 Filtrage léger : {len(alternatives)} → {len(filtered)} alternatives (maximum conservé pour LLM)")
        return filtered
    
    def get_alternatives_summary(
        self,
        product_id: str,
        quantity: int,
        proposed_price: Optional[float] = None
    ) -> str:
        """
        Récupère un résumé formaté des alternatives disponibles
        
        Args:
            product_id: ID du produit
            quantity: Quantité demandée
            proposed_price: Prix proposé
            
        Returns:
            str: Résumé formaté pour l'utilisateur
        """
        result = self.find_alternatives_for_order(product_id, quantity, proposed_price)
        
        if result["status"] == "NO_ALTERNATIVES":
            return f"❌ Aucune alternative trouvée pour {product_id}"
        
        if result["status"] == "ERROR":
            return f"❌ Erreur : {result['message']}"
        
        alternatives = result["alternatives"]
        summary = f"🔄 {len(alternatives)} alternatives disponibles pour {product_id} :\n\n"
        
        for i, alt in enumerate(alternatives, 1):
            summary += f"{i}. **{alt.get('name', 'Produit inconnu')}**\n"
            summary += f"   • Stock : {alt.get('stock_disponible', 'N/A')} unités\n"
            summary += f"   • Prix : {alt.get('prix_vente_conseille', 'N/A')}€\n"
            summary += f"   • Délai : {alt.get('delai', 'N/A')}\n"
            
            # Affichage sécurisé de la similarité
            similarite = alt.get('similarite_technique')
            if isinstance(similarite, (int, float)):
                summary += f"   • Compatibilité : {similarite:.0%}\n"
            
            summary += "\n"
        
        return summary
    
    def debug_alternatives(
        self,
        product_id: str,
        quantity: int,
        proposed_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Version debug pour voir toutes les étapes de recherche d'alternatives
        """
        debug_info = {
            "input": {
                "product_id": product_id,
                "quantity": quantity,
                "proposed_price": proposed_price
            },
            "steps": {},
            "error": None
        }
        
        try:
            # Étape 1: fetch_docs
            query = f"Alternative pour {product_id}"
            result = fetch_docs(
                query=query,
                product_id=product_id,
                required_qty=quantity,
                prix_propose=proposed_price
            )
            
            debug_info["steps"]["fetch_docs"] = {
                "success": bool(result),
                "alternatives_found": len(result.get("alternatives", [])) if result else 0,
                "original_product_found": bool(result and result.get("produit"))
            }
            
            if not result:
                debug_info["error"] = "fetch_docs a retourné None"
                return debug_info
            
            # Étape 2: Enrichissement
            alternatives = result.get("alternatives", [])
            original_product = result.get("produit", {})
            
            enriched = enrich_alternatives_for_llm(alternatives, original_product, proposed_price)
            debug_info["steps"]["enrichment"] = {
                "before": len(alternatives),
                "after": len(enriched)
            }
            
            # Étape 3: Filtrage
            filtered = self._filter_alternatives_by_problems(enriched, quantity, {"stock": True, "margin": True})
            debug_info["steps"]["filtering"] = {
                "before": len(enriched),
                "after": len(filtered)
            }
            
            debug_info["final_alternatives"] = filtered
            
        except Exception as e:
            debug_info["error"] = str(e)
            logger.error(f"Erreur debug_alternatives: {e}")
        
        return debug_info 