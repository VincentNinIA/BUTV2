"""
Module d'extraction de produits et quantités
==========================================

Ce module gère l'extraction des informations de commande depuis le texte utilisateur.
Il contient les différentes stratégies d'extraction et de parsing.
"""

from .product_parser import ProductParser
from .text_extractor import extract_product_info, normalize_text

__all__ = ['ProductParser', 'extract_product_info', 'normalize_text'] 