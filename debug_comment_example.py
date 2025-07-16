#!/usr/bin/env python3
"""
Exemple d'utilisation du CommentAgent de NINIA
=============================================

Ce script montre comment utiliser le nouveau module de génération
de commentaires intelligents dans votre code.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from ninia.agent import NiniaAgent
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def exemple_usage_comment_agent():
    """Exemple pratique d'utilisation du CommentAgent"""
    
    print("🎯 === EXEMPLE D'UTILISATION DU COMMENT AGENT ===\n")
    
    # Initialisation de l'agent NINIA (inclut le CommentAgent)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Erreur: OPENAI_API_KEY non configuré")
        return
    
    agent = NiniaAgent(api_key=api_key)
    print("✅ Agent NINIA initialisé (CommentAgent inclus)\n")
    
    # Exemple 1: Commande standard
    print("📦 Exemple 1: Commande standard")
    commande_info = {
        'nom_produit': 'CAISSE US SC 450X300X230MM',
        'quantite_demandee': 300,
        'stock_disponible': 500,
        'stock_suffisant': True,
        'marge_calculee': 2.5,
        'marge_suffisante': True,
        'prix_propose': 0.7,
        'delai_livraison': '2 semaines',
        'alertes': 'Aucune'
    }
    
    commentaire = agent.generate_table_comment(commande_info, comment_type="order")
    print(f"   💬 Commentaire généré: {commentaire}\n")
    
    # Exemple 2: Problème de stock
    print("⚠️ Exemple 2: Problème de stock")
    stock_info = {
        'nom_produit': 'Film étirable 20µm',
        'stock_actuel': 50,
        'seuil_minimum': 100,
        'delai_reappro': '4 semaines'
    }
    
    commentaire = agent.generate_table_comment(stock_info, comment_type="stock_alert")
    print(f"   💬 Commentaire généré: {commentaire}\n")
    
    # Exemple 3: Détection automatique
    print("🤖 Exemple 3: Détection automatique du type")
    auto_info = {
        'nom_produit': 'Étui fourreau mousse',
        'quantite_demandee': 100,  # Présence de quantité → détection "order"
        'stock_disponible': 50,
        'stock_suffisant': False
    }
    
    commentaire = agent.generate_table_comment(auto_info, comment_type="auto")
    print(f"   💬 Commentaire auto: {commentaire}\n")
    
    # Exemple 4: Debug complet
    print("🔍 Exemple 4: Debug complet")
    debug_result = agent.debug_comment_generation(auto_info)
    print(f"   🎯 Type détecté: {debug_result['detected_type']}")
    print(f"   🔧 Statut LLM: {debug_result['llm_status']}")
    print("   📝 Commentaires générés par type:")
    for comment_type, comment in debug_result['generated_comments'].items():
        if not comment.startswith("Erreur"):
            print(f"      - {comment_type}: {comment}")
    
    print("\n✨ === INTÉGRATION RÉUSSIE ===")
    print("Le CommentAgent est maintenant intégré dans votre chatbot !")
    print("Les commentaires du tableau seront générés automatiquement.")

if __name__ == "__main__":
    exemple_usage_comment_agent() 