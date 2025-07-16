"""
Module de gestion des alternatives
=================================

Ce module gère la recherche et la sélection d'alternatives :
- Recherche d'alternatives techniques
- Sélection optimale par LLM
- Enrichissement des alternatives
"""

from .manager import AlternativesManager
from .selector import select_best_alternative

__all__ = ['AlternativesManager', 'select_best_alternative'] 