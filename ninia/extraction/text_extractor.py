#!/usr/bin/env python3
"""
Fonctions utilitaires pour l'extraction de texte
==============================================

Module contenant les fonctions de base pour :
- Normalisation de texte (accents, casse, etc.)
- Extraction de prix depuis du texte
- Nettoyage et préparation des chaînes
"""

import re
import logging
import unidecode
from typing import Optional

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """
    Normalise un texte pour la recherche
    
    Args:
        text: Texte à normaliser
        
    Returns:
        str: Texte normalisé (sans accents, minuscules, nettoyé)
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Suppression des accents et normalisation Unicode
    normalized = unidecode.unidecode(text.lower().strip())
    
    # Nettoyage des espaces multiples
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized

def extract_price_from_message(message: str) -> Optional[float]:
    """
    Extrait le prix d'un message utilisateur
    
    Args:
        message: Message contenant potentiellement un prix
        
    Returns:
        float: Prix extrait ou None si rien trouvé
    """
    logger.info(f"🔍 Extraction de prix depuis : '{message[:50]}...'")
    
    # Nettoyer le message des espaces Unicode
    text_clean = re.sub(r'\s', ' ', message)
    text_clean = text_clean.replace('à', 'a')  # Normaliser les 'à'
    
    # Patterns pour extraire le prix (par ordre de priorité)
    price_patterns = [
        r'[Pp]rix\s*:\s*(\d+(?:[,.]?\d+)?)€?',    # "Prix : 1€" ou "prix: 12.50"
        r'(?:a|pour|de)\s*(\d+(?:[,.]?\d+)?)\s*(?:euros?|eur|€)',  # "à 8 euros", "pour 12€"
        r'(\d+(?:[,.]?\d+)?)\s*(?:euros?|eur|€)',  # "15€", "8 euros"
        r'(\d+(?:[,.]?\d+)?)\s*€',                 # "1€"
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            try:
                prix_str = match.group(1).replace(',', '.')
                prix = float(prix_str)
                logger.info(f"✅ Prix trouvé : {prix}€ depuis '{match.group(0)}'")
                return prix
            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Erreur conversion prix '{match.group(1)}' : {e}")
                continue
    
    logger.info("❌ Aucun prix trouvé")
    return None

def extract_product_info(message: str, inventory_df=None) -> tuple:
    """
    Interface simplifiée pour l'extraction complète
    
    Args:
        message: Message utilisateur
        inventory_df: DataFrame optionnel de l'inventaire
        
    Returns:
        tuple: (product_id, quantity, price)
    """
    from .product_parser import ProductParser
    
    parser = ProductParser(inventory_df)
    return parser.extract_product_info(message)

def clean_command_keywords(text: str, keywords: list = None) -> str:
    """
    Supprime les mots-clés de commande du début du texte
    
    Args:
        text: Texte à nettoyer
        keywords: Liste des mots-clés à supprimer
        
    Returns:
        str: Texte nettoyé
    """
    if keywords is None:
        keywords = [
            "commande de", "commande", "acheter", "prendre", 
            "je veux", "je voudrais", "j'aimerais", "besoin de", 
            "pour", "donne moi"
        ]
    
    # Trier par longueur décroissante pour éviter les conflits
    keywords = sorted(keywords, key=len, reverse=True)
    
    stripped_text = text.strip()
    for keyword in keywords:
        # Supprimer au début du texte
        if stripped_text.lower().startswith(keyword.lower() + " "):
            stripped_text = stripped_text[len(keyword)+1:].lstrip()
        elif stripped_text.lower() == keyword.lower():
            stripped_text = ""
            break
    
    return stripped_text

def extract_units_and_quantities(text: str) -> list:
    """
    Extrait toutes les quantités et unités d'un texte
    
    Args:
        text: Texte à analyser
        
    Returns:
        list: Liste de dictionnaires avec 'quantity', 'unit', 'position'
    """
    results = []
    
    # Unités de commande reconnues
    command_units = [
        "unite", "unites", "rouleau", "rouleaux", "exemplaire", "exemplaires",
        "piece", "pieces", "caisse", "caisses", "boite", "boites", 
        "palette", "palettes", "sac", "sacs", "carton", "cartons"
    ]
    
    # Normaliser le texte
    normalized = normalize_text(text)
    
    # Chercher les patterns quantité + unité
    for unit in command_units:
        pattern = rf"(\d+)\s*({unit})\b"
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            results.append({
                'quantity': int(match.group(1)),
                'unit': match.group(2),
                'position': match.start(),
                'text': match.group(0)
            })
    
    # Chercher aussi les patterns "Qté X"
    qty_patterns = [
        r'[Qq]té\s+(\d+)',
        r'[Qq]uantité\s*:?\s*(\d+)',
    ]
    
    for pattern in qty_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            results.append({
                'quantity': int(match.group(1)),
                'unit': 'qty_keyword',
                'position': match.start(),
                'text': match.group(0)
            })
    
    # Trier par position dans le texte
    results.sort(key=lambda x: x['position'])
    
    return results 