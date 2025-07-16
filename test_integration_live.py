                        #!/usr/bin/env python3
"""
Test d'intégration : Alternatives RAG dans interface live
=======================================================

Vérifie que les alternatives remontent bien dans les commentaires et emails.
"""

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath('.'))
load_dotenv()

def test_integration_complete():
    """Test complet de l'intégration RAG → Interface Live"""
    print("🚀 === TEST INTÉGRATION RAG → INTERFACE LIVE ===\n")
    
    try:
        from rag.commande_manager import CommandeManagerAvance
        
        # Initialiser le gestionnaire
        manager = CommandeManagerAvance()
        
        # Test 1: Cas avec rupture garantie (doit déclencher RAG)
        print("📋 Test 1: Rupture de stock garantie (doit déclencher RAG)")
        ligne_test = "76000 00420000 CAISSE US SC 450X300X230MM Qté 5000 Prix : 0,7€"  # Stock insuffisant garanti
        
        resultat = manager.analyser_ligne_commande_complete(ligne_test)
        
        print(f"✅ Parsing réussi: {resultat.parsing_success}")
        print(f"📦 Produit trouvé: {resultat.product_found}")
        print(f"🔍 Alternatives RAG: {len(resultat.alternatives_rag)} trouvées")
        print(f"💬 Commentaire: {resultat.commentaire_utilisateur}")
        print(f"📧 Email envoyé: {resultat.email_envoye}")
        
        if resultat.alternatives_rag:
            print(f"\n🎯 Top 3 alternatives:")
            for i, alt in enumerate(resultat.alternatives_rag[:3], 1):
                print(f"   {i}. {alt.get('name', 'N/A')} - Stock: {alt.get('stock_disponible', 'N/A')}")
        
        # Vérifier que l'intégration fonctionne
        success_checks = {
            "parsing_ok": resultat.parsing_success,
            "alternatives_trouvees": len(resultat.alternatives_rag) > 0,
            "commentaire_mentionne_alternatives": "alternatives" in resultat.commentaire_utilisateur.lower(),
            "email_genere": resultat.email_envoye or resultat.details_email is not None
        }
        
        print(f"\n📊 Vérifications:")
        for check, status in success_checks.items():
            icon = "✅" if status else "❌"
            print(f"   {icon} {check.replace('_', ' ').title()}: {status}")
        
        total_score = sum(success_checks.values()) / len(success_checks)
        print(f"\n🎯 Score d'intégration Test 1: {total_score:.1%}")
        
        # Test 2: Cas avec marge insuffisante (doit aussi déclencher RAG)
        print(f"\n📋 Test 2: Marge insuffisante (doit déclencher RAG)")
        ligne_test2 = "76000 00420000 CAISSE US SC 400X300X300MM Qté 100 Prix : 0,20€"  # Prix très bas
        
        resultat2 = manager.analyser_ligne_commande_complete(ligne_test2)
        
        print(f"✅ Parsing réussi: {resultat2.parsing_success}")
        print(f"🔍 Alternatives RAG: {len(resultat2.alternatives_rag)} trouvées")
        print(f"💬 Commentaire: {resultat2.commentaire_utilisateur}")
        
        # Vérifications Test 2
        success_checks2 = {
            "parsing_ok": resultat2.parsing_success,
            "alternatives_trouvees": len(resultat2.alternatives_rag) > 0,
            "commentaire_mentionne_alternatives": "alternatives" in resultat2.commentaire_utilisateur.lower()
        }
        
        total_score2 = sum(success_checks2.values()) / len(success_checks2)
        print(f"🎯 Score d'intégration Test 2: {total_score2:.1%}")
        
        # Score global
        score_global = (total_score + total_score2) / 2
        print(f"\n🏆 SCORE GLOBAL: {score_global:.1%}")
        
        if score_global >= 0.5:
            print("🎉 INTÉGRATION RÉUSSIE - Les alternatives remontent bien dans l'interface live !")
        else:
            print("⚠️ Problème d'intégration détecté")
        
        return score_global >= 0.5
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

if __name__ == "__main__":
    success = test_integration_complete()
    exit(0 if success else 1) 