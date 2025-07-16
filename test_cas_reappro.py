#!/usr/bin/env python3
"""
Test des améliorations pour le cas de dépendance au réapprovisionnement
=====================================================================

Ce script teste spécifiquement le cas mentionné par l'utilisateur :
7600005 00000000 CAISSE US SC 200X140X140MM Qté 3000 Prix : 0,8€

Où le produit est théoriquement en rupture mais avec réapprovisionnement
suffisant, donc pas de problème réel.
"""

import sys
import os
import logging
from datetime import datetime

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag.commande_manager import CommandeManagerAvance
from rag.gestionnaire_stock import GestionnaireStock

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_cas_reappro_specifique():
    """Test du cas spécifique avec réapprovisionnement"""
    print("=" * 70)
    print("🧪 TEST CAS RÉAPPROVISIONNEMENT SPÉCIFIQUE")
    print("=" * 70)
    
    # Commande problématique mentionnée par l'utilisateur
    commande_test = "7600005 00000000	CAISSE US SC 200X140X140MM Qté 3000 Prix : 0,8€"
    
    print(f"📋 Commande testée: {commande_test}")
    print()
    
    # Initialiser le gestionnaire de commandes
    try:
        commande_manager = CommandeManagerAvance()
        print("✅ Gestionnaire de commandes initialisé")
    except Exception as e:
        print(f"❌ Erreur initialisation gestionnaire: {e}")
        return
    
    # Analyser la ligne de commande
    print("\n📊 ANALYSE DE LA COMMANDE:")
    print("-" * 50)
    
    try:
        ligne_analysee = commande_manager.analyser_ligne_commande_complete(
            commande_test,
            date_commande=datetime.now()
        )
        
        print(f"🔍 Parsing réussi: {ligne_analysee.parsing_success}")
        print(f"📦 Produit trouvé: {ligne_analysee.product_found}")
        print(f"🆔 ID produit: {ligne_analysee.id_produit}")
        print(f"📝 Désignation: {ligne_analysee.designation}")
        print(f"🔢 Quantité: {ligne_analysee.quantite}")
        print(f"💰 Prix unitaire: {ligne_analysee.prix_unitaire}€")
        print(f"💰 Prix total: {ligne_analysee.prix_total}€")
        
        print("\n📈 ANALYSE DE STOCK:")
        print("-" * 30)
        
        if ligne_analysee.verification_rupture:
            verif = ligne_analysee.verification_rupture
            print(f"📊 Stock suffisant: {verif.stock_suffisant}")
            print(f"🔄 Type disponibilité: {verif.type_disponibilite}")
            print(f"⚠️ Niveau alerte: {verif.niveau_alerte}")
            print(f"📧 Nécessite alerte commercial: {verif.necessite_alerte_commercial}")
            print(f"📝 Message principal: {verif.message_principal}")
            
            # Détails du stock
            if verif.produit:
                produit = verif.produit
                stock_actuel = produit.quantite_stock - produit.commandes_a_livrer
                print(f"🏪 Stock magasin: {produit.quantite_stock}")
                print(f"📦 Commandes à livrer: {produit.commandes_a_livrer}")
                print(f"🔢 Stock actuel net: {stock_actuel}")
                print(f"📈 Stock à recevoir: {produit.stock_a_recevoir}")
                print(f"🎯 Stock total futur: {stock_actuel + produit.stock_a_recevoir}")
                print(f"❓ Quantité demandée: {ligne_analysee.quantite}")
        
        print("\n🔄 ANALYSE DU DÉCLENCHEMENT RAG:")
        print("-" * 40)
        
        print(f"📋 Alternatives RAG trouvées: {len(ligne_analysee.alternatives_rag)}")
        if len(ligne_analysee.alternatives_rag) > 0:
            print("❌ PROBLÈME: Le RAG a été déclenché alors qu'il ne devrait pas !")
            print("   Le stock total est suffisant avec le réapprovisionnement")
        else:
            print("✅ CORRECT: Le RAG n'a pas été déclenché")
            print("   Stock total suffisant avec réapprovisionnement")
        
        print("\n💬 COMMENTAIRE GÉNÉRÉ:")
        print("-" * 30)
        print(f"📝 Commentaire: {ligne_analysee.commentaire_utilisateur}")
        print(f"🎯 Niveau alerte: {ligne_analysee.niveau_alerte}")
        
        # Vérifier si le commentaire est approprié
        if "dépend du réapprovisionnement" in ligne_analysee.commentaire_utilisateur:
            print("✅ CORRECT: Le commentaire explique la dépendance au réapprovisionnement")
        else:
            print("❌ PROBLÈME: Le commentaire n'explique pas clairement la situation")
        
        print("\n📧 GESTION DES ALERTES:")
        print("-" * 30)
        print(f"📬 Email envoyé: {ligne_analysee.email_envoye}")
        
        if ligne_analysee.email_envoye:
            print("❌ PROBLÈME: Un email a été envoyé alors qu'il n'y a pas de problème critique")
        else:
            print("✅ CORRECT: Pas d'email envoyé (situation normale)")
        
        print("\n🎯 RÉSUMÉ DE L'ANALYSE:")
        print("-" * 30)
        
        # Évaluer si l'analyse est correcte
        stock_ok = ligne_analysee.verification_rupture.stock_suffisant if ligne_analysee.verification_rupture else False
        rag_declenche = len(ligne_analysee.alternatives_rag) > 0
        email_envoye = ligne_analysee.email_envoye
        
        if stock_ok and not rag_declenche and not email_envoye:
            print("✅ ANALYSE PARFAITE !")
            print("   - Stock suffisant avec réapprovisionnement")
            print("   - RAG non déclenché (correct)")
            print("   - Pas d'email d'alerte (correct)")
            print("   - Commentaire informatif")
        else:
            print("⚠️ PROBLÈMES DÉTECTÉS:")
            if not stock_ok:
                print("   - Stock analysé comme insuffisant")
            if rag_declenche:
                print("   - RAG déclenché inutilement")
            if email_envoye:
                print("   - Email d'alerte envoyé inutilement")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        import traceback
        traceback.print_exc()

def test_comparaison_avant_apres():
    """Test de comparaison avant/après les améliorations"""
    print("\n" + "=" * 70)
    print("🔄 TEST DE COMPARAISON AVANT/APRÈS LES AMÉLIORATIONS")
    print("=" * 70)
    
    # Cas de test variés
    cas_tests = [
        ("7600005 00000000	CAISSE US SC 200X140X140MM Qté 3000 Prix : 0,8€", "Stock avec réapprovisionnement"),
        ("76000 00420000	CAISSE US SC 450X300X230MM Qté 5000 Prix : 0,7€", "Rupture totale"),
        ("76000 00330000	CAISSE US SC 350X250X200MM Qté 100 Prix : 0,6€", "Stock suffisant"),
    ]
    
    commande_manager = CommandeManagerAvance()
    
    for commande, description in cas_tests:
        print(f"\n📋 Test: {description}")
        print(f"   Commande: {commande}")
        
        try:
            ligne_analysee = commande_manager.analyser_ligne_commande_complete(commande)
            
            # Résumé rapide
            rag_declenche = len(ligne_analysee.alternatives_rag) > 0
            stock_ok = ligne_analysee.verification_rupture.stock_suffisant if ligne_analysee.verification_rupture else False
            
            print(f"   ✅ Stock suffisant: {stock_ok}")
            print(f"   🔄 RAG déclenché: {rag_declenche}")
            print(f"   💬 Commentaire: {ligne_analysee.commentaire_utilisateur}")
            
            # Évaluation rapide
            if stock_ok and not rag_declenche:
                print("   🎯 Analyse optimale !")
            elif not stock_ok and rag_declenche:
                print("   ⚠️ Problème détecté, RAG déclenché (correct)")
            elif stock_ok and rag_declenche:
                print("   ❌ RAG déclenché inutilement")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")

if __name__ == "__main__":
    print("🧪 TESTS DES AMÉLIORATIONS RÉAPPROVISIONNEMENT")
    print("=" * 70)
    
    # Test du cas spécifique
    test_cas_reappro_specifique()
    
    # Test de comparaison
    test_comparaison_avant_apres()
    
    print("\n✅ Tests terminés !")
    print("=" * 70) 