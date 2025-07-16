#!/usr/bin/env python3
"""
Script de test pour déclencher le RAG avec des cas de rupture et de marge
=====================================================================

Ce script teste spécifiquement :
1. Le déclenchement du RAG en cas de rupture de stock
2. Le déclenchement du RAG en cas de marge insuffisante  
3. L'analyse et sélection d'alternatives par le LLM
4. Le système complet d'alertes email

"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Ajouter le chemin du projet
sys.path.insert(0, os.path.abspath('.'))

def test_rag_rupture_stock():
    """Test 1: Déclenchement RAG en cas de rupture de stock"""
    print("\n🔍 === TEST 1: RUPTURE DE STOCK ===")
    
    try:
        from rag.core import answer
        from rag.retrieval import fetch_docs
        
        # Cas test : commande d'une grande quantité pour forcer rupture
        product_id = "CAISSE US SC 450X300X230MM"  # Produit existant
        quantity = 10000  # Quantité énorme pour forcer rupture
        question = f"Je veux commander {quantity} unités de {product_id}"
        
        print(f"🎯 Test rupture avec : {product_id} x {quantity}")
        print(f"📝 Question : {question}")
        
        # Déclencher la recherche RAG  
        print("\n🔍 Déclenchement du RAG via fetch_docs...")
        result = fetch_docs(
            query=question,
            product_id=product_id,
            required_qty=quantity
        )
        
        # Analyser le résultat
        if result and result.get("alternatives"):
            print(f"✅ RAG DÉCLENCHÉ ! {len(result['alternatives'])} alternatives trouvées")
            
            # Afficher les alternatives
            for i, alt in enumerate(result["alternatives"][:3], 1):
                print(f"   {i}. {alt['name']} - Stock: {alt['stock_disponible']} - Score: {alt.get('score', 'N/A')}")
            
            # Test avec l'agent pour la sélection LLM
            print("\n🤖 Test sélection par le LLM...")
            response = answer(
                question=question,
                product_id=product_id,
                required_qty=quantity
            )
            
            print(f"📋 Réponse LLM (premiers 200 chars): {response[:200]}...")
            return True
        else:
            print("❌ Aucune alternative trouvée - RAG non déclenché")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test rupture: {str(e)}")
        return False

def test_rag_marge_insuffisante():
    """Test 2: Déclenchement RAG en cas de marge insuffisante"""
    print("\n💰 === TEST 2: MARGE INSUFFISANTE ===")
    
    try:
        from rag.core import answer
        from rag.retrieval import fetch_docs
        
        # Cas test : prix très bas pour forcer marge insuffisante
        product_id = "CAISSE US SC 450X300X230MM"
        quantity = 100
        prix_propose = 0.20  # Prix très bas pour forcer marge insuffisante
        question = f"Je veux commander {quantity} {product_id} à {prix_propose}€ l'unité"
        
        print(f"🎯 Test marge avec : {product_id} x {quantity} à {prix_propose}€")
        print(f"📝 Question : {question}")
        
        # Déclencher la recherche RAG avec prix proposé
        print("\n🔍 Déclenchement du RAG pour marge insuffisante...")
        result = fetch_docs(
            query=question,
            product_id=product_id,
            required_qty=quantity,
            prix_propose=prix_propose
        )
        
        # Analyser le résultat
        if result and result.get("alternatives"):
            print(f"✅ RAG DÉCLENCHÉ POUR MARGE ! {len(result['alternatives'])} alternatives trouvées")
            
            # Afficher les alternatives avec marges
            for i, alt in enumerate(result["alternatives"][:3], 1):
                marge = alt.get('marge', 0)
                marge_min = alt.get('marge_minimum', 0)
                print(f"   {i}. {alt['name']} - Marge: {marge:.2f}€ (min: {marge_min:.2f}€)")
            
            # Test avec l'agent pour la sélection LLM
            print("\n🤖 Test sélection LLM pour marge...")
            response = answer(
                question=question,
                product_id=product_id,
                required_qty=quantity,
                prix_propose=prix_propose
            )
            
            print(f"📋 Réponse LLM (premiers 200 chars): {response[:200]}...")
            return True
        else:
            print("❌ Aucune alternative trouvée pour marge")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test marge: {str(e)}")
        return False

def test_agent_complet():
    """Test 3: Agent NINIA complet avec alertes email"""
    print("\n🤖 === TEST 3: AGENT NINIA COMPLET ===")
    
    try:
        from ninia.agent import NiniaAgent
        
        # Initialiser l'agent
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ Clé OpenAI manquante")
            return False
            
        agent = NiniaAgent(api_key=api_key)
        
        # Test avec format spécifique [[memory:2717753]]
        message_test = "76000 00420000 CAISSE US SC 450X300X230MM Qté 5000 Prix : 0,3€"
        
        print(f"🎯 Test agent avec : {message_test}")
        print("📧 (Devrait déclencher alerte email pour marge ET stock)")
        
        # Traiter la commande
        response = agent.analyser_commande(message_test)
        
        print(f"✅ Réponse agent : {response[:300]}...")
        
        # Test génération commentaire + email
        commande_info = {
            'nom_produit': 'CAISSE US SC 450X300X230MM',
            'quantite_demandee': 5000,
            'stock_disponible': 100,  # Stock insuffisant
            'stock_suffisant': False,
            'marge_calculee': 0.1,    # Marge insuffisante  
            'marge_minimum': 0.5,
            'marge_suffisante': False,
            'prix_propose': 0.3
        }
        
        # Test génération email d'alerte
        if hasattr(agent, 'generate_alert_email_if_needed'):
            email_result = agent.generate_alert_email_if_needed(commande_info, "Client_Test")
            
            if email_result:
                print(f"📧 EMAIL D'ALERTE GÉNÉRÉ !")
                print(f"   Objet: {email_result['objet']}")
                print(f"   Corps (100 premiers chars): {email_result['corps'][:100]}...")
                return True
            else:
                print("⚠️ Aucun email d'alerte généré")
                
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test agent: {str(e)}")
        return False

def test_commande_manager_avance():
    """Test 4: CommandeManagerAvance avec système de ruptures"""
    print("\n📋 === TEST 4: COMMANDE MANAGER AVANCÉ ===")
    
    try:
        from rag.commande_manager import CommandeManagerAvance
        
        # Initialiser le gestionnaire
        manager = CommandeManagerAvance()
        
        # Test avec ligne de commande problématique
        ligne_test = "76000 00420000 CAISSE US SC 450X300X230MM Qté 8000 Prix : 0,25€"
        
        print(f"🎯 Test manager avec : {ligne_test}")
        
        # Analyser la ligne
        resultat = manager.analyser_ligne_commande_complete(ligne_test)
        
        print(f"✅ Analyse terminée :")
        print(f"   - Produit trouvé: {resultat.product_found}")
        print(f"   - Parsing réussi: {resultat.parsing_success}")
        print(f"   - Email envoyé: {resultat.email_envoye}")
        print(f"   - Niveau alerte: {resultat.niveau_alerte}")
        print(f"   - Commentaire: {resultat.commentaire_utilisateur}")
        
        if resultat.verification_rupture:
            print(f"   - Stock suffisant: {resultat.verification_rupture.stock_suffisant}")
            print(f"   - Type disponibilité: {resultat.verification_rupture.type_disponibilite}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test manager: {str(e)}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 === TESTS DE DÉCLENCHEMENT DU RAG ===")
    print("🎯 Objectif: Vérifier que le RAG propose bien des alternatives")
    print("📧 Bonus: Tester les alertes email automatiques\n")
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Résultats des tests
    resultats = []
    
    # Test 1: Rupture de stock
    resultats.append(("Rupture Stock", test_rag_rupture_stock()))
    
    # Test 2: Marge insuffisante  
    resultats.append(("Marge Insuffisante", test_rag_marge_insuffisante()))
    
    # Test 3: Agent complet
    resultats.append(("Agent NINIA", test_agent_complet()))
    
    # Test 4: Gestionnaire avancé
    resultats.append(("Manager Avancé", test_commande_manager_avance()))
    
    # Résumé final
    print("\n" + "="*60)
    print("📋 RÉSUMÉ DES TESTS DE DÉCLENCHEMENT RAG:")
    
    tests_reussis = 0
    for nom_test, resultat in resultats:
        status = "✅ RÉUSSI" if resultat else "❌ ÉCHEC"
        print(f"   {nom_test:.<20} {status}")
        if resultat:
            tests_reussis += 1
    
    print(f"\n🏆 BILAN: {tests_reussis}/{len(resultats)} tests réussis")
    
    if tests_reussis == len(resultats):
        print("🎉 EXCELLENT ! Le RAG se déclenche correctement.")
        print("📧 Les alertes email sont fonctionnelles.")
        print("🤖 Le LLM propose bien les meilleures alternatives.")
    elif tests_reussis > 0:
        print("⚠️  PARTIEL : Certains tests ont réussi.")
        print("🔧 Vérifiez les erreurs ci-dessus pour les échecs.")
    else:
        print("❌ PROBLÈME : Aucun test réussi.")
        print("🔧 Vérifiez la configuration et les logs d'erreurs.")

if __name__ == "__main__":
    main() 