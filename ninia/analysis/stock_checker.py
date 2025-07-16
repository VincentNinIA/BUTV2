#!/usr/bin/env python3
"""
Vérificateur de stock et marge
============================

Module pour les vérifications rapides et modulaires de :
- Stock disponible
- Marges
- Prix
- Délais
"""

import logging
from typing import Dict, Any, Optional
from rag.retrieval import get_stock
from rag.optimized_search import OptimizedProductSearch

logger = logging.getLogger(__name__)

def check_stock(product_id: str) -> Dict[str, Any]:
    """
    Vérification rapide du stock pour un produit
    
    Args:
        product_id: ID ou nom du produit
        
    Returns:
        Dict: Informations sur le stock
    """
    try:
        logger.info(f"📦 Vérification stock pour : {product_id}")
        
        # Utiliser get_stock pour une vérification rapide
        stock = get_stock(product_id)
        
        if stock is None:
            return {
                "status": "ERROR",
                "message": f"Produit '{product_id}' non trouvé",
                "stock_disponible": 0,
                "product_found": False
            }
        
        return {
            "status": "OK" if stock > 0 else "RUPTURE",
            "message": f"Stock disponible : {stock} unités" if stock > 0 else "Rupture de stock",
            "stock_disponible": stock,
            "product_found": True,
            "product_id": product_id
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur vérification stock : {str(e)}")
        return {
            "status": "ERROR",
            "message": f"Erreur lors de la vérification : {str(e)}",
            "stock_disponible": 0,
            "product_found": False
        }

def check_margin(
    product_id: str, 
    proposed_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Vérification rapide de la marge pour un produit
    
    Args:
        product_id: ID ou nom du produit
        proposed_price: Prix proposé (optionnel)
        
    Returns:
        Dict: Informations sur la marge
    """
    try:
        logger.info(f"💰 Vérification marge pour : {product_id} @ {proposed_price}€")
        
        # Utiliser OptimizedProductSearch pour récupérer les infos
        search = OptimizedProductSearch()
        product_info = search.get_product_info(product_id)
        
        if not product_info:
            return {
                "status": "ERROR",
                "message": f"Produit '{product_id}' non trouvé",
                "product_found": False
            }
        
        # Récupération des prix
        prix_achat = product_info.get('prix_achat', 0)
        marge_minimum = product_info.get('marge_minimum', 0)
        prix_vente_conseille = product_info.get('prix_vente_conseille', 0)
        
        # Calcul de la marge
        if proposed_price is not None:
            prix_final = proposed_price
            marge_actuelle = proposed_price - prix_achat
        else:
            prix_final = prix_vente_conseille
            marge_actuelle = prix_vente_conseille - prix_achat
            
        marge_suffisante = marge_actuelle >= marge_minimum
        
        status = "OK" if marge_suffisante else "ATTENTION"
        
        if marge_suffisante:
            message = f"✅ Marge suffisante : {marge_actuelle:.2f}€ (min: {marge_minimum:.2f}€)"
        else:
            message = f"⚠️ Marge insuffisante : {marge_actuelle:.2f}€ < {marge_minimum:.2f}€"
        
        return {
            "status": status,
            "message": message,
            "product_found": True,
            "product_id": product_id,
            "prix_final": prix_final,
            "prix_achat": prix_achat,
            "marge_actuelle": marge_actuelle,
            "marge_minimum": marge_minimum,
            "marge_suffisante": marge_suffisante,
            "prix_vente_conseille": prix_vente_conseille
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur vérification marge : {str(e)}")
        return {
            "status": "ERROR",
            "message": f"Erreur lors de la vérification : {str(e)}",
            "product_found": False
        }

def check_stock_and_margin(
    product_id: str, 
    quantity: int, 
    proposed_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Vérification combinée stock + marge
    
    Args:
        product_id: ID ou nom du produit
        quantity: Quantité demandée
        proposed_price: Prix proposé (optionnel)
        
    Returns:
        Dict: Résultat combiné des vérifications
    """
    logger.info(f"🔍 Vérification combinée : {quantity}x {product_id} @ {proposed_price}€")
    
    # Vérifications séparées
    stock_result = check_stock(product_id)
    margin_result = check_margin(product_id, proposed_price)
    
    # Si l'un des deux a échoué
    if not stock_result["product_found"] or not margin_result["product_found"]:
        return {
            "status": "ERROR",
            "message": f"Produit '{product_id}' non trouvé",
            "stock_result": stock_result,
            "margin_result": margin_result
        }
    
    # Analyse combinée
    stock_ok = stock_result["stock_disponible"] >= quantity
    marge_ok = margin_result["marge_suffisante"]
    
    # Détermination du statut global
    if stock_ok and marge_ok:
        status = "OK"
        message = f"✅ Commande validée : {quantity}x {product_id}"
    elif stock_ok and not marge_ok:
        status = "ATTENTION"
        message = f"⚠️ Stock OK mais marge insuffisante"
    elif not stock_ok and marge_ok:
        status = "ATTENTION"
        message = f"⚠️ Marge OK mais stock insuffisant ({stock_result['stock_disponible']}/{quantity})"
    else:
        status = "REFUSED"
        message = f"❌ Stock ET marge insuffisants"
    
    return {
        "status": status,
        "message": message,
        "product_id": product_id,
        "quantity_requested": quantity,
        "stock_sufficient": stock_ok,
        "margin_sufficient": marge_ok,
        "stock_result": stock_result,
        "margin_result": margin_result,
        "combined_analysis": {
            "stock_available": stock_result["stock_disponible"],
            "stock_needed": quantity,
            "margin_current": margin_result.get("marge_actuelle", 0),
            "margin_minimum": margin_result.get("marge_minimum", 0),
            "final_price": margin_result.get("prix_final", 0)
        }
    }

def quick_availability_check(product_id: str) -> bool:
    """
    Vérification ultra-rapide de disponibilité
    
    Args:
        product_id: ID du produit
        
    Returns:
        bool: True si le produit est disponible (stock > 0)
    """
    try:
        stock = get_stock(product_id)
        return stock is not None and stock > 0
    except:
        return False

def get_product_pricing(product_id: str) -> Optional[Dict[str, float]]:
    """
    Récupération rapide des informations de prix
    
    Args:
        product_id: ID du produit
        
    Returns:
        Dict: Informations de prix ou None si non trouvé
    """
    try:
        search = OptimizedProductSearch()
        product_info = search.get_product_info(product_id)
        
        if not product_info:
            return None
            
        return {
            "prix_achat": product_info.get('prix_achat', 0),
            "prix_vente_conseille": product_info.get('prix_vente_conseille', 0),
            "marge_minimum": product_info.get('marge_minimum', 0),
            "marge_actuelle": product_info.get('prix_vente_conseille', 0) - product_info.get('prix_achat', 0)
        }
    except Exception as e:
        logger.error(f"❌ Erreur récupération prix : {e}")
        return None 