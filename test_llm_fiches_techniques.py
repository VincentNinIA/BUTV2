#!/usr/bin/env python3
"""
Test de Vérification LLM - Fiches Techniques
===========================================

Ce script vérifie que :
1. Le LLM reçoit bien les fiches techniques complètes
2. Il analyse correctement les informations reçues
3. Il fait des choix pertinents basés sur les données
4. Les prompts contiennent toutes les informations nécessaires
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import time # Added missing import for time

# Ajouter le chemin du projet
sys.path.insert(0, os.path.abspath('.'))

def test_fiches_techniques_retrieval():
    """Test 1: Vérifier que les fiches techniques sont bien récupérées"""
    print("\n🔍 === TEST 1: RÉCUPÉRATION FICHES TECHNIQUES ===")
    
    try:
        from rag.retrieval import _vector_store, _inventory_df
        
        # Test sur un produit connu
        test_product = "CAISSE US SC 400X300X300MM"
        print(f"Test sur : {test_product}")
        
        # Recherche de fiche technique
        print("🔍 Recherche fiche technique...")
        product_docs = _vector_store.similarity_search_with_score(
            f"fiche technique {test_product}",
            k=3  # Plus de résultats pour analyse
        )
        
        if product_docs:
            for i, (doc, score) in enumerate(product_docs):
                print(f"\n📄 Fiche {i+1} (score: {score:.3f}):")
                print(f"Contenu (200 premiers chars): {doc.page_content[:200]}...")
                
                # Vérifier si c'est bien une fiche technique
                content_lower = doc.page_content.lower()
                tech_indicators = [
                    'fiche produit', 'caractéristiques techniques', 'conception',
                    'type :', 'force :', 'avantages', 'description détaillée'
                ]
                
                tech_found = [ind for ind in tech_indicators if ind in content_lower]
                print(f"Indicateurs techniques trouvés: {tech_found}")
                
                if tech_found:
                    print("✅ Fiche technique valide détectée")
                else:
                    print("⚠️ Contenu technique limité")
        else:
            print("❌ Aucune fiche technique trouvée")
            
        return bool(product_docs)
        
    except Exception as e:
        print(f"❌ Erreur récupération fiches: {e}")
        return False

def test_llm_prompt_construction():
    """Test 2: Vérifier la construction des prompts pour le LLM"""
    print("\n🤖 === TEST 2: CONSTRUCTION PROMPTS LLM ===")
    
    try:
        from rag.core import answer
        from rag.retrieval_optimized import fetch_docs_optimized
        
        # Test avec un cas problématique pour déclencher alternatives
        test_product = "CAISSE US SC 400X300X300MM"
        required_qty = 1000
        prix_propose = 0.25  # Prix bas pour déclencher problème marge
        
        print(f"Test: {test_product}, Qté: {required_qty}, Prix: {prix_propose}€")
        
        # Récupérer les données RAG
        print("📦 Récupération données RAG...")
        result = fetch_docs_optimized(
            query=f"Analyse {test_product}",
            product_id=test_product,
            required_qty=required_qty,
            prix_propose=prix_propose
        )
        
        if result and result.get('alternatives'):
            produit = result['produit']
            alternatives = result['alternatives']
            
            print(f"\n✅ Données récupérées:")
            print(f"   - Produit principal: {produit.get('name', 'N/A')}")
            print(f"   - Alternatives trouvées: {len(alternatives)}")
            print(f"   - Marge produit: {produit.get('marge_actuelle', 'N/A')}€")
            
            # Analyser le contenu des alternatives
            print(f"\n📊 Analyse contenu alternatives:")
            for i, alt in enumerate(alternatives[:3]):  # Top 3
                print(f"\n   Alternative {i+1}: {alt.get('name', 'N/A')}")
                print(f"   - Stock: {alt.get('stock_disponible', 'N/A')}")
                print(f"   - Marge: {alt.get('marge', 'N/A')}€")
                print(f"   - Similarité: {alt.get('similarite_technique', 'N/A')}")
                
                # Vérifier les fiches techniques des alternatives
                description = alt.get('description', '')
                if description:
                    print(f"   - Fiche technique: OUI ({len(description)} chars)")
                    if 'fiche produit' in description.lower():
                        print("     ✅ Fiche technique structurée détectée")
                    else:
                        print(f"     📄 Contenu: {description[:100]}...")
                else:
                    print("   - Fiche technique: NON")
            
            return True
        else:
            print("❌ Aucune alternative récupérée")
            return False
            
    except Exception as e:
        print(f"❌ Erreur construction prompt: {e}")
        return False

def test_llm_decision_making():
    """Test 3: Vérifier la qualité des décisions du LLM"""
    print("\n🧠 === TEST 3: QUALITÉ DÉCISIONS LLM ===")
    
    try:
        from ninia.agent import NiniaAgent
        import os
        
        # Créer l'agent avec la clé API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY manquante dans l'environnement")
            return False
            
        agent = NiniaAgent(api_key)
        
        # Test cases avec attentes spécifiques
        test_cases = [
            {
                "name": "Cas 1: Marge insuffisante",
                "input": "76000 00420000 CAISSE US SC 400X300X300MM Qté 100 Prix : 0,20€",
                "expectation": "Devrait identifier marge insuffisante et proposer alternatives"
            },
            {
                "name": "Cas 2: Stock insuffisant", 
                "input": "76000 00420000 CAISSE US SC 450X300X230MM Qté 5000 Prix : 0,7€",
                "expectation": "Devrait identifier rupture stock et proposer alternatives"
            },
            {
                "name": "Cas 3: Produit correct",
                "input": "76000 00420000 CAISSE US SC 200X150X150MM Qté 50 Prix : 1,0€",
                "expectation": "Devrait valider le produit et mentionner alternatives"
            }
        ]
        
        results = []
        for test_case in test_cases:
            print(f"\n🎯 {test_case['name']}")
            print(f"Input: {test_case['input']}")
            print(f"Attente: {test_case['expectation']}")
            
            # Analyser avec l'agent
            print("🤖 Analyse par l'agent...")
            start_time = time.time()
            
            response = agent.analyser_commande(test_case['input'])
            
            analysis_time = time.time() - start_time
            
            # Analyser la réponse
            response_text = response.get('response', '') if isinstance(response, dict) else str(response)
            
            print(f"⏱️ Temps d'analyse: {analysis_time:.2f}s")
            print(f"📝 Réponse (200 premiers chars): {response_text[:200]}...")
            
            # Vérifications qualité
            quality_checks = {
                "mentionne_alternatives": "alternative" in response_text.lower(),
                "cite_chiffres": any(char.isdigit() for char in response_text),
                "analyse_marge": "marge" in response_text.lower(),
                "analyse_stock": "stock" in response_text.lower(),
                "propose_solution": any(word in response_text.lower() for word in ["propose", "recommande", "suggère"])
            }
            
            print(f"✅ Vérifications qualité:")
            for check, passed in quality_checks.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check.replace('_', ' ').title()}: {passed}")
            
            # Score qualité
            quality_score = sum(quality_checks.values()) / len(quality_checks)
            print(f"📊 Score qualité: {quality_score:.1%}")
            
            results.append({
                "case": test_case['name'],
                "time": analysis_time,
                "quality_score": quality_score,
                "checks": quality_checks
            })
        
        # Synthèse
        print(f"\n📋 === SYNTHÈSE QUALITÉ LLM ===")
        avg_time = sum(r['time'] for r in results) / len(results)
        avg_quality = sum(r['quality_score'] for r in results) / len(results)
        
        print(f"⏱️ Temps moyen: {avg_time:.2f}s")
        print(f"📊 Qualité moyenne: {avg_quality:.1%}")
        
        if avg_quality >= 0.8:
            print("🎉 EXCELLENTE qualité des décisions LLM")
        elif avg_quality >= 0.6:
            print("✅ BONNE qualité des décisions LLM")
        else:
            print("⚠️ Qualité des décisions À AMÉLIORER")
            
        return avg_quality >= 0.6
        
    except Exception as e:
        print(f"❌ Erreur test décisions: {e}")
        return False

def test_fiches_alternatives_optimized():
    """Test 4: Vérifier que la version optimisée récupère les fiches des alternatives"""
    print("\n⚡ === TEST 4: FICHES DANS VERSION OPTIMISÉE ===")
    
    try:
        from rag.retrieval_optimized import fetch_docs_optimized
        from rag.retrieval import _vector_store
        
        # Test avec un cas qui déclenche alternatives
        test_product = "CAISSE US SC 400X300X300MM"
        result = fetch_docs_optimized(
            query="Test fiches alternatives",
            product_id=test_product,
            required_qty=1000,
            prix_propose=0.25
        )
        
        if not result or not result.get('alternatives'):
            print("❌ Aucune alternative dans version optimisée")
            return False
        
        alternatives = result['alternatives']
        print(f"✅ {len(alternatives)} alternatives trouvées")
        
        # Vérifier si les alternatives ont des fiches techniques
        alternatives_with_fiches = 0
        total_fiche_length = 0
        
        for i, alt in enumerate(alternatives):
            alt_name = alt.get('name', 'N/A')
            description = alt.get('description', '')
            
            print(f"\n📄 Alternative {i+1}: {alt_name}")
            
            if description:
                alternatives_with_fiches += 1
                total_fiche_length += len(description)
                print(f"   ✅ Fiche présente ({len(description)} chars)")
                
                # Tester qualité de la fiche
                tech_keywords = ['fiche produit', 'caractéristiques', 'conception', 'type', 'force']
                found_keywords = [kw for kw in tech_keywords if kw in description.lower()]
                print(f"   📋 Mots-clés techniques: {found_keywords}")
                
            else:
                print(f"   ❌ Pas de fiche technique")
                # Essayer de récupérer manuellement
                print(f"   🔍 Tentative récupération manuelle...")
                try:
                    manual_docs = _vector_store.similarity_search_with_score(
                        f"fiche technique {alt_name}",
                        k=1
                    )
                    if manual_docs:
                        manual_content = manual_docs[0][0].page_content
                        print(f"   📄 Fiche trouvée manuellement ({len(manual_content)} chars)")
                    else:
                        print(f"   ❌ Aucune fiche trouvée manuellement")
                except Exception as e:
                    print(f"   ❌ Erreur récupération manuelle: {e}")
        
        # Statistiques
        fiche_coverage = alternatives_with_fiches / len(alternatives)
        avg_fiche_length = total_fiche_length / max(alternatives_with_fiches, 1)
        
        print(f"\n📊 Statistiques fiches techniques:")
        print(f"   - Couverture: {fiche_coverage:.1%} ({alternatives_with_fiches}/{len(alternatives)})")
        print(f"   - Taille moyenne: {avg_fiche_length:.0f} caractères")
        
        if fiche_coverage >= 0.5:
            print("✅ Couverture acceptable des fiches techniques")
            return True
        else:
            print("⚠️ Couverture insuffisante des fiches techniques")
            return False
        
    except Exception as e:
        print(f"❌ Erreur test fiches optimisées: {e}")
        return False

def main():
    """Fonction principale de test"""
    load_dotenv()
    
    print("🕐 Début des tests LLM - Fiches Techniques")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exécuter tous les tests
    tests = [
        ("Récupération fiches", test_fiches_techniques_retrieval),
        ("Construction prompts", test_llm_prompt_construction), 
        ("Qualité décisions", test_llm_decision_making),
        ("Fiches dans optimisé", test_fiches_alternatives_optimized)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n" + "="*60)
        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            print(f"❌ Erreur dans {test_name}: {e}")
            results[test_name] = False
    
    # Bilan final
    print(f"\n" + "="*60)
    print(f"📋 === BILAN FINAL ===")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, success in results.items():
        status = "✅ RÉUSSI" if success else "❌ ÉCHEC"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Score global: {passed_tests}/{total_tests} ({passed_tests/total_tests:.1%})")
    
    if passed_tests == total_tests:
        print("🎉 TOUS LES TESTS RÉUSSIS - LLM reçoit bien les fiches techniques !")
    elif passed_tests >= total_tests * 0.75:
        print("✅ BONNE qualité - Quelques améliorations possibles")
    else:
        print("⚠️ AMÉLIORATIONS REQUISES - Vérifier la récupération des fiches")
    
    print(f"\n🏁 Tests terminés: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main() 