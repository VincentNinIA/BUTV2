"""
Module de génération de commentaires intelligents pour NINIA
=========================================================

Ce module contient l'agent spécialisé dans la génération de commentaires
automatiques pour les tableaux de traitement des commandes.

Classes principales:
- CommentAgent: Agent principal de génération de commentaires
- CommentTemplates: Templates de prompts pour différents types de commentaires
"""

from .comment_agent import CommentAgent
from .comment_templates import CommentTemplates

__all__ = ["CommentAgent", "CommentTemplates"] 